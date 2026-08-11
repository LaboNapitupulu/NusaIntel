from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from typing import Any

SIX_PLACES = Decimal("0.000001")
PREPROCESSING_VERSION = "zscore-complete-case-v1"
METHODOLOGY_VERSION = "regional-analytics-v1"


class AnalyticsError(ValueError):
    """Raised when analytics cannot be evaluated transparently."""


def rounded(value: Decimal) -> Decimal:
    return value.quantize(SIX_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class PreparedFeatures:
    feature_codes: tuple[str, ...]
    region_codes: tuple[str, ...]
    raw_values: dict[str, dict[str, Decimal | None]]
    standardized: dict[str, dict[str, Decimal]]
    preprocessing: dict[str, dict[str, Decimal]]
    feature_coverage: dict[str, Decimal]
    excluded_features: tuple[str, ...]
    excluded_regions: tuple[str, ...]


def prepare_features(
    values_by_feature: dict[str, dict[str, Decimal | None]],
    *,
    minimum_feature_coverage: Decimal,
) -> PreparedFeatures:
    if not Decimal(0) < minimum_feature_coverage <= Decimal(1):
        raise AnalyticsError("Minimum feature coverage must be above 0 and at most 1.")
    if len(values_by_feature) < 2:
        raise AnalyticsError("At least two features are required.")

    feature_codes = sorted(values_by_feature)
    region_sets = [set(values_by_feature[code]) for code in feature_codes]
    if not region_sets or any(regions != region_sets[0] for regions in region_sets[1:]):
        raise AnalyticsError("All features must cover the same region universe explicitly.")
    all_regions = sorted(region_sets[0])
    if len(all_regions) < 3:
        raise AnalyticsError("At least three regions are required.")

    denominator = Decimal(len(all_regions))
    coverage = {
        code: rounded(
            Decimal(sum(values_by_feature[code][region] is not None for region in all_regions))
            / denominator
        )
        for code in feature_codes
    }
    selected = [code for code in feature_codes if coverage[code] >= minimum_feature_coverage]
    excluded_features = tuple(code for code in feature_codes if code not in selected)
    if len(selected) < 2:
        raise AnalyticsError("Fewer than two features meet the configured completeness threshold.")

    eligible_regions = [
        region
        for region in all_regions
        if all(values_by_feature[code][region] is not None for code in selected)
    ]
    excluded_regions = tuple(region for region in all_regions if region not in eligible_regions)
    if len(eligible_regions) < 3:
        raise AnalyticsError("Fewer than three complete-case regions remain for analytics.")

    preprocessing: dict[str, dict[str, Decimal]] = {}
    standardized: dict[str, dict[str, Decimal]] = {region: {} for region in eligible_regions}
    for code in selected:
        present = [values_by_feature[code][region] for region in eligible_regions]
        numeric = [value for value in present if value is not None]
        mean = sum(numeric, Decimal(0)) / Decimal(len(numeric))
        variance = sum(((value - mean) ** 2 for value in numeric), Decimal(0)) / Decimal(
            len(numeric)
        )
        scale = variance.sqrt() if variance > 0 else Decimal(1)
        preprocessing[code] = {"mean": rounded(mean), "scale": rounded(scale)}
        for region in eligible_regions:
            value = values_by_feature[code][region]
            if value is None:  # guarded by complete-case selection
                raise AnalyticsError("Missing value reached deterministic preprocessing.")
            standardized[region][code] = rounded((value - mean) / scale)

    return PreparedFeatures(
        feature_codes=tuple(selected),
        region_codes=tuple(eligible_regions),
        raw_values=values_by_feature,
        standardized=standardized,
        preprocessing=preprocessing,
        feature_coverage=coverage,
        excluded_features=excluded_features,
        excluded_regions=excluded_regions,
    )


def feature_set_version(
    prepared: PreparedFeatures,
    *,
    year: int,
    dataset_versions: dict[str, dict[str, Any]],
) -> str:
    payload = {
        "year": year,
        "preprocessing_version": PREPROCESSING_VERSION,
        "features": [
            {
                "code": code,
                "version_id": dataset_versions[code]["version_id"],
                "checksum": dataset_versions[code]["checksum"],
                "mean": str(prepared.preprocessing[code]["mean"]),
                "scale": str(prepared.preprocessing[code]["scale"]),
            }
            for code in prepared.feature_codes
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:20]


def similar_regions(
    prepared: PreparedFeatures,
    *,
    target_region: str,
    limit: int,
) -> list[dict[str, Any]]:
    if target_region not in prepared.standardized:
        raise AnalyticsError("Target region is not eligible for complete-case similarity.")
    if limit < 1 or limit > 10:
        raise AnalyticsError("Similarity limit must be between 1 and 10.")

    target = prepared.standardized[target_region]
    results: list[dict[str, Any]] = []
    for region in prepared.region_codes:
        if region == target_region:
            continue
        squared = {
            code: (target[code] - prepared.standardized[region][code]) ** 2
            for code in prepared.feature_codes
        }
        total = sum(squared.values(), Decimal(0))
        distance = (total / Decimal(len(prepared.feature_codes))).sqrt()
        drivers = []
        for code in prepared.feature_codes:
            raw_target = prepared.raw_values[code][target_region]
            raw_candidate = prepared.raw_values[code][region]
            if raw_target is None or raw_candidate is None:
                raise AnalyticsError("Missing value reached similarity explanation.")
            difference = raw_target - raw_candidate
            drivers.append(
                {
                    "indicator_code": code,
                    "target_value": raw_target,
                    "candidate_value": raw_candidate,
                    "standardized_gap": rounded(
                        abs(target[code] - prepared.standardized[region][code])
                    ),
                    "distance_share": (rounded(squared[code] / total) if total > 0 else Decimal(0)),
                    "target_relative_to_candidate": (
                        "higher" if difference > 0 else "lower" if difference < 0 else "equal"
                    ),
                }
            )
        drivers.sort(key=lambda row: (-Decimal(str(row["distance_share"])), row["indicator_code"]))
        results.append(
            {
                "region_code": region,
                "distance": rounded(distance),
                "drivers": drivers,
            }
        )
    results.sort(key=lambda row: (Decimal(str(row["distance"])), str(row["region_code"])))
    return results[:limit]


def _euclidean(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)))


