from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Any, Literal

NormalizationMethod = Literal["min_max", "percentile"]
Direction = Literal["higher", "lower"]
SIX_PLACES = Decimal("0.000001")
WEIGHT_TOLERANCE = Decimal("0.01")


class OpportunityError(ValueError):
    """Raised when a scoring request cannot be evaluated transparently."""


class CompatibilityError(OpportunityError):
    """Raised when indicator metadata and observations are incompatible."""


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    code: str
    unit: str
    favorable_direction: Direction


@dataclass(frozen=True, slots=True)
class IndicatorWeight:
    code: str
    weight: Decimal
    direction: Direction


def rounded(value: Decimal) -> Decimal:
    return value.quantize(SIX_PLACES, rounding=ROUND_HALF_UP)


def validate_weights(weights: list[IndicatorWeight]) -> None:
    if not weights:
        raise OpportunityError("At least one indicator is required.")
    codes = [item.code for item in weights]
    if len(codes) != len(set(codes)):
        raise OpportunityError("Indicator codes must be unique.")
    if any(item.weight < 0 for item in weights):
        raise OpportunityError("Weights cannot be negative.")
    total = sum((item.weight for item in weights), Decimal(0))
    if abs(total - Decimal(100)) > WEIGHT_TOLERANCE:
        raise OpportunityError("Weights must sum to 100 percent within 0.01 tolerance.")


def validate_compatibility(
    specifications: dict[str, IndicatorSpec],
    observed_units: dict[str, set[str]],
    weights: list[IndicatorWeight],
) -> None:
    for item in weights:
        specification = specifications.get(item.code)
        if specification is None:
            raise CompatibilityError(f"Unknown indicator: {item.code}.")
        units = observed_units.get(item.code, set())
        if units and units != {specification.unit}:
            raise CompatibilityError(
                f"Indicator {item.code} mixes incompatible units: {sorted(units)}."
            )


def normalize_series(
    values: dict[str, Decimal | None],
    *,
    method: NormalizationMethod,
    direction: Direction,
) -> dict[str, Decimal | None]:
    present = {key: value for key, value in values.items() if value is not None}
    result: dict[str, Decimal | None] = {key: None for key in values}
    if not present:
        return result

    if method == "min_max":
        low = min(present.values())
        high = max(present.values())
        span = high - low
        for key, value in present.items():
            normalized = Decimal("0.5") if span == 0 else (value - low) / span
            result[key] = rounded(normalized if direction == "higher" else 1 - normalized)
        return result

    if method != "percentile":
        raise OpportunityError(f"Unsupported normalization method: {method}.")

    ordered = sorted(present.items(), key=lambda item: (item[1], item[0]))
    denominator = Decimal(max(len(ordered) - 1, 1))
    cursor = 0
    while cursor < len(ordered):
        end = cursor + 1
        while end < len(ordered) and ordered[end][1] == ordered[cursor][1]:
            end += 1
        average_rank = Decimal(cursor + end - 1) / Decimal(2)
        percentile = Decimal("0.5") if len(ordered) == 1 else average_rank / denominator
        normalized = percentile if direction == "higher" else 1 - percentile
        for index in range(cursor, end):
            result[ordered[index][0]] = rounded(normalized)
        cursor = end
    return result


def normalize_matrix(
    values_by_indicator: dict[str, dict[str, Decimal | None]],
    weights: list[IndicatorWeight],
    method: NormalizationMethod,
) -> dict[str, dict[str, Decimal | None]]:
    return {
        item.code: normalize_series(
            values_by_indicator[item.code], method=method, direction=item.direction
        )
        for item in weights
    }


def score_regions(
    *,
    selected_regions: list[str],
    values_by_indicator: dict[str, dict[str, Decimal | None]],
    weights: list[IndicatorWeight],
    method: NormalizationMethod,
    coverage_threshold: Decimal,
) -> dict[str, Any]:
    validate_weights(weights)
    if not Decimal(0) <= coverage_threshold <= Decimal(1):
        raise OpportunityError("Coverage threshold must be between 0 and 1.")
    if len(selected_regions) < 2 or len(selected_regions) > 38:
        raise OpportunityError("Select between 2 and 38 regions for scoring.")
    if len(selected_regions) != len(set(selected_regions)):
        raise OpportunityError("Region codes must be unique.")
    missing_series = [item.code for item in weights if item.code not in values_by_indicator]
    if missing_series:
        raise OpportunityError(f"Missing indicator series: {', '.join(missing_series)}.")

    normalized = normalize_matrix(values_by_indicator, weights, method)
    rows: list[dict[str, object]] = []
    indicator_count = Decimal(len(weights))
    for region_code in selected_regions:
        available = [
            item
            for item in weights
            if values_by_indicator[item.code].get(region_code) is not None
            and normalized[item.code].get(region_code) is not None
        ]
        coverage = Decimal(len(available)) / indicator_count
        available_weight = sum((item.weight for item in available), Decimal(0))
        eligible = coverage >= coverage_threshold and available_weight > 0
        contributions: list[dict[str, object]] = []
        score = Decimal(0)
        for item in weights:
            raw_value = values_by_indicator[item.code].get(region_code)
            normalized_value = normalized[item.code].get(region_code)
            included = item in available and eligible and available_weight > 0
            effective_weight = item.weight / available_weight * Decimal(100) if included else None
            contribution = (
                normalized_value * effective_weight
                if included and normalized_value is not None and effective_weight is not None
                else None
            )
            if contribution is not None:
                score += contribution
            contributions.append(
                {
                    "indicator_code": item.code,
                    "raw_value": raw_value,
                    "normalized_value": normalized_value,
                    "configured_weight": rounded(item.weight),
                    "effective_weight": (
                        rounded(effective_weight) if effective_weight is not None else None
                    ),
                    "contribution": rounded(contribution) if contribution is not None else None,
                    "direction": item.direction,
                    "missing": raw_value is None,
                }
            )
        rows.append(
            {
                "region_code": region_code,
                "coverage": rounded(coverage),
                "eligible": eligible,
                "score": rounded(score) if eligible else None,
                "rank": None,
                "contributions": contributions,
            }
        )

    ranked = sorted(
        (row for row in rows if row["score"] is not None),
        key=lambda row: (-Decimal(str(row["score"])), str(row["region_code"])),
    )
    previous_score: Decimal | None = None
    previous_rank = 0
    for position, row in enumerate(ranked, start=1):
        current_score = Decimal(str(row["score"]))
        if current_score != previous_score:
            previous_rank = position
            previous_score = current_score
        row["rank"] = previous_rank
    ordered_rows = ranked + sorted(
        (row for row in rows if row["score"] is None), key=lambda row: str(row["region_code"])
    )
    return {
        "normalization": method,
        "coverage_threshold": rounded(coverage_threshold),
        "results": ordered_rows,
        "normalized": normalized,
    }


