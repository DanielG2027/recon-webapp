# Configuration - env and defaults. Bind 127.0.0.1 only.
# All secrets MUST be set via environment variables or .env file.
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _build_db_url(driver: str) -> str:
    """Build a database URL from individual env vars. No hardcoded passwords."""
    user = os.environ.get("RECON_DB_USER", "recon")
    password = os.environ.get("RECON_DB_PASSWORD", "")
    host = os.environ.get("RECON_DB_HOST", "127.0.0.1")
    port = os.environ.get("RECON_DB_PORT", "5432")
    name = os.environ.get("RECON_DB_NAME", "recon")
    if not password:
        raise RuntimeError(
            "RECON_DB_PASSWORD is not set. "
            "Copy .env.example to .env and fill in the database password."
        )
    return f"postgresql+{driver}://{user}:{password}@{host}:{port}/{name}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RECON_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Database — built from individual env vars; no inline credentials
    db_user: str = "recon"
    db_password: str = ""
    db_host: str = "127.0.0.1"
    db_port: str = "5432"
    db_name: str = "recon"

    @property
    def database_url(self) -> str:
        return _build_db_url("asyncpg")

    @property
    def database_url_sync(self) -> str:
        return _build_db_url("psycopg")

    # Storage limits (PRD)
    max_projects: int = 15
    max_artifact_bytes: int = 15 * 1024 * 1024 * 1024  # 15 GB
    raw_retention_days: int = 7
    log_retention_days: int = 7

    # Jobs
    default_concurrency: int = 2
    max_concurrency: int = 4
    default_container_cpu: str = "2"
    default_container_memory_gb: int = 2

    # Paths
    artifact_root: Path = Path("data/artifacts")
    report_root: Path = Path("data/reports")

    # Noise threshold for warning gate
    noise_warning_threshold: int = 7

    def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(**kwargs)
        self.artifact_root = Path(os.environ.get("RECON_ARTIFACT_ROOT", "data/artifacts"))
        self.report_root = Path(os.environ.get("RECON_REPORT_ROOT", "data/reports"))


settings = Settings()
