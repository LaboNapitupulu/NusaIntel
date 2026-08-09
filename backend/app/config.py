from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NusaIntel API"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    bps_api_key: SecretStr | None = None
    bps_base_url: str = "https://webapi.bps.go.id/v1/api"
    bps_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    bps_max_attempts: int = Field(default=3, ge=1, le=6)
    bps_retry_base_seconds: float = Field(default=0.75, ge=0, le=30)
    bps_min_interval_seconds: float = Field(default=1.0, ge=0, le=60)
    bps_user_agent: str = "NusaIntel/0.2 (+https://github.com/LaboNapitupulu/NusaIntel)"

    @model_validator(mode="after")
    def validate_production_configuration(self) -> Self:
        if self.app_env == "production" and not self.database_url:
            raise ValueError("DATABASE_URL is required when APP_ENV=production")
        return self

    @property
    def resolved_database_url(self) -> str:
        return self.database_url or (
            "postgresql+asyncpg://nusa_intel:nusa_intel_dev@localhost:5432/nusa_intel"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
