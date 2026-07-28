from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.repositories import database, trust_registry_service
from app.database.models import AdministrativeAuditRow
from app.database.uow import UnitOfWork


router = APIRouter(prefix="/admin", tags=["Administration"])
_memory_audit = []


class TrustTransitionRequest(BaseModel):
    status: str = Field(pattern="^(approved|suspended|removed)$")
    reason: str = Field(min_length=1, max_length=2000)
    authority: str = Field(
        default="GAP Pilot Administrator", min_length=1, max_length=500
    )


def require_administrator(request: Request):
    settings = request.app.state.settings
    if not settings.admin_api_enabled:
        raise HTTPException(status_code=404, detail="Administrative API is disabled.")
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = header[7:]
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(digest, settings.admin_api_token_hash or ""):
        raise HTTPException(status_code=403, detail="Invalid administrator token.")
    return digest[:16]


def _audit(request, actor, action, target, outcome, details):
    row = {
        "event_id": str(uuid.uuid4()),
        "action": action,
        "target_id": target,
        "request_id": request.state.request_id,
        "outcome": outcome,
        "actor_fingerprint": actor,
        "occurred_at": datetime.now(timezone.utc),
        "details_json": json.dumps(details, sort_keys=True, separators=(",", ":")),
    }
    if database is None:
        _memory_audit.append(row)
    else:
        with database.session() as session:
            session.add(AdministrativeAuditRow(**row))


@router.post("/providers/{provider_id}/trust")
def transition_provider_trust(
    provider_id: str,
    body: TrustTransitionRequest,
    request: Request,
    actor=Depends(require_administrator),
):
    try:
        if database is None:
            decision = trust_registry_service.record_decision(
                provider_id=provider_id,
                status=body.status,
                authority=body.authority,
                reason=body.reason,
            )
        else:
            with UnitOfWork(database.session_factory):
                decision = trust_registry_service.record_decision(
                    provider_id=provider_id,
                    status=body.status,
                    authority=body.authority,
                    reason=body.reason,
                )
    except ValueError as error:
        _audit(
            request,
            actor,
            "provider-trust-transition",
            provider_id,
            "denied",
            {"reason": str(error)},
        )
        raise HTTPException(status_code=409, detail=str(error)) from error
    _audit(
        request,
        actor,
        "provider-trust-transition",
        provider_id,
        "succeeded",
        {"decision_id": decision.decision_id, "status": decision.status},
    )
    return {
        "decision_id": decision.decision_id,
        "provider_id": provider_id,
        "status": decision.status,
        "request_id": request.state.request_id,
    }


@router.get("/audit")
def administrative_audit(request: Request, actor=Depends(require_administrator)):
    if database is None:
        rows = _memory_audit
    else:
        with database.session_factory() as session:
            values = (
                session.query(AdministrativeAuditRow)
                .order_by(AdministrativeAuditRow.occurred_at)
                .all()
            )
            rows = [
                {
                    "event_id": item.event_id,
                    "action": item.action,
                    "target_id": item.target_id,
                    "request_id": item.request_id,
                    "outcome": item.outcome,
                    "occurred_at": item.occurred_at,
                }
                for item in values
            ]
    return {"events": rows, "count": len(rows)}
