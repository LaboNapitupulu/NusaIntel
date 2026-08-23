from __future__ import annotations

import sys
from importlib import import_module
from os import environ
from pathlib import Path

from pydantic import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

Settings = import_module("app.config").Settings


def main() -> int:
    try:
        settings = Settings(app_env="production")
    except ValidationError as error:
        print("Public beta configuration is invalid:", file=sys.stderr)
        for item in error.errors(include_url=False, include_input=False):
            print(f"- {item['msg']}", file=sys.stderr)
        return 2

    public_api_url = environ.get("NEXT_PUBLIC_API_BASE_URL", "")
    if "CHANGE_ME" in (settings.database_url or ""):
        print(
            "Public beta configuration is invalid:\n"
            "- DATABASE_URL still contains a placeholder value",
            file=sys.stderr,
        )
        return 2
    if not public_api_url.startswith("https://"):
        print(
            "Public beta configuration is invalid:\n"
            "- NEXT_PUBLIC_API_BASE_URL must be an explicit HTTPS URL",
            file=sys.stderr,
        )
        return 2

    print(
        "Public beta configuration valid: "
        f"cors_origins={len(settings.cors_origins)} "
        f"allowed_hosts={len(settings.allowed_hosts)} "
        "frontend_api_url=https "
        f"answer_limit={settings.regulation_answer_rate_limit_requests}/"
        f"{settings.regulation_answer_rate_limit_window_seconds}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