def _canonicalize_labels(
    points: dict[str, tuple[float, ...]], labels: dict[str, int], k: int
) -> dict[str, int]:
    centroids: list[tuple[int, tuple[float, ...]]] = []
    for cluster in range(k):
        members = [points[code] for code in sorted(points) if labels[code] == cluster]
        centroid = tuple(
            sum(row[index] for row in members) / len(members) for index in range(len(members[0]))
        )
        centroids.append((cluster, centroid))
    remap = {
        old: new
        for new, (old, _) in enumerate(sorted(centroids, key=lambda item: item[1]), start=1)
    }
    return {code: remap[label] for code, label in labels.items()}


def _cluster_once(points: dict[str, tuple[float, ...]], *, k: int, seed: int) -> dict[str, int]:
    region_codes = sorted(points)
    first = min(
        region_codes,
        key=lambda code: hashlib.sha256(f"{seed}:{code}".encode()).hexdigest(),
    )
    centroid_codes = [first]
    while len(centroid_codes) < k:
        candidates = [code for code in region_codes if code not in centroid_codes]
        next_code = max(
            candidates,
            key=lambda code: (
                min(_euclidean(points[code], points[current]) for current in centroid_codes),
                code,
            ),
        )
        centroid_codes.append(next_code)
    centroids = [points[code] for code in centroid_codes]
    labels: dict[str, int] = {}

    for _ in range(100):
        next_labels = {
            code: min(
                range(k),
                key=lambda cluster: (_euclidean(points[code], centroids[cluster]), cluster),
            )
            for code in region_codes
        }
        if next_labels == labels:
            break
        labels = next_labels
        next_centroids: list[tuple[float, ...]] = []
        for cluster in range(k):
            members = [points[code] for code in region_codes if labels[code] == cluster]
            if not members:
                counts = Counter(labels.values())
                replacement_candidates = [code for code in region_codes if counts[labels[code]] > 1]
                if not replacement_candidates:
                    raise AnalyticsError("Clustering could not produce non-empty clusters.")
                replacement = max(
                    replacement_candidates,
                    key=lambda code: (
                        _euclidean(points[code], centroids[labels[code]]),
                        code,
                    ),
                )
                members = [points[replacement]]
                labels[replacement] = cluster
            next_centroids.append(
                tuple(
                    sum(row[index] for row in members) / len(members)
                    for index in range(len(members[0]))
                )
            )
        centroids = next_centroids
    return _canonicalize_labels(points, labels, k)


def _silhouette(points: dict[str, tuple[float, ...]], labels: dict[str, int]) -> float:
    scores: list[float] = []
    for code in sorted(points):
        own = [other for other in points if labels[other] == labels[code] and other != code]
        if not own:
            scores.append(0.0)
            continue
        a = sum(_euclidean(points[code], points[other]) for other in own) / len(own)
        other_clusters = sorted(set(labels.values()) - {labels[code]})
        b = min(
            sum(
                _euclidean(points[code], points[other])
                for other in points
                if labels[other] == cluster
            )
            / sum(labels[other] == cluster for other in points)
            for cluster in other_clusters
        )
        scores.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return sum(scores) / len(scores)


