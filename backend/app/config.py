from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlsplit

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
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "test", "testserver"]
    bps_api_key: SecretStr | None = None
    bps_base_url: str = "https://webapi.bps.go.id/v1/api"
    bps_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    bps_max_attempts: int = Field(default=3, ge=1, le=6)
    bps_retry_base_seconds: float = Field(default=0.75, ge=0, le=30)
    bps_min_interval_seconds: float = Field(default=1.0, ge=0, le=60)
    bps_user_agent: str = "NusaIntel/0.2 (+https://github.com/LaboNapitupulu/NusaIntel)"
    bps_schedule_enabled: bool = False
    bps_schedule_indicator: Literal[
        "grdp_growth_constant_2010",
        "grdp_per_capita_current",
        "hdi",
        "poverty_rate",
        "tpak",
        "tpt",
    ] = "tpt"
    bps_schedule_interval_seconds: int = Field(default=86400, ge=300, le=604800)
    regulation_answer_timeout_seconds: float = Field(default=9.0, gt=0, le=10)
    regulation_maximum_concurrent_answers: int = Field(default=8, ge=1, le=64)
    regulation_answer_rate_limit_requests: int = Field(default=10, ge=1, le=1000)
    regulation_answer_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    @model_validator(mode="after")
    def validate_production_configuration(self) -> Self:
        if self.app_env == "production" and not self.database_url:
            raise ValueError("DATABASE_URL is required when APP_ENV=production")
        if self.app_env == "production":
            parsed_origins = [urlsplit(origin) for origin in self.cors_origins]
            if not parsed_origins or any(
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                for parsed in parsed_origins
            ):
                raise ValueError("Production CORS_ORIGINS must contain explicit HTTPS origins only")
            if (
                not self.allowed_hosts
                or "*" in self.allowed_hosts
                or any(
                    not host.strip() or "://" in host or "/" in host for host in self.allowed_hosts
                )
            ):
                raise ValueError("Production ALLOWED_HOSTS must be explicit and cannot use '*'")
            public_hosts = {
                host
                for host in self.allowed_hosts
                if host not in {"localhost", "127.0.0.1", "test", "testserver"}
            }
            if not public_hosts:
                raise ValueError("Production ALLOWED_HOSTS must include the public API hostname")
        if self.bps_schedule_enabled and (
            self.bps_api_key is None or not self.bps_api_key.get_secret_value().strip()
        ):
            raise ValueError("BPS_API_KEY is required when BPS scheduling is enabled")
        return self

    @property
    def resolved_database_url(self) -> str:
        return self.database_url or (
            "postgresql+asyncpg://nusa_intel:nusa_intel_dev@localhost:5432/nusa_intel"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
