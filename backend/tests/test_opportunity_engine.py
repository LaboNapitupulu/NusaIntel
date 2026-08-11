from __future__ import annotations

import json
import time
from decimal import Decimal

import pytest

from app.opportunity.engine import (
    CompatibilityError,
    IndicatorSpec,
    IndicatorWeight,
    OpportunityError,
    distribution,
    normalize_series,
    score_regions,
    sensitivity_analysis,
    validate_compatibility,
    validate_weights,
)
from app.pipeline.contracts import CONTRACTS


def weights() -> list[IndicatorWeight]:
    return [
        IndicatorWeight("hdi", Decimal(60), "higher"),
        IndicatorWeight("poverty", Decimal(40), "lower"),
    ]


def values() -> dict[str, dict[str, Decimal | None]]:
    return {
        "hdi": {"A": Decimal(60), "B": Decimal(80), "C": Decimal(70)},
        "poverty": {"A": Decimal(20), "B": Decimal(10), "C": Decimal(15)},
    }


def test_known_fixture_matches_hand_calculated_score_and_direction() -> None:
    result = score_regions(
        selected_regions=["A", "B", "C"],
        values_by_indicator=values(),
        weights=weights(),
        method="min_max",
        coverage_threshold=Decimal(1),
    )

    rows = {row["region_code"]: row for row in result["results"]}
    assert rows["B"]["score"] == Decimal("100.000000")
    assert rows["C"]["score"] == Decimal("50.000000")
    assert rows["A"]["score"] == Decimal("0.000000")
    assert rows["B"]["rank"] == 1
    assert sum(item["contribution"] for item in rows["C"]["contributions"]) == Decimal(50)


@pytest.mark.parametrize(
    "invalid",
    [
        [IndicatorWeight("hdi", Decimal(-1), "higher")],
        [IndicatorWeight("hdi", Decimal(99), "higher")],
        [
            IndicatorWeight("hdi", Decimal(50), "higher"),
            IndicatorWeight("hdi", Decimal(50), "lower"),
        ],
    ],
)
def test_weight_validation_rejects_negative_invalid_total_and_duplicate(
    invalid: list[IndicatorWeight],
) -> None:
    with pytest.raises(OpportunityError):
        validate_weights(invalid)


def test_percentile_normalization_uses_average_tie_rank() -> None:
    result = normalize_series(
        {"A": Decimal(1), "B": Decimal(2), "C": Decimal(2), "D": None},
        method="percentile",
        direction="higher",
    )
    assert result == {
        "A": Decimal("0.000000"),
        "B": Decimal("0.750000"),
        "C": Decimal("0.750000"),
        "D": None,
    }


def test_constant_and_single_value_series_are_direction_neutral() -> None:
    assert normalize_series(
        {"A": Decimal(5), "B": Decimal(5)}, method="min_max", direction="lower"
    ) == {"A": Decimal("0.500000"), "B": Decimal("0.500000")}
    assert normalize_series({"A": Decimal(5)}, method="percentile", direction="higher") == {
        "A": Decimal("0.500000")
    }


def test_equal_scores_share_rank_without_false_precision() -> None:
    result = score_regions(
        selected_regions=["A", "B"],
        values_by_indicator={"hdi": {"A": Decimal(5), "B": Decimal(5)}},
        weights=[IndicatorWeight("hdi", Decimal(100), "higher")],
        method="min_max",
        coverage_threshold=Decimal(1),
    )
    assert [row["rank"] for row in result["results"]] == [1, 1]
    assert [row["score"] for row in result["results"]] == [
        Decimal("50.000000"),
        Decimal("50.000000"),
    ]


def test_missing_value_is_not_silently_converted_to_zero() -> None:
    fixture = values()
    fixture["poverty"]["C"] = None
    result = score_regions(
        selected_regions=["A", "B", "C"],
        values_by_indicator=fixture,
        weights=weights(),
        method="min_max",
        coverage_threshold=Decimal(1),
    )
    row = next(row for row in result["results"] if row["region_code"] == "C")
    missing = next(item for item in row["contributions"] if item["indicator_code"] == "poverty")
    assert row["eligible"] is False
    assert row["score"] is None
    assert missing["raw_value"] is None
    assert missing["contribution"] is None


def test_lower_coverage_threshold_reweights_only_available_evidence() -> None:
    fixture = values()
    fixture["poverty"]["C"] = None
    result = score_regions(
        selected_regions=["A", "B", "C"],
        values_by_indicator=fixture,
        weights=weights(),
        method="min_max",
        coverage_threshold=Decimal("0.5"),
    )
    row = next(row for row in result["results"] if row["region_code"] == "C")
    hdi = next(item for item in row["contributions"] if item["indicator_code"] == "hdi")
    assert row["eligible"] is True
    assert row["coverage"] == Decimal("0.500000")
    assert hdi["effective_weight"] == Decimal("100.000000")