def _comb2(value: int) -> float:
    return value * (value - 1) / 2


def _adjusted_rand(left: dict[str, int], right: dict[str, int]) -> float:
    codes = sorted(left)
    contingency = Counter((left[code], right[code]) for code in codes)
    left_counts = Counter(left.values())
    right_counts = Counter(right.values())
    pairs = sum(_comb2(count) for count in contingency.values())
    left_pairs = sum(_comb2(count) for count in left_counts.values())
    right_pairs = sum(_comb2(count) for count in right_counts.values())
    total_pairs = _comb2(len(codes))
    expected = left_pairs * right_pairs / total_pairs if total_pairs else 0.0
    maximum = (left_pairs + right_pairs) / 2
    return (pairs - expected) / (maximum - expected) if maximum != expected else 1.0


def _cluster_descriptions(
    prepared: PreparedFeatures, assignments: dict[str, int]
) -> list[dict[str, Any]]:
    descriptions = []
    for cluster in sorted(set(assignments.values())):
        members = sorted(code for code, assigned in assignments.items() if assigned == cluster)
        deviations = []
        for feature in prepared.feature_codes:
            mean = sum(
                (prepared.standardized[region][feature] for region in members), Decimal(0)
            ) / Decimal(len(members))
            deviations.append((feature, rounded(mean)))
        notable = [item for item in deviations if abs(item[1]) >= Decimal("0.35")]
        notable.sort(key=lambda item: (-abs(item[1]), item[0]))
        if notable:
            phrases = [
                f"{code} relatif {'lebih tinggi' if value > 0 else 'lebih rendah'}"
                for code, value in notable[:3]
            ]
            description = "; ".join(phrases) + " dibanding rata-rata feature set."
        else:
            description = "Profil fitur berada dekat rata-rata feature set."
        descriptions.append(
            {
                "cluster_id": cluster,
                "member_count": len(members),
                "region_codes": members,
                "description": description,
                "feature_deviations": dict(deviations),
            }
        )
    return descriptions


def evaluate_clusters(
    prepared: PreparedFeatures,
    *,
    candidate_k: list[int],
    seeds: list[int],
    minimum_silhouette: Decimal,
    minimum_stability: Decimal,
) -> dict[str, Any]:
    if not seeds or len(seeds) < 2:
        raise AnalyticsError("At least two deterministic seeds are required.")
    valid_k = sorted(set(candidate_k))
    if not valid_k or any(k < 2 or k >= len(prepared.region_codes) for k in valid_k):
        raise AnalyticsError("Candidate k must be unique and between 2 and region count minus 1.")
    if not Decimal(-1) <= minimum_silhouette <= Decimal(1):
        raise AnalyticsError("Minimum silhouette must be between -1 and 1.")
    if not Decimal(0) <= minimum_stability <= Decimal(1):
        raise AnalyticsError("Minimum stability must be between 0 and 1.")

    points = {
        region: tuple(float(prepared.standardized[region][code]) for code in prepared.feature_codes)
        for region in prepared.region_codes
    }
    evidence: list[dict[str, Any]] = []
    runs_by_k: dict[int, list[dict[str, int]]] = {}
    for k in valid_k:
        runs = [_cluster_once(points, k=k, seed=seed) for seed in seeds]
        runs_by_k[k] = runs
        silhouettes = [_silhouette(points, run) for run in runs]
        stability_values = [
            max(0.0, _adjusted_rand(left, right)) for left, right in combinations(runs, 2)
        ]
        evidence.append(
            {
                "k": k,
                "silhouette": rounded(Decimal(str(sum(silhouettes) / len(silhouettes)))),
                "stability": rounded(
                    Decimal(str(sum(stability_values) / len(stability_values)))
                    if stability_values
                    else Decimal(1)
                ),
                "minimum_cluster_size": min(Counter(runs[0].values()).values()),
            }
        )
    chosen = max(evidence, key=lambda row: (Decimal(str(row["silhouette"])), -int(row["k"])))
    publishable = (
        Decimal(str(chosen["silhouette"])) >= minimum_silhouette
        and Decimal(str(chosen["stability"])) >= minimum_stability
        and int(chosen["minimum_cluster_size"]) >= 2
    )
    assignments = runs_by_k[int(chosen["k"])][0] if publishable else {}
    return {
        "candidate_evidence": evidence,
        "chosen_k": int(chosen["k"]),
        "publishable": publishable,
        "validation_message": (
            "Cluster membership is exposed because silhouette, stability, and minimum size pass."
            if publishable
            else "Cluster membership is withheld because validation is materially weak."
        ),
        "assignments": assignments,
        "clusters": _cluster_descriptions(prepared, assignments) if publishable else [],
    }
