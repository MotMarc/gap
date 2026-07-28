from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.protocol import router as protocol_router
from app.api.admin import router as admin_router
from app.core.provider_config import PROVIDERS
from app.core.registry_authority_config import REFERENCE_REGISTRY_AUTHORITY
from app.core.transparency_log_config import REFERENCE_TRANSPARENCY_LOG
from app.core.transparency_witness_config import REFERENCE_TRANSPARENCY_WITNESS
from app.core.logging import configure_logging
from app.core.middleware import operational_middleware
from app.core.settings import get_settings
from app.core.version import APPLICATION_VERSION
from app.crypto.provider_keys import (
    encode_public_key,
    load_private_key,
    load_public_key,
)
from app.database import require_head
from app.core.repositories import (
    BOOTSTRAP_REPORT,
    FEDERATION_INVALID_FILE_COUNT,
    FEDERATION_LOADED_BUNDLE_COUNT,
    transparency_log_repository,
    witness_statement_repository,
    checkpoint_gossip_repository,
    database,
)


APPLICATION_DIRECTORY = Path(__file__).resolve().parent
WEB_DIRECTORY = APPLICATION_DIRECTORY / "web"
settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    configure_logging(settings.log_level)
    application.state.ready = False
    application.state.readiness_reason = "startup-checks-pending"
    if not settings.key_directory.is_dir():
        raise RuntimeError("Required key directory is unavailable.")
    identities = [
        *PROVIDERS,
        REFERENCE_REGISTRY_AUTHORITY,
        REFERENCE_TRANSPARENCY_LOG,
        REFERENCE_TRANSPARENCY_WITNESS,
    ]
    for identity in identities:
        for key in identity.signing_keys:
            if not key.public_key_path.is_file():
                raise RuntimeError(f"Public key is unavailable for {key.key_id}.")
            if key.status == "active":
                if key.private_key_path is None or not key.private_key_path.is_file():
                    raise RuntimeError(
                        f"Active private key is unavailable for {key.key_id}."
                    )
                derived = encode_public_key(
                    load_private_key(key.private_key_path).public_key()
                )
                published = encode_public_key(load_public_key(key.public_key_path))
                if derived != published:
                    raise RuntimeError(f"Key-pair mismatch for {key.key_id}.")
    if database is not None:
        require_head(database.engine)
        with database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    latest_head = transparency_log_repository.latest_tree_head()
    if (
        latest_head is None
        or latest_head.payload.tree_size != transparency_log_repository.entry_count
        or latest_head.payload.root_hash != transparency_log_repository.current_root()
    ):
        raise RuntimeError(
            "Stored transparency state does not match its signed tree head."
        )
    application.state.ready = True
    application.state.readiness_reason = None
    yield
    application.state.ready = False
    active_database = getattr(application.state, "database", None)
    if active_database is not None:
        active_database.dispose()


app = FastAPI(
    title="Generation Attribution Protocol",
    description=(
        "Reference implementation and browser demonstrator for the "
        "Generation Attribution Protocol."
    ),
    version=APPLICATION_VERSION,
    lifespan=lifespan,
)
app.state.settings = settings
app.state.database = database
app.middleware("http")(operational_middleware)
if settings.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )


app.include_router(protocol_router)
app.include_router(admin_router)


app.mount(
    "/static",
    StaticFiles(directory=WEB_DIRECTORY),
    name="static",
)


@app.get(
    "/",
    include_in_schema=False,
    response_class=FileResponse,
)
def read_demonstrator() -> FileResponse:
    """
    Serve the GAP browser demonstrator.
    """

    return FileResponse(
        WEB_DIRECTORY / "index.html",
        media_type="text/html",
    )


@app.get(
    "/health",
    tags=["System"],
)
def read_health() -> dict[str, str | int | bool]:
    """
    Return the current service status.
    """

    return {
        "status": "healthy",
        "service": "gap-reference-implementation",
        "version": APPLICATION_VERSION,
        "ready": bool(getattr(app.state, "ready", True)),
        "persistence_mode": settings.persistence_mode,
        "environment": settings.app_env,
        "bootstrap_created_count": BOOTSTRAP_REPORT["created"],
        "federation_loaded_bundle_count": FEDERATION_LOADED_BUNDLE_COUNT,
        "federation_invalid_file_count": FEDERATION_INVALID_FILE_COUNT,
        "transparency_log_loaded": True,
        "transparency_entry_count": transparency_log_repository.entry_count,
        "transparency_tree_size": transparency_log_repository.entry_count,
        "transparency_valid_tree_head_count": len(
            transparency_log_repository.list_tree_heads()
        ),
        "transparency_invalid_runtime_object_count": (
            transparency_log_repository.invalid_runtime_object_count
        ),
        "transparency_consistency_valid": True,
        "trusted_witness_count": 1,
        "witness_statement_count": len(witness_statement_repository.list_all()),
        "witness_invalid_runtime_object_count": (
            witness_statement_repository.invalid_runtime_object_count
        ),
        "gossip_observation_count": len(checkpoint_gossip_repository.list_all()),
        "gossip_invalid_runtime_object_count": (
            checkpoint_gossip_repository.invalid_runtime_object_count
        ),
    }


@app.get("/health/live", tags=["System"])
def liveness() -> dict[str, str]:
    return {
        "status": "alive",
        "service": "gap-reference-implementation",
        "version": APPLICATION_VERSION,
    }


@app.get("/health/ready", tags=["System"])
def readiness():
    ready = bool(getattr(app.state, "ready", True))
    payload = {
        "status": "ready" if ready else "not-ready",
        "version": APPLICATION_VERSION,
    }
    if settings.health_details_enabled and not ready:
        payload["reason"] = getattr(app.state, "readiness_reason", "startup-incomplete")
    return JSONResponse(payload, status_code=200 if ready else 503)


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException):
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        {
            "detail": error.detail,
            "error": {
                "code": f"http-{error.status_code}",
                "message": str(error.detail),
                "request_id": request_id,
            },
        },
        status_code=error.status_code,
        headers=error.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        {
            "error": {
                "code": "validation-error",
                "message": "Request validation failed.",
                "request_id": request_id,
            }
        },
        status_code=422,
    )
