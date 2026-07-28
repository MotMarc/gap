import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))
from app.core.repositories import BOOTSTRAP_REPORT, transparency_log_repository  # noqa: E402

print(
    f"created={BOOTSTRAP_REPORT['created']} existing={BOOTSTRAP_REPORT['existing']} "
    f"tree_size={transparency_log_repository.entry_count} "
    f"root={transparency_log_repository.current_root()}"
)
