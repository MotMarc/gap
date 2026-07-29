import os


# Isolated repository tests intentionally retain the reference in-memory wiring.
# Tests must never inherit an operator's persistence configuration.  Import-time
# application wiring otherwise risks writing to retained runtime evidence.
os.environ["APP_ENV"] = "test"
os.environ["PERSISTENCE_MODE"] = "memory"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
