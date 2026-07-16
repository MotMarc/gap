from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Provider:
    """
    Represents a participating GAP provider.

    A Provider owns its signing keys and issues Generation Credentials
    under a stable provider identifier.
    """

    provider_id: str
    provider_name: str
    key_id: str
    private_key_path: Path
    public_key_path: Path
