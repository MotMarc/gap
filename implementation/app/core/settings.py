from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.version import APPLICATION_VERSION


ROOT_DIRECTORY = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["test", "development", "demonstration", "production"] = (
        "development"
    )
    app_version: str = APPLICATION_VERSION
    database_url: str = (
        f"sqlite:///{(ROOT_DIRECTORY / 'runtime' / 'gap.db').as_posix()}"
    )
    persistence_mode: Literal["memory", "database"] = "database"
    runtime_directory: Path = ROOT_DIRECTORY / "runtime"
    key_directory: Path = ROOT_DIRECTORY / "implementation" / "keys"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    admin_api_enabled: bool = False
    admin_api_token_hash: str | None = None
    cors_allowed_origins: list[str] = Field(default_factory=list)
    max_request_size: int = Field(default=2 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    startup_strict_mode: bool = True
    backup_directory: Path = ROOT_DIRECTORY / "runtime" / "backups"
    health_details_enabled: bool = False

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"sqlite", "postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL must use SQLite or PostgreSQL.")
        if parsed.scheme == "sqlite" and not parsed.path:
            raise ValueError("SQLite DATABASE_URL must include a database path.")
        if parsed.scheme.startswith("postgresql") and not parsed.hostname:
            raise ValueError("PostgreSQL DATABASE_URL must include a hostname.")
        return value

    @field_validator("admin_api_token_hash")
    @classmethod
    def validate_token_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalised = value.lower()
        if len(normalised) != 64 or any(
            c not in "0123456789abcdef" for c in normalised
        ):
            raise ValueError("ADMIN_API_TOKEN_HASH must be a SHA-256 hex digest.")
        return normalised

    @model_validator(mode="after")
    def validate_combinations(self):
        if self.app_version != APPLICATION_VERSION:
            raise ValueError(f"APP_VERSION must be {APPLICATION_VERSION}.")
        if self.admin_api_enabled and not self.admin_api_token_hash:
            raise ValueError(
                "ADMIN_API_TOKEN_HASH is required when ADMIN_API_ENABLED is true."
            )
        if self.app_env == "production":
            if self.persistence_mode != "database":
                raise ValueError("Production requires database persistence.")
            if "*" in self.cors_allowed_origins:
                raise ValueError("Wildcard CORS is forbidden in production.")
        key_path = self.key_directory.resolve()
        runtime_path = self.runtime_directory.resolve()
        if key_path == runtime_path or runtime_path in key_path.parents:
            raise ValueError(
                "KEY_DIRECTORY cannot be inside the public runtime directory."
            )
        return self

    @property
    def database_safe_label(self) -> str:
        return "sqlite" if self.database_url.startswith("sqlite") else "postgresql"


def hash_admin_token(token: str) -> str:
    if not token:
        raise ValueError("Administrator token cannot be empty.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@lru_cache
def get_settings() -> Settings:
    return Settings()
