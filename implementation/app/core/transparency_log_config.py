from datetime import datetime, timezone
from app.core.settings import get_settings
from app.domain.transparency_log import (
    TransparencyLogOperator,
    TransparencyLogSigningKey,
)


KEY_DIRECTORY = get_settings().key_directory

REFERENCE_TRANSPARENCY_LOG = TransparencyLogOperator(
    log_id="gap-reference-transparency-log",
    log_name="GAP Reference Transparency Log",
    active_key_id="gap-log-key-2026-01",
    signing_keys=(
        TransparencyLogSigningKey(
            key_id="gap-log-key-2026-01",
            status="active",
            public_key_path=KEY_DIRECTORY / "transparency_log_public.key",
            private_key_path=KEY_DIRECTORY / "transparency_log_private.key",
            created_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        ),
    ),
)

TRUSTED_TRANSPARENCY_LOGS = {
    REFERENCE_TRANSPARENCY_LOG.log_id: REFERENCE_TRANSPARENCY_LOG
}
