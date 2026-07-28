from datetime import datetime, timezone
from app.core.settings import get_settings
from app.domain.transparency_witness import (
    TransparencyWitness,
    TransparencyWitnessSigningKey,
)
from app.services.transparency_witness_repository import (
    TransparencyWitnessRepository,
)


KEY_DIRECTORY = get_settings().key_directory
REFERENCE_TRANSPARENCY_WITNESS = TransparencyWitness(
    witness_id="gap-reference-witness",
    witness_name="GAP Reference Transparency Witness",
    active_key_id="gap-witness-key-2026-01",
    signing_keys=(
        TransparencyWitnessSigningKey(
            key_id="gap-witness-key-2026-01",
            status="active",
            public_key_path=KEY_DIRECTORY / "transparency_witness_public.key",
            private_key_path=KEY_DIRECTORY / "transparency_witness_private.key",
            created_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        ),
    ),
)
transparency_witness_repository = TransparencyWitnessRepository(
    (REFERENCE_TRANSPARENCY_WITNESS,)
)