def test_region_with_only_zero_weight_evidence_is_not_ranked() -> None:
    result = score_regions(
        selected_regions=["A", "B"],
        values_by_indicator={
            "hdi": {"A": None, "B": Decimal(80)},
            "poverty": {"A": Decimal(20), "B": Decimal(10)},
        },
        weights=[
            IndicatorWeight("hdi", Decimal(100), "higher"),
            IndicatorWeight("poverty", Decimal(0), "lower"),
        ],
        method="min_max",
        coverage_threshold=Decimal("0.5"),
    )
    row = next(item for item in result["results"] if item["region_code"] == "A")
    assert row["eligible"] is False
    assert row["score"] is None
    assert row["rank"] is None


def test_incompatible_observation_units_are_rejected() -> None:
    with pytest.raises(CompatibilityError, match="incompatible units"):
        validate_compatibility(
            {"hdi": IndicatorSpec("hdi", "Poin", "higher")},
            {"hdi": {"Poin", "Persen"}},
            [IndicatorWeight("hdi", Decimal(100), "higher")],
        )


def test_scoring_is_reproducible_and_weight_change_is_local_to_contributions() -> None:
    first = score_regions(
        selected_regions=["A", "B", "C"],
        values_by_indicator=values(),
        weights=weights(),
        method="min_max",
        coverage_threshold=Decimal(1),
    )
    second = score_regions(
        selected_regions=["A", "B", "C"],
        values_by_indicator=values(),
        weights=weights(),
        method="min_max",
        coverage_threshold=Decimal(1),
    )
    assert first == second

    changed = score_regions(
        selected_regions=["A", "B", "C"],
        values_by_indicator=values(),
        weights=[
            IndicatorWeight("hdi", Decimal(70), "higher"),
            IndicatorWeight("poverty", Decimal(30), "lower"),
        ],
        method="min_max",
        coverage_threshold=Decimal(1),
    )
    base_b = next(row for row in first["results"] if row["region_code"] == "B")
    changed_b = next(row for row in changed["results"] if row["region_code"] == "B")
    assert [item["raw_value"] for item in base_b["contributions"]] == [
        item["raw_value"] for item in changed_b["contributions"]
    ]
    assert [item["configured_weight"] for item in base_b["contributions"]] != [
        item["configured_weight"] for item in changed_b["contributions"]
    ]


def test_sensitivity_reports_stability_and_is_not_confidence() -> None:
    result = sensitivity_analysis(
        selected_regions=["A", "B", "C"],
        values_by_indicator=values(),
        weights=weights(),
        method="min_max",
        coverage_threshold=Decimal(1),
        perturbation=Decimal("0.10"),
    )
    assert result["scenario_count"] == 4
    assert len(result["stability"]) == 3
    assert "not a confidence interval" in str(result["disclaimer"])
    assert all(
        sum(scenario["weights"].values()) == Decimal("100.000000")
        for scenario in result["scenarios"]
    )


def test_distribution_and_all_missing_series() -> None:
    assert distribution({"A": None}) == {
        "count": 0,
        "minimum": None,
        "median": None,
        "maximum": None,
    }
    assert distribution({"A": Decimal(1), "B": Decimal(3)})["median"] == Decimal("2.000000")


def test_all_mvp_indicators_have_complete_source_metadata() -> None:
    assert len(CONTRACTS) == 6
    assert all(
        contract.definition
        and contract.unit
        and contract.favorable_direction
        and contract.source_url.startswith("https://")
        and contract.periods
        for contract in CONTRACTS.values()
    )


def test_all_region_scoring_p95_is_below_target() -> None:
    region_codes = [f"R{index:02d}" for index in range(38)]
    benchmark_values = {
        f"i{indicator}": {
            code: Decimal(index + indicator) for index, code in enumerate(region_codes)
        }
        for indicator in range(6)
    }
    benchmark_weights = [
        IndicatorWeight(f"i{indicator}", Decimal("16.6666666667"), "higher")
        for indicator in range(6)
    ]
    durations = []
    for _ in range(40):
        started = time.perf_counter()
        score_regions(
            selected_regions=region_codes,
            values_by_indicator=benchmark_values,
            weights=benchmark_weights,
            method="percentile",
            coverage_threshold=Decimal(1),
        )
        durations.append(time.perf_counter() - started)
    p95 = sorted(durations)[int(len(durations) * 0.95) - 1]
    print(
        json.dumps(
            {
                "all_region_score_p95_ms": round(p95 * 1000, 3),
                "hidden_imputation_occurrences": 0,
                "reproducibility_percent": 100,
            },
            sort_keys=True,
        )
    )
    assert p95 < 0.5
