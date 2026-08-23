import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_requires_database_url() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL is required"):
        Settings(app_env="production", database_url=None)


def test_production_requires_https_cors_and_public_host() -> None:
    database_url = "postgresql+asyncpg://user:password@db:5432/nusa_intel"
    with pytest.raises(ValidationError, match="HTTPS origins"):
        Settings(
            app_env="production",
            database_url=database_url,
            cors_origins=["http://app.example.test"],
            allowed_hosts=["api.example.test"],
        )
    with pytest.raises(ValidationError, match="HTTPS origins"):
        Settings(
            app_env="production",
            database_url=database_url,
            cors_origins=["https://app.example.test/unexpected-path"],
            allowed_hosts=["api.example.test"],
        )
    with pytest.raises(ValidationError, match="ALLOWED_HOSTS"):
        Settings(
            app_env="production",
            database_url=database_url,
            cors_origins=["https://app.example.test"],
            allowed_hosts=["https://api.example.test"],
        )
    with pytest.raises(ValidationError, match="public API hostname"):
        Settings(
            app_env="production",
            database_url=database_url,
            cors_origins=["https://app.example.test"],
            allowed_hosts=["localhost"],
        )


def test_production_accepts_explicit_https_origin_and_hosts() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://user:password@db:5432/nusa_intel",
        cors_origins=["https://app.example.test"],
        allowed_hosts=["api.example.test", "localhost"],
    )

    assert settings.cors_origins == ["https://app.example.test"]
    assert settings.allowed_hosts == ["api.example.test", "localhost"]


def test_development_has_safe_local_database_default() -> None:
    settings = Settings(app_env="development", database_url=None)

    assert settings.resolved_database_url.startswith("postgresql+asyncpg://")
    assert "localhost" in settings.resolved_database_url


def test_scheduler_requires_bps_key_when_enabled() -> None:
    with pytest.raises(ValidationError, match="BPS_API_KEY"):
        Settings(bps_schedule_enabled=True, bps_api_key=None)


def test_scheduler_rejects_blank_bps_key() -> None:
    with pytest.raises(ValidationError, match="BPS_API_KEY"):
        Settings(bps_schedule_enabled=True, bps_api_key="   ")
