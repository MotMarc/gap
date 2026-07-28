import os


# Isolated repository tests intentionally retain the reference in-memory wiring.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("PERSISTENCE_MODE", "memory")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
