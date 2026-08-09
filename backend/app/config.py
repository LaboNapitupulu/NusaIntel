from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
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
