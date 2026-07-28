from app.crypto.provider_keys import encode_public_key, load_public_key
from app.domain.transparency_witness import TransparencyWitness
from app.schemas.transparency_witness import (
    TransparencyWitnessIdentityDocument,
    TransparencyWitnessPublishedKey,
)


def create_transparency_witness_identity_document(
    witness: TransparencyWitness,
) -> TransparencyWitnessIdentityDocument:
    return TransparencyWitnessIdentityDocument(
        witness_id=witness.witness_id,
        witness_name=witness.witness_name,
        active_key_id=witness.active_key_id,
        signing_keys=tuple(
            TransparencyWitnessPublishedKey(
                key_id=key.key_id,
                public_key=encode_public_key(load_public_key(key.public_key_path)),
                status=key.status,
                created_at=key.created_at,
                retired_at=key.retired_at,
                revoked_at=key.revoked_at,
                revocation_reason=key.revocation_reason,
            )
            for key in witness.signing_keys
        ),
    )
