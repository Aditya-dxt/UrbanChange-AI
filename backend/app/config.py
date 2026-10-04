"""
Application configuration using pydantic-settings.
All values are read from environment variables (or a .env file).
No secrets are stored here; .env must never be committed.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


AdapterMode = Literal["mock", "http"]
IntelligenceMode = Literal["mock", "http", "python"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    secret_key: str = "change-me-in-production"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/urbanchange"
    )

    # ── Storage ───────────────────────────────────────────────────────────────
    storage_root: str = "/data/storage"

    # ── Adapter modes ─────────────────────────────────────────────────────────
    satellite_adapter: AdapterMode = "mock"
    ml_adapter: AdapterMode = "mock"
    gis_adapter: AdapterMode = "mock"
    intelligence_adapter: IntelligenceMode = "mock"

    # ── HTTP adapter URLs and timeouts ────────────────────────────────────────
    satellite_base_url: str = "http://localhost:8001"
    satellite_timeout_seconds: int = 30

    ml_base_url: str = "http://localhost:8002"
    ml_timeout_seconds: int = 60

    gis_base_url: str = "http://localhost:8003"
    gis_timeout_seconds: int = 30

    intelligence_base_url: str = "http://localhost:8004"
    intelligence_timeout_seconds: int = 60

    # ── Python module adapter (Intelligence only) ─────────────────────────────
    intelligence_python_entrypoint: str = ""

    # ── Pipeline configuration ────────────────────────────────────────────────
    context_layer_ids: list[str] = []
    temporal_max_observations: int = 0  # 0 = MVP two-date mode

    # ── Rate limiting ─────────────────────────────────────────────────────────
    run_rate_limit_per_minute: int = 10

    # ── Derived / constants ───────────────────────────────────────────────────
    api_version: str = "0.1.0"
    contract_version: str = "0.1.0"

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> list[str]:
        """Accept comma-separated string from env or a list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]

    @field_validator("context_layer_ids", mode="before")
    @classmethod
    def _parse_layer_ids(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def _validate_python_entrypoint(self) -> "Settings":
        if self.intelligence_adapter == "python" and not self.intelligence_python_entrypoint:
            raise ValueError(
                "INTELLIGENCE_PYTHON_ENTRYPOINT must be set when "
                "INTELLIGENCE_ADAPTER=python"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
