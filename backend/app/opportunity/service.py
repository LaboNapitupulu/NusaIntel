from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    CoverageSummary,
    Dataset,
    DatasetVersion,
    GoldRegionalObservation,
    Incident,
    Indicator,
    Region,
    Source,
)
from app.opportunity.engine import (
    CompatibilityError,
    IndicatorSpec,
    IndicatorWeight,
    OpportunityError,
    distribution,
    normalize_matrix,
    score_regions,
    sensitivity_analysis,
    validate_compatibility,
)
from app.opportunity.schemas import ComparisonRequest, ScoreRequest, SensitivityRequest

METHODOLOGY_VERSION = "opportunity-score-v1"


@dataclass(slots=True)
class OpportunityContext:
    specifications: dict[str, IndicatorSpec]
    indicators: dict[str, Indicator]
    values: dict[str, dict[str, Decimal | None]]
    observed_units: dict[str, set[str]]
    versions: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, str]]
    region_names: dict[str, str]


class OpportunityService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def indicator_catalog(self) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            indicators = list(await session.scalars(select(Indicator).order_by(Indicator.code)))
            return [await self._indicator_summary(session, indicator) for indicator in indicators]

    async def region_catalog(self) -> list[dict[str, str]]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(Region)
                .where(
                    Region.level == "province",
                    Region.valid_to.is_(None),
                    Region.code != "9999",
                )
                .order_by(Region.name)
            )
            return [{"code": row.code, "name": row.name} for row in rows]

    async def compare(self, request: ComparisonRequest) -> dict[str, Any]:
        context = await self._load_context(request.indicator_codes, request.year)
        weights = [
            IndicatorWeight(
                code=code,
                weight=Decimal(100) / Decimal(len(request.indicator_codes)),
                direction=context.specifications[code].favorable_direction,
            )
            for code in request.indicator_codes
        ]
        validate_compatibility(context.specifications, context.observed_units, weights)
        self._validate_regions(request.region_codes, context.region_names)
        normalized = normalize_matrix(context.values, weights, request.normalization)

        comparison_rows: list[dict[str, Any]] = []
        for region_code in request.region_codes:
            comparison_rows.append(
                {
                    "region_code": region_code,
                    "region_name": context.region_names[region_code],
                    "values": [
                        {
                            "indicator_code": code,
                            "raw_value": context.values[code].get(region_code),
                            "normalized_value": normalized[code].get(region_code),
                            "unit": context.specifications[code].unit,
                            "reference_period": context.versions[code]["analysis_reference_period"],
                            "missing": context.values[code].get(region_code) is None,
                        }
                        for code in request.indicator_codes
                    ],
                }
            )

        async with self._session_factory() as session:
            trends = await self._trends(
                session,
                request.indicator_codes,
                request.region_codes,
                context.versions,
                context.region_names,
            )
        return {
            "year": request.year,
            "normalization": request.normalization,
            "methodology_version": METHODOLOGY_VERSION,
            "regions": comparison_rows,
            "trends": trends,
            "distributions": {
                code: distribution(context.values[code]) for code in request.indicator_codes
            },
            "dataset_versions": context.versions,
            "sources": context.sources,
        }

    async def score(self, request: ScoreRequest) -> dict[str, Any]:
        weights = self._weights(request)
        context = await self._load_context([item.code for item in weights], request.year)
        validate_compatibility(context.specifications, context.observed_units, weights)
        self._validate_regions(request.region_codes, context.region_names)
        result = score_regions(
            selected_regions=request.region_codes,
            values_by_indicator=context.values,
            weights=weights,
            method=request.normalization,
            coverage_threshold=request.coverage_threshold,
        )
        self._attach_region_names(result, context.region_names)
        return {
            "year": request.year,
            "methodology_version": METHODOLOGY_VERSION,
            "configuration": request.model_dump(mode="json"),
            "dataset_versions": context.versions,
            "sources": context.sources,
            **result,
        }

    async def sensitivity(self, request: SensitivityRequest) -> dict[str, Any]:
        weights = self._weights(request)
        context = await self._load_context([item.code for item in weights], request.year)
        validate_compatibility(context.specifications, context.observed_units, weights)
        self._validate_regions(request.region_codes, context.region_names)
        result = sensitivity_analysis(
            selected_regions=request.region_codes,
            values_by_indicator=context.values,
            weights=weights,
            method=request.normalization,
            coverage_threshold=request.coverage_threshold,
            perturbation=request.perturbation,
        )
        for row in result["base_results"]:
            row["region_name"] = context.region_names[str(row["region_code"])]
        for row in result["stability"]:
            row["region_name"] = context.region_names[str(row["region_code"])]
        return {
            "year": request.year,
            "methodology_version": METHODOLOGY_VERSION,
            "configuration": request.model_dump(mode="json"),
            "dataset_versions": context.versions,
            **result,
        }

    async def export_report(self, request: SensitivityRequest) -> dict[str, Any]:
        score = await self.score(ScoreRequest.model_validate(request.model_dump()))
        sensitivity = await self.sensitivity(request)
        return {
            "report_type": "regional-opportunity-scenario",
            "generated_at": datetime.now(UTC),
            "methodology_version": METHODOLOGY_VERSION,
            "configuration": request.model_dump(mode="json"),
            "dataset_versions": score["dataset_versions"],
            "sources": score["sources"],
            "ranking": score["results"],
            "sensitivity": {
                "perturbation": sensitivity["perturbation"],
                "scenario_count": sensitivity["scenario_count"],
                "stability": sensitivity["stability"],
                "disclaimer": sensitivity["disclaimer"],
            },
            "limitations": [
                "The score represents a user-controlled scenario, not an objective fact.",
                "Missing values are never replaced with zero.",
                "Sensitivity is not a confidence interval and does not imply causality.",
            ],
        }

    async def _indicator_summary(
        self, session: AsyncSession, indicator: Indicator
    ) -> dict[str, Any]:
        dataset = await session.scalar(
            select(Dataset).where(
                Dataset.code == f"{indicator.code}_gold", Dataset.active.is_(True)
            )
        )
        version = await self._latest_published_version(session, dataset.id) if dataset else None
        coverage_rows: list[CoverageSummary] = []
        if version is not None:
            coverage_rows = list(
                await session.scalars(
                    select(CoverageSummary)
                    .where(CoverageSummary.dataset_version_id == version.id)
                    .order_by(CoverageSummary.period)
                )
            )
        open_incidents = 0
        silver_dataset = await session.scalar(
            select(Dataset).where(Dataset.code == f"{indicator.code}_silver")
        )
        if silver_dataset is not None:
            open_incidents = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Incident)
                    .where(
                        Incident.dataset_id == silver_dataset.id,
                        Incident.status.in_(["open", "acknowledged"]),
                    )
                )
                or 0
            )
        minimum_coverage = min(
            (Decimal(row.coverage_percent) for row in coverage_rows), default=Decimal(0)
        )
        quality_status = (
            "critical"
            if open_incidents
            else "healthy"
            if version is not None and minimum_coverage >= Decimal(95)
            else "warning"
        )
        return {
            "code": indicator.code,
            "name": indicator.name,
            "definition": indicator.definition,
            "unit": indicator.unit,
            "favorable_direction": indicator.favorable_direction,
            "source_url": indicator.source_url,
            "reference_period_rule": indicator.reference_period_rule,
            "periods": [
                {
                    "period": row.period,
                    "expected_regions": row.expected_regions,
                    "observed_regions": row.observed_regions,
                    "missing_regions": row.missing_regions,
                    "coverage_percent": row.coverage_percent,
                }
                for row in coverage_rows
            ],
            "quality_status": quality_status,
            "open_incident_count": open_incidents,
            "dataset_version_id": str(version.id) if version else None,
            "dataset_checksum": version.checksum if version else None,
        }

    async def _load_context(self, indicator_codes: list[str], year: int) -> OpportunityContext:
        async with self._session_factory() as session:
            indicators = list(
                await session.scalars(select(Indicator).where(Indicator.code.in_(indicator_codes)))
            )
            by_code = {indicator.code: indicator for indicator in indicators}
            missing = sorted(set(indicator_codes) - set(by_code))
            if missing:
                raise CompatibilityError(f"Unknown indicators: {', '.join(missing)}.")

            regions = list(
                await session.scalars(
                    select(Region).where(
                        Region.level == "province",
                        Region.valid_to.is_(None),
                        Region.code != "9999",
                    )
                )
            )
            region_names = {region.code: region.name for region in regions}
            values: dict[str, dict[str, Decimal | None]] = {}
            observed_units: dict[str, set[str]] = {}
            versions: dict[str, dict[str, Any]] = {}
            sources: dict[str, dict[str, str]] = {}
            specifications: dict[str, IndicatorSpec] = {}

            for code in indicator_codes:
                indicator = by_code[code]
                dataset_row = (
                    await session.execute(
                        select(Dataset, Source)
                        .join(Source, Source.id == Dataset.source_id)
                        .where(Dataset.code == f"{code}_gold", Dataset.active.is_(True))
                    )
                ).one_or_none()
                if dataset_row is None:
                    raise OpportunityError(f"No active Gold dataset for indicator {code}.")
                dataset, source = dataset_row
                version = await self._latest_published_version(session, dataset.id)
                if version is None:
                    raise OpportunityError(f"No published Gold version for indicator {code}.")
                period_start = date(year, 1, 1)
                period_end = date(year, 12, 31)
                observations = list(
                    await session.scalars(
                        select(GoldRegionalObservation).where(
                            GoldRegionalObservation.dataset_version_id == version.id,
                            GoldRegionalObservation.period.between(period_start, period_end),
                            GoldRegionalObservation.is_national_aggregate.is_(False),
                        )
                    )
                )
                if not observations:
                    raise CompatibilityError(
                        f"Indicator {code} has no comparable observations for analysis year {year}."
                    )
                reference_periods = {observation.period for observation in observations}
                if len(reference_periods) != 1:
                    raise CompatibilityError(
                        f"Indicator {code} has multiple reference periods in analysis year {year}."
                    )
                values[code] = {region_code: None for region_code in region_names}
                for observation in observations:
                    if observation.region_code in values[code]:
                        values[code][observation.region_code] = observation.value
                observed_units[code] = {observation.unit for observation in observations}
                specifications[code] = IndicatorSpec(
                    code=code,
                    unit=indicator.unit,
                    favorable_direction=(
                        "lower" if indicator.favorable_direction == "lower" else "higher"
                    ),
                )
                versions[code] = {
                    "dataset_id": str(dataset.id),
                    "dataset_code": dataset.code,
                    "version_id": str(version.id),
                    "checksum": version.checksum,
                    "source_reference_at": version.source_reference_at,
                    "retrieved_at": version.retrieved_at,
                    "analysis_reference_period": next(iter(reference_periods)),
                }
                sources[code] = {
                    "name": source.name,
                    "url": indicator.source_url,
                    "attribution": source.attribution,
                }
            return OpportunityContext(
                specifications=specifications,
                indicators=by_code,
                values=values,
                observed_units=observed_units,
                versions=versions,
                sources=sources,
                region_names=region_names,
            )

    async def _trends(
        self,
        session: AsyncSession,
        indicator_codes: list[str],
        region_codes: list[str],
        versions: dict[str, dict[str, Any]],
        region_names: dict[str, str],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for code in indicator_codes:
            observations = list(
                await session.scalars(
                    select(GoldRegionalObservation)
                    .where(
                        GoldRegionalObservation.dataset_version_id
                        == uuid.UUID(versions[code]["version_id"]),
                        GoldRegionalObservation.region_code.in_(region_codes),
                        GoldRegionalObservation.is_national_aggregate.is_(False),
                    )
                    .order_by(GoldRegionalObservation.region_code, GoldRegionalObservation.period)
                )
            )
            rows.extend(
                {
                    "indicator_code": code,
                    "region_code": observation.region_code,
                    "region_name": region_names[observation.region_code],
                    "period": observation.period,
                    "value": observation.value,
                    "unit": observation.unit,
                    "missing": observation.value is None,
                }
                for observation in observations
            )
        return rows

    async def _latest_published_version(
        self, session: AsyncSession, dataset_id: uuid.UUID
    ) -> DatasetVersion | None:
        version = await session.scalar(
            select(DatasetVersion)
            .where(
                DatasetVersion.dataset_id == dataset_id,
                DatasetVersion.status == "published",
            )
            .order_by(DatasetVersion.processed_at.desc(), DatasetVersion.retrieved_at.desc())
            .limit(1)
        )
        return version

    def _weights(self, request: ScoreRequest) -> list[IndicatorWeight]:
        return [
            IndicatorWeight(code=item.code, weight=item.weight, direction=item.direction)
            for item in request.indicators
        ]

    def _validate_regions(self, region_codes: list[str], region_names: dict[str, str]) -> None:
        unknown = sorted(set(region_codes) - set(region_names))
        if unknown:
            raise OpportunityError(f"Unknown regions: {', '.join(unknown)}.")

    def _attach_region_names(self, result: dict[str, Any], region_names: dict[str, str]) -> None:
        for row in result["results"]:
            row["region_name"] = region_names[str(row["region_code"])]
