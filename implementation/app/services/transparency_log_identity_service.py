import base64
from cryptography.hazmat.primitives import serialization

from app.crypto.provider_keys import load_public_key
from app.domain.transparency_log import TransparencyLogOperator
from app.schemas.transparency_log import (
    TransparencyLogIdentityDocument,
    TransparencyLogPublishedKey,
)


def create_transparency_log_identity_document(
    operator: TransparencyLogOperator,
) -> TransparencyLogIdentityDocument:
    if isinstance(operator, TransparencyLogIdentityDocument):
        return operator.model_copy(deep=True)
    if hasattr(operator, "identity_document"):
        return operator.identity_document.model_copy(deep=True)
    keys = []
    for key in operator.signing_keys:
        public_key = load_public_key(key.public_key_path)
        raw = public_key.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        keys.append(
            TransparencyLogPublishedKey(
                key_id=key.key_id,
                public_key=base64.b64encode(raw).decode("ascii"),
                status=key.status,
                created_at=key.created_at,
                retired_at=key.retired_at,
                revoked_at=key.revoked_at,
                revocation_reason=key.revocation_reason,
            )
        )
    return TransparencyLogIdentityDocument(
        log_id=operator.log_id,
        log_name=operator.log_name,
        active_key_id=operator.active_key_id,
        signing_keys=tuple(keys),
    )
