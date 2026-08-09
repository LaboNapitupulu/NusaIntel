import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_requires_database_url() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL is required"):
        Settings(app_env="production", database_url=None)


def test_development_has_safe_local_database_default() -> None:
    settings = Settings(app_env="development", database_url=None)

    assert settings.resolved_database_url.startswith("postgresql+asyncpg://")
    assert "localhost" in settings.resolved_database_url
