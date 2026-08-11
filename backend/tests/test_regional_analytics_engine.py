from __future__ import annotations

from decimal import Decimal

import pytest

from app.regional_analytics.engine import (
    AnalyticsError,
    PreparedFeatures,
    evaluate_clusters,
    feature_set_version,
    prepare_features,
    similar_regions,
)


def fixture_values() -> dict[str, dict[str, Decimal | None]]:
    return {
        "hdi": {
            "A": Decimal("60"),
            "B": Decimal("61"),
            "C": Decimal("80"),
            "D": Decimal("81"),
            "E": Decimal("79"),
            "F": Decimal("59"),
        },
        "poverty": {
            "A": Decimal("20"),
            "B": Decimal("19"),
            "C": Decimal("5"),
            "D": Decimal("4"),
            "E": Decimal("6"),
            "F": Decimal("21"),
        },
        "growth": {
            "A": Decimal("4.0"),
            "B": Decimal("4.1"),
            "C": Decimal("6.0"),
            "D": Decimal("6.1"),
            "E": Decimal("5.9"),
            "F": None,
        },
    }


def prepared_complete() -> PreparedFeatures:
    return prepare_features(
        {code: values for code, values in fixture_values().items() if code != "growth"},
        minimum_feature_coverage=Decimal(1),
    )


def test_preprocessing_excludes_incomplete_feature_without_imputation() -> None:
    prepared = prepare_features(fixture_values(), minimum_feature_coverage=Decimal("0.90"))
    assert prepared.feature_codes == ("hdi", "poverty")
    assert prepared.excluded_features == ("growth",)
    assert prepared.excluded_regions == ()
    assert all(set(row) == {"hdi", "poverty"} for row in prepared.standardized.values())


def test_similarity_is_deterministic_explainable_and_row_order_invariant() -> None:
    prepared = prepared_complete()
    first = similar_regions(prepared, target_region="A", limit=3)
    reversed_values = {
        feature: dict(reversed(list(values.items())))
        for feature, values in reversed(list(fixture_values().items()))
        if feature != "growth"
    }
    reordered = prepare_features(reversed_values, minimum_feature_coverage=Decimal(1))
    second = similar_regions(reordered, target_region="A", limit=3)

    assert first == second
    assert [item["region_code"] for item in first[:2]] == ["B", "F"]
    assert sum(item["distance_share"] for item in first[0]["drivers"]) == Decimal("1.000000")
    assert {item["target_relative_to_candidate"] for item in first[0]["drivers"]} <= {
        "higher",
        "lower",
        "equal",
    }


def test_feature_set_version_binds_versions_preprocessing_and_year() -> None:
    prepared = prepared_complete()
    versions = {
        code: {"version_id": f"version-{code}", "checksum": f"checksum-{code}"}
        for code in prepared.feature_codes
    }
    first = feature_set_version(prepared, year=2024, dataset_versions=versions)
    second = feature_set_version(prepared, year=2024, dataset_versions=versions)
    changed = feature_set_version(prepared, year=2025, dataset_versions=versions)
    assert first == second
    assert first != changed
    assert len(first) == 20


def test_cluster_evaluation_records_silhouette_stability_and_neutral_descriptions() -> None:
    prepared = prepared_complete()
    result = evaluate_clusters(
        prepared,
        candidate_k=[2, 3],
        seeds=[11, 29, 47],
        minimum_silhouette=Decimal("0.10"),
        minimum_stability=Decimal("0.60"),
    )
    assert result["publishable"] is True
    assert result["chosen_k"] == 2
    assert len(result["candidate_evidence"]) == 2
    assert all("silhouette" in row and "stability" in row for row in result["candidate_evidence"])
    assert set(result["assignments"]) == set(prepared.region_codes)
    prohibited = {"buruk", "tertinggal", "terbaik", "terburuk"}
    descriptions = " ".join(item["description"].lower() for item in result["clusters"])
    assert not any(word in descriptions for word in prohibited)


def test_materially_weak_clustering_withholds_membership() -> None:
    constant = {
        "one": {code: Decimal(1) for code in "ABCDEF"},
        "two": {code: Decimal(2) for code in "ABCDEF"},
    }
    prepared = prepare_features(constant, minimum_feature_coverage=Decimal(1))
    result = evaluate_clusters(
        prepared,
        candidate_k=[2, 3],
        seeds=[11, 29],
        minimum_silhouette=Decimal("0.10"),
        minimum_stability=Decimal("0.60"),
    )
    assert result["publishable"] is False
    assert result["assignments"] == {}
    assert result["clusters"] == []
    assert "withheld" in result["validation_message"]


@pytest.mark.parametrize(
    ("values", "threshold", "message"),
    [
        ({"one": {"A": Decimal(1)}}, Decimal(1), "At least two features"),
        (
            {
                "one": {"A": Decimal(1), "B": None, "C": None},
                "two": {"A": Decimal(1), "B": None, "C": None},
            },
            Decimal(1),
            "Fewer than two features",
        ),
    ],
)
def test_invalid_feature_sets_fail_closed(
    values: dict[str, dict[str, Decimal | None]], threshold: Decimal, message: str
) -> None:
    with pytest.raises(AnalyticsError, match=message):
        prepare_features(values, minimum_feature_coverage=threshold)
