from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx

from app.config import get_settings


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect safe BPS variable metadata.")
    parser.add_argument("variables", nargs="+", type=int)
    return parser.parse_args()


async def _paged_items(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    variable_id: int,
) -> list[dict[str, Any]]:
    parameters: dict[str, str | int] = {
        "model": model,
        "lang": "ind",
        "domain": "0000",
        "var": variable_id,
        "page": 1,
        "key": api_key,
    }
    response = await client.get("list", params=parameters)
    response.raise_for_status()
    payload = response.json()
    if payload.get("data-availability") != "available":
        return []
    data = payload.get("data")
    if not isinstance(data, list) or len(data) < 2:
        return []
    page_info, items = data[0], data[1]
    if not isinstance(page_info, dict) or not isinstance(items, list):
        return []
    result = [item for item in items if isinstance(item, dict)]
    pages = int(page_info.get("pages", 1))
    for page in range(2, pages + 1):
        parameters["page"] = page
        response = await client.get("list", params=parameters)
        response.raise_for_status()
        next_data = response.json().get("data", [])
        if isinstance(next_data, list) and len(next_data) >= 2 and isinstance(next_data[1], list):
            result.extend(item for item in next_data[1] if isinstance(item, dict))
    return result


async def _inspect(variable_ids: list[int]) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.bps_api_key is None:
        raise RuntimeError("BPS_API_KEY is required.")
    api_key = settings.bps_api_key.get_secret_value()
    result: list[dict[str, Any]] = []
    async with httpx.AsyncClient(
        base_url=f"{settings.bps_base_url.rstrip('/')}/",
        timeout=settings.bps_timeout_seconds,
        headers={"User-Agent": settings.bps_user_agent},
    ) as client:
        for variable_id in variable_ids:
            periods = await _paged_items(client, api_key, "th", variable_id)
            derived_variables = await _paged_items(client, api_key, "turvar", variable_id)
            derived_periods = await _paged_items(client, api_key, "turth", variable_id)
            result.append(
                {
                    "variable_id": variable_id,
                    "periods": [
                        item
                        for item in periods
                        if str(item.get("th", "")) in {"2023", "2024", "2025"}
                    ],
                    "derived_variables": derived_variables,
                    "derived_periods": derived_periods,
                }
            )
    return result


def main() -> None:
    arguments = _arguments()
    result = asyncio.run(_inspect(arguments.variables))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
