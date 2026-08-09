from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.bps.errors import BPSPayloadError
from app.pipeline.contracts import IndicatorContract
from app.pipeline.types import (
    NormalizedBatch,
    NormalizedObservation,
    QuarantinedRow,
    RetrievedPayload,
)


def _metadata_values(payload: dict[str, Any], field: str) -> tuple[str, ...]:
    value = payload.get(field)
    if isinstance(value, dict):
        candidate = value.get("val")
        return (str(candidate),) if candidate is not None else ()
    if not isinstance(value, list):
        return ()

    result: list[str] = []
    for item in value:
        if isinstance(item, dict) and item.get("val") is not None:
            result.append(str(item["val"]))
    return tuple(result)


def _source_key(
    region: str,
    variable: str,
    derived_variable: str,
    year: str,
    derived_period: str,
) -> str:
    return f"{region}{variable}{derived_variable}{year}{derived_period}"


def _observation_key(indicator: str, region: str, period: date) -> str:
    natural_key = f"{indicator}|{region}|{period.isoformat()}"
    return hashlib.sha256(natural_key.encode()).hexdigest()


def _parse_value(source_value: Any) -> tuple[Decimal | None, str | None, str]:
    if source_value is None or source_value == "":
        return None, None, "missing"

    text = str(source_value).strip()
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None, text, "invalid"
    if not value.is_finite():
        return None, text, "invalid"
    return value, text, "observed"


def _checksum(observations: list[NormalizedObservation]) -> str:
    stable_rows = [
        {
            "indicator": row.indicator_code,
            "key": row.observation_key,
            "period": row.period.isoformat(),
            "region": row.region_code,
            "source_value": row.source_value,
            "status": row.value_status,
            "value": str(row.value) if row.value is not None else None,
        }
        for row in sorted(observations, key=lambda item: item.observation_key)
    ]
    body = json.dumps(stable_rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()


def normalize_payload(
    retrieved: RetrievedPayload,
    contract: IndicatorContract,
) -> NormalizedBatch:
    payload = retrieved.payload
    datacontent = payload.get("datacontent")
    if not isinstance(datacontent, dict):
        raise BPSPayloadError("BPS datacontent must be an object.")

    variable_ids = _metadata_values(payload, "var")
    derived_variable_ids = _metadata_values(payload, "turvar")
    year_ids = _metadata_values(payload, "tahun")
    derived_period_ids = _metadata_values(payload, "turtahun")
    region_ids = _metadata_values(payload, "vervar")

    required = {
        "var": str(contract.bps_variable_id),
        "turvar": str(contract.bps_derived_variable_id),
        "turtahun": str(contract.bps_derived_period_id),
    }
    actual = {
        "var": variable_ids,
        "turvar": derived_variable_ids,
        "turtahun": derived_period_ids,
    }
    for field, expected in required.items():
        if expected not in actual[field]:
            raise BPSPayloadError(f"BPS {field} metadata does not match the data contract.")

    expected_year_ids = {
        str(period.bps_year_id) for period in contract.periods if period.bps_year_id is not None
    }
    if not expected_year_ids.issubset(set(year_ids)):
        raise BPSPayloadError("BPS year metadata does not satisfy the data contract.")

    known_regions = {region.code: region.name for region in contract.regions}
    known_regions[contract.national_code] = "INDONESIA"
    metadata_region_ids = set(region_ids)
    observations: list[NormalizedObservation] = []
    quarantined: list[QuarantinedRow] = []
    recognized_keys: set[str] = set()

    for region_code in sorted(metadata_region_ids):
        for variable_id in variable_ids:
            for derived_variable_id in derived_variable_ids:
                for period in contract.periods:
                    if period.bps_year_id is None:
                        continue
                    year_id = str(period.bps_year_id)
                    for derived_period_id in derived_period_ids:
                        key = _source_key(
                            region_code,
                            variable_id,
                            derived_variable_id,
                            year_id,
                            derived_period_id,
                        )
                        if key not in datacontent:
                            continue
                        recognized_keys.add(key)
                        if region_code not in known_regions:
                            quarantined.append(
                                QuarantinedRow(
                                    reason_code="unknown_region",
                                    source_key=key,
                                    safe_payload={
                                        "region_code": region_code,
                                        "period": period.year,
                                        "source_value": str(datacontent[key]),
                                    },
                                )
                            )

    for key in sorted(set(datacontent) - recognized_keys):
        quarantined.append(
            QuarantinedRow(
                reason_code="unrecognized_composite_key",
                source_key=str(key),
                safe_payload={"source_value": str(datacontent[key])},
            )
        )

    for region_code, region_name in sorted(known_regions.items()):
        for period in contract.periods:
            if period.bps_year_id is None:
                value, source_value, status = None, None, "missing"
            else:
                key = _source_key(
                    region_code,
                    str(contract.bps_variable_id),
                    str(contract.bps_derived_variable_id),
                    str(period.bps_year_id),
                    str(contract.bps_derived_period_id),
                )
                value, source_value, status = _parse_value(datacontent.get(key))
            observation_period = date(period.year, period.month, 1)
            observations.append(
                NormalizedObservation(
                    observation_key=_observation_key(
                        contract.code, region_code, observation_period
                    ),
                    region_code=region_code,
                    region_name=region_name,
                    indicator_code=contract.code,
                    period=observation_period,
                    value=value,
                    source_value=source_value,
                    value_status=status,
                    unit=contract.unit,
                    is_national_aggregate=region_code == contract.national_code,
                )
            )

    return NormalizedBatch(
        observations=tuple(observations),
        quarantined=tuple(quarantined),
        checksum=_checksum(observations),
    )