def sensitivity_analysis(
    *,
    selected_regions: list[str],
    values_by_indicator: dict[str, dict[str, Decimal | None]],
    weights: list[IndicatorWeight],
    method: NormalizationMethod,
    coverage_threshold: Decimal,
    perturbation: Decimal,
) -> dict[str, Any]:
    if not Decimal(0) < perturbation <= Decimal("0.5"):
        raise OpportunityError("Sensitivity perturbation must be above 0 and at most 0.5.")
    base = score_regions(
        selected_regions=selected_regions,
        values_by_indicator=values_by_indicator,
        weights=weights,
        method=method,
        coverage_threshold=coverage_threshold,
    )
    base_ranks = {
        str(row["region_code"]): int(row["rank"])
        for row in base["results"]
        if row["rank"] is not None
    }
    scenarios: list[dict[str, Any]] = []
    rank_samples: dict[str, list[int]] = {code: [] for code in selected_regions}
    for target in weights:
        for sign, label in ((Decimal(-1), "decrease"), (Decimal(1), "increase")):
            adjusted_values = {
                item.code: item.weight * (1 + sign * perturbation)
                if item.code == target.code
                else item.weight
                for item in weights
            }
            adjusted_total = sum(adjusted_values.values(), Decimal(0))
            adjusted = [
                IndicatorWeight(
                    code=item.code,
                    weight=adjusted_values[item.code] / adjusted_total * Decimal(100),
                    direction=item.direction,
                )
                for item in weights
            ]
            outcome = score_regions(
                selected_regions=selected_regions,
                values_by_indicator=values_by_indicator,
                weights=adjusted,
                method=method,
                coverage_threshold=coverage_threshold,
            )
            ranks = {
                str(row["region_code"]): int(row["rank"])
                for row in outcome["results"]
                if row["rank"] is not None
            }
            for region_code, rank in ranks.items():
                rank_samples[region_code].append(rank)
            scenarios.append(
                {
                    "indicator_code": target.code,
                    "change": label,
                    "weights": {item.code: rounded(item.weight) for item in adjusted},
                    "ranks": ranks,
                }
            )

    stability: list[dict[str, Any]] = []
    scenario_count = len(scenarios)
    for region_code in selected_regions:
        sample_ranks = rank_samples[region_code]
        base_rank = base_ranks.get(region_code)
        unchanged = sum(rank == base_rank for rank in sample_ranks) if base_rank is not None else 0
        stability.append(
            {
                "region_code": region_code,
                "base_rank": base_rank,
                "min_rank": min(sample_ranks) if sample_ranks else None,
                "max_rank": max(sample_ranks) if sample_ranks else None,
                "max_absolute_shift": (
                    max(abs(rank - base_rank) for rank in sample_ranks)
                    if sample_ranks and base_rank is not None
                    else None
                ),
                "unchanged_percent": (
                    rounded(Decimal(unchanged) / Decimal(scenario_count) * Decimal(100))
                    if scenario_count
                    else None
                ),
            }
        )
    stability.sort(
        key=lambda item: (-(int(item["max_absolute_shift"] or 0)), str(item["region_code"]))
    )
    return {
        "perturbation": rounded(perturbation),
        "scenario_count": scenario_count,
        "base_results": base["results"],
        "stability": stability,
        "scenarios": scenarios,
        "disclaimer": (
            "Sensitivity shows rank response to weight changes; it is not a confidence "
            "interval and does not imply causality."
        ),
    }


def distribution(values: dict[str, Decimal | None]) -> dict[str, Decimal | int | None]:
    present = sorted(value for value in values.values() if value is not None)
    if not present:
        return {"count": 0, "minimum": None, "median": None, "maximum": None}
    return {
        "count": len(present),
        "minimum": rounded(present[0]),
        "median": rounded(Decimal(str(median(present)))),
        "maximum": rounded(present[-1]),
    }
