from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.opportunity.engine import OpportunityError
from app.opportunity.service import OpportunityContext, OpportunityService
from app.pipeline.contracts import CONTRACTS
from app.regional_analytics.engine import (
    METHODOLOGY_VERSION,
    PREPROCESSING_VERSION,
    PreparedFeatures,
    evaluate_clusters,
    feature_set_version,
    prepare_features,
    similar_regions,
)
from app.regional_analytics.schemas import (
    AnalyticsReportRequest,
    ClusterRequest,
    FeatureSetRequest,
    SimilarityRequest,
)


class RegionalAnalyticsService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._opportunity = OpportunityService(session_factory)

    async def similarity(self, request: SimilarityRequest) -> dict[str, Any]:
        context, prepared, version = await self._prepare(request)
        if request.target_region_code not in context.region_names:
            raise OpportunityError(f"Unknown region: {request.target_region_code}.")
        results = similar_regions(
            prepared,
            target_region=request.target_region_code,
            limit=request.limit,
        )
        for row in results:
            row["region_name"] = context.region_names[str(row["region_code"])]
            for driver in row["drivers"]:
                code = str(driver["indicator_code"])
                driver.update(self._feature_metadata(context, code))
        return {
            **self._evidence(context, prepared, version, request),
            "target_region_code": request.target_region_code,
            "target_region_name": context.region_names[request.target_region_code],
            "results": results,
        }

    async def clusters(self, request: ClusterRequest) -> dict[str, Any]:
        context, prepared, version = await self._prepare(request)
        result = evaluate_clusters(
            prepared,
            candidate_k=request.candidate_k,
            seeds=request.seeds,
            minimum_silhouette=request.minimum_silhouette,
            minimum_stability=request.minimum_stability,
        )
        assignments = result["assignments"]
        result["assignments"] = [
            {
                "region_code": region,
                "region_name": context.region_names[region],
                "cluster_id": assignments[region],
            }
            for region in sorted(assignments)
        ]
        for cluster in result["clusters"]:
            cluster["regions"] = [
                {"code": code, "name": context.region_names[code]}
                for code in cluster.pop("region_codes")
            ]
            cluster["feature_deviations"] = [
                {
                    "indicator_code": code,
                    "standardized_deviation": value,
                    **self._feature_metadata(context, code),
                }
                for code, value in cluster["feature_deviations"].items()
            ]
        return {**self._evidence(context, prepared, version, request), **result}

    async def report(self, request: AnalyticsReportRequest) -> dict[str, Any]:
        similarity = await self.similarity(
            SimilarityRequest.model_validate(
                request.model_dump(
                    include={
                        "indicator_codes",
                        "year",
                        "minimum_feature_coverage",
                        "target_region_code",
                        "limit",
                    }
                )
            )
        )
        clusters = await self.clusters(
            ClusterRequest.model_validate(
                request.model_dump(
                    include={
                        "indicator_codes",
                        "year",
                        "minimum_feature_coverage",
                        "candidate_k",
                        "seeds",
                        "minimum_silhouette",
                        "minimum_stability",
                    }
                )
            )
        )
        detail = await self.region_detail(request.target_region_code, request.year)
        map_feature = request.indicator_codes[0]
        context = await self._opportunity.load_context(request.indicator_codes, request.year)
        return {
            "report_type": "regional-analytics-report",
            "generated_at": datetime.now(UTC),
            "methodology_version": METHODOLOGY_VERSION,
            "configuration": request.model_dump(mode="json"),
            "target_region": detail,
            "similarity": similarity,
            "clustering": clusters,
            "map": {
                "representation": "schematic-province-tile-choropleth-v1",
                "indicator_code": map_feature,
                **self._feature_metadata(context, map_feature),
                "values": [
                    {
                        "region_code": code,
                        "region_name": context.region_names[code],
                        "value": context.values[map_feature][code],
                    }
                    for code in sorted(context.region_names)
                ],
                "disclaimer": (
                    "Tile positions are schematic and are not official administrative boundaries."
                ),
            },
            "citations": [
                {
                    "indicator_code": code,
                    **self._feature_metadata(context, code),
                    "dataset_version": context.versions[code],
                }
                for code in request.indicator_codes
            ],
            "limitations": [
                "Similarity and clustering describe standardized feature profiles, not causality.",
                (
                    "Missing observations are excluded through complete-case analysis; "
                    "no zero-fill is used."
                ),
                "Cluster membership is withheld when validation is materially weak.",
                "Cluster descriptions are neutral evidence summaries, not normative labels.",
                "The map is a schematic tile layout, not an authoritative boundary map.",
            ],
        }

    async def region_detail(self, region_code: str, year: int) -> dict[str, Any]:
        indicator_codes = sorted(CONTRACTS)
        context = await self._opportunity.load_context(indicator_codes, year)
        if region_code not in context.region_names:
            raise OpportunityError(f"Unknown region: {region_code}.")
        return {
            "region_code": region_code,
            "region_name": context.region_names[region_code],
            "year": year,
            "indicators": [
                {
                    "indicator_code": code,
                    "value": context.values[code][region_code],
                    "missing": context.values[code][region_code] is None,
                    "dataset_version": context.versions[code],
                    **self._feature_metadata(context, code),
                }
                for code in indicator_codes
            ],
        }

    async def _prepare(
        self, request: FeatureSetRequest
    ) -> tuple[OpportunityContext, PreparedFeatures, str]:
        context = await self._opportunity.load_context(request.indicator_codes, request.year)
        prepared = prepare_features(
            context.values,
            minimum_feature_coverage=request.minimum_feature_coverage,
        )
        version = feature_set_version(
            prepared,
            year=request.year,
            dataset_versions=context.versions,
        )
        return context, prepared, version

    def _evidence(
        self,
        context: OpportunityContext,
        prepared: PreparedFeatures,
        version: str,
        request: FeatureSetRequest,
    ) -> dict[str, Any]:
        return {
            "year": request.year,
            "methodology_version": METHODOLOGY_VERSION,
            "feature_set_version": version,
            "preprocessing_version": PREPROCESSING_VERSION,
            "configuration": request.model_dump(mode="json"),
            "selected_features": [
                {
                    "indicator_code": code,
                    "coverage": prepared.feature_coverage[code],
                    "mean": prepared.preprocessing[code]["mean"],
                    "scale": prepared.preprocessing[code]["scale"],
                    "dataset_version": context.versions[code],
                    **self._feature_metadata(context, code),
                }
                for code in prepared.feature_codes
            ],
            "excluded_features": list(prepared.excluded_features),
            "excluded_regions": [
                {"code": code, "name": context.region_names[code]}
                for code in prepared.excluded_regions
            ],
            "eligible_region_count": len(prepared.region_codes),
        }

    def _feature_metadata(self, context: OpportunityContext, code: str) -> dict[str, Any]:
        indicator = context.indicators[code]
        return {
            "indicator_name": indicator.name,
            "definition": indicator.definition,
            "unit": indicator.unit,
            "source": context.sources[code],
            "reference_period": context.versions[code]["analysis_reference_period"],
        }
