"""Validate and decode a BPS Dynamic Data response fixture offline.

This is a Phase 0 spike, not the production connector. Composite
``datacontent`` keys are resolved by generating keys from the response's own
dimension metadata. This avoids brittle fixed-width parsing.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_FIELDS = {
    "status",
    "data-availability",
    "var",
    "labelvervar",
    "vervar",
    "tahun",
    "turvar",
    "turtahun",
    "datacontent",
}


def _require_list(payload: dict[str, Any], field: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValueError(f"Field {field!r} must be a list.")
    return value


def validate_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate stable envelope assumptions and return an offline summary."""

    missing = sorted(REQUIRED_TOP_LEVEL_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    if payload["status"] != "OK":
        raise ValueError(f"Expected status 'OK', received {payload['status']!r}.")
    if payload["data-availability"] != "available":
        raise ValueError("Fixture does not contain available data.")

    variables = _require_list(payload, "var")
    derived_variables = _require_list(payload, "turvar")
    vertical_variables = _require_list(payload, "vervar")
    periods = _require_list(payload, "tahun")
    derived_periods = _require_list(payload, "turtahun")
    dimensions = (
        vertical_variables,
        variables,
        derived_variables,
        periods,
        derived_periods,
    )
    if any(not dimension for dimension in dimensions):
        raise ValueError("BPS dimension metadata must not be empty.")

    data_content = payload["datacontent"]
    if not isinstance(data_content, dict) or not data_content:
        raise ValueError("Field 'datacontent' must be a non-empty object.")
    if any(not isinstance(key, str) for key in data_content):
        raise ValueError("Every datacontent key must be a string.")
    if any(not isinstance(value, (int, float)) for value in data_content.values()):
        raise ValueError("The Phase 0 fixture expects numeric datacontent values.")

    expected_keys: dict[str, tuple[dict[str, Any], ...]] = {}
    for members in itertools.product(*dimensions):
        key = "".join(str(member["val"]) for member in members)
        if key in expected_keys:
            raise ValueError(f"Ambiguous composite key generated: {key}")
        expected_keys[key] = members

    unknown_keys = sorted(set(data_content) - set(expected_keys))
    if unknown_keys:
        raise ValueError(
            f"Fixture contains {len(unknown_keys)} keys not represented by metadata."
        )

    missing_keys = sorted(set(expected_keys) - set(data_content))
    missing_observations = [
        {
            "geography": expected_keys[key][0].get("label"),
            "period": expected_keys[key][3].get("label"),
            "derived_period": expected_keys[key][4].get("label"),
        }
        for key in missing_keys
    ]

    variable = variables[0]
    return {
        "status": payload["status"],
        "availability": payload["data-availability"],
        "variable_id": variable.get("val"),
        "variable_label": variable.get("label"),
        "unit": variable.get("unit"),
        "geography_label": payload["labelvervar"],
        "geography_count": len(vertical_variables),
        "period_count": len(periods),
        "observation_count": len(data_content),
        "expected_observation_count": len(expected_keys),
        "coverage_percent": round(100 * len(data_content) / len(expected_keys), 2),
        "missing_observation_count": len(missing_keys),
        "missing_observations": missing_observations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()

    with args.fixture.open("r", encoding="utf-8") as fixture_file:
        payload = json.load(fixture_file)
    if not isinstance(payload, dict):
        raise ValueError("BPS response root must be an object.")

    print(json.dumps(validate_envelope(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
