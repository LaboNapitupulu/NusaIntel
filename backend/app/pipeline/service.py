from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    CoverageSummary,
    DataContract,
    Dataset,
    DatasetVersion,
    GoldRegionalObservation,
    Indicator,
    LineageEdge,
    Observation,
    PipelineRun,
    QualityCheckResult,
    QuarantineRecord,
    RawPayload,
    Region,
    Source,
)
from app.pipeline.contracts import IndicatorContract
from app.pipeline.normalize import normalize_payload
from app.pipeline.quality import evaluate_quality
from app.pipeline.types import PipelineOutcome, RetrievedPayload

TRANSFORMATION_VERSION = "bps-medallion-v1"


def _contract_specification(contract: IndicatorContract) -> dict[str, Any]:
    return {
        "code": contract.code,
        "favorable_direction": contract.favorable_direction,
        "periods": [asdict(period) for period in contract.periods],
        "regions": [asdict(region) for region in contract.regions],
        "unit": contract.unit,
        "variable_id": contract.bps_variable_id,
        "derived_variable_id": contract.bps_derived_variable_id,
        "derived_period_id": contract.bps_derived_period_id,
        "send_derived_variable_parameter": contract.send_derived_variable_parameter,
    }


def _json_checksum(value: dict[str, Any]) -> str:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


class PipelineService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def run(
        self,
        retrieved: RetrievedPayload,
        contract: IndicatorContract,
    ) -> PipelineOutcome:
        bronze_version_id = await self._persist_bronze(retrieved, contract)
        existing = await self._published_outcome(bronze_version_id, retrieved, contract)
        if existing is not None:
            return existing

        batch = normalize_payload(retrieved, contract)
        report = evaluate_quality(batch, contract)
        now = datetime.now(UTC)
        run_id = uuid.uuid4()

        async with self._session_factory() as session, session.begin():
            datasets = await self._ensure_catalog(session, contract)
            await self._ensure_dimensions(session, contract)
            silver_version = await self._get_or_create_version(
                session,
                dataset_id=datasets["silver"].id,
                source_identity=retrieved.source_identity,
                checksum=batch.checksum,
                retrieved_at=retrieved.retrieved_at,
                row_count=len(batch.observations),
                status="validated" if report.publishable else "rejected",
                processed_at=now,
            )
            run = PipelineRun(
                id=run_id,
                dataset_version_id=silver_version.id,
                run_type="bps_ingestion",
                status="running",
                started_at=now,
                correlation_id=str(uuid.uuid4()),
            )
            session.add(run)
            await session.flush()

            has_silver_rows = await session.scalar(
                select(Observation.id)
                .where(Observation.dataset_version_id == silver_version.id)
                .limit(1)
            )
            if has_silver_rows is None:
                session.add_all(
                    [
                        Observation(
                            region_code=row.region_code,
                            indicator_code=row.indicator_code,
                            dataset_version_id=silver_version.id,
                            period=row.period,
                            observation_key=row.observation_key,
                            value=row.value,
                            source_value=row.source_value,
                            value_status=row.value_status,
                            source_note=None,
                            is_national_aggregate=row.is_national_aggregate,
                        )
                        for row in batch.observations
                    ]
                )

            for check in report.checks:
                session.add(
                    QualityCheckResult(
                        dataset_version_id=silver_version.id,
                        pipeline_run_id=run.id,
                        check_code=check.code,
                        severity=check.severity,
                        status="passed" if check.passed else "failed",
                        expected=check.expected,
                        observed=check.observed,
                        safe_sample=list(check.safe_sample) or None,
                    )
                )

            for row in batch.quarantined:
                existing_quarantine = await session.scalar(
                    select(QuarantineRecord.id).where(
                        QuarantineRecord.dataset_version_id == silver_version.id,
                        QuarantineRecord.source_key == row.source_key,
                        QuarantineRecord.reason_code == row.reason_code,
                    )
                )
                if existing_quarantine is None:
                    session.add(
                        QuarantineRecord(
                            dataset_version_id=silver_version.id,
                            pipeline_run_id=run.id,
                            reason_code=row.reason_code,
                            source_key=row.source_key,
                            safe_payload=row.safe_payload,
                        )
                    )

            if not report.publishable:
                run.status = "failed"
                run.finished_at = now
                run.error_category = "quality_gate"
                return PipelineOutcome(
                    status="rejected",
                    run_id=str(run.id),
                    bronze_version_id=str(bronze_version_id),
                    silver_version_id=str(silver_version.id),
                    gold_version_id=None,
                    raw_observations=retrieved.row_count,
                    normalized_observations=len(batch.observations),
                    published_observations=0,
                    quarantined_observations=len(batch.quarantined),
                    checksum=batch.checksum,
                )

            gold_version = await self._get_or_create_version(
                session,
                dataset_id=datasets["gold"].id,
                source_identity=retrieved.source_identity,
                checksum=batch.checksum,
                retrieved_at=retrieved.retrieved_at,
                row_count=len(batch.observations),
                status="published",
                processed_at=now,
            )
            has_gold_rows = await session.scalar(
                select(GoldRegionalObservation.id)
                .where(GoldRegionalObservation.dataset_version_id == gold_version.id)
                .limit(1)
            )
            if has_gold_rows is None:
                session.add_all(
                    [
                        GoldRegionalObservation(
                            dataset_version_id=gold_version.id,
                            observation_key=row.observation_key,
                            region_code=row.region_code,
                            indicator_code=row.indicator_code,
                            period=row.period,
                            value=row.value,
                            value_status=row.value_status,
                            unit=row.unit,
                            is_national_aggregate=row.is_national_aggregate,
                        )
                        for row in batch.observations
                    ]
                )
                session.add_all(self._coverage_rows(gold_version.id, batch, contract))

            session.add_all(
                [
                    LineageEdge(
                        upstream_version_id=bronze_version_id,
                        downstream_version_id=silver_version.id,
                        transformation_version=TRANSFORMATION_VERSION,
                        run_id=run.id,
                    ),
                    LineageEdge(
                        upstream_version_id=silver_version.id,
                        downstream_version_id=gold_version.id,
                        transformation_version=TRANSFORMATION_VERSION,
                        run_id=run.id,
                    ),
                ]
            )
            run.dataset_version_id = gold_version.id
            run.status = "succeeded"
            run.finished_at = now

            return PipelineOutcome(
                status="published",
                run_id=str(run.id),
                bronze_version_id=str(bronze_version_id),
                silver_version_id=str(silver_version.id),
                gold_version_id=str(gold_version.id),
                raw_observations=retrieved.row_count,
                normalized_observations=len(batch.observations),
                published_observations=len(batch.observations),
                quarantined_observations=len(batch.quarantined),
                checksum=batch.checksum,
            )

    async def _persist_bronze(
        self,
        retrieved: RetrievedPayload,
        contract: IndicatorContract,
    ) -> uuid.UUID:
        async with self._session_factory() as session, session.begin():
            datasets = await self._ensure_catalog(session, contract)
            version = await self._get_or_create_version(
                session,
                dataset_id=datasets["bronze"].id,
                source_identity=retrieved.source_identity,
                checksum=retrieved.checksum,
                retrieved_at=retrieved.retrieved_at,
                row_count=retrieved.row_count,
                status="ingested",
            )
            existing_payload = await session.scalar(
                select(RawPayload.id).where(RawPayload.dataset_version_id == version.id)
            )
            if existing_payload is None:
                session.add(
                    RawPayload(
                        dataset_version_id=version.id,
                        endpoint=retrieved.endpoint,
                        safe_parameters=retrieved.safe_parameters,
                        response_headers=retrieved.response_headers,
                        http_status=retrieved.http_status,
                        body_text=retrieved.body_text,
                        payload=retrieved.payload,
                        content_sha256=retrieved.checksum,
                        byte_count=retrieved.byte_count,
                    )
                )
            return version.id

    async def _published_outcome(
        self,
        bronze_version_id: uuid.UUID,
        retrieved: RetrievedPayload,
        contract: IndicatorContract,
    ) -> PipelineOutcome | None:
        async with self._session_factory() as session:
            silver_edge = LineageEdge
            silver_version_id = await session.scalar(
                select(silver_edge.downstream_version_id).where(
                    silver_edge.upstream_version_id == bronze_version_id
                )
            )
            if silver_version_id is None:
                return None
            gold_version_id = await session.scalar(
                select(LineageEdge.downstream_version_id)
                .join(
                    DatasetVersion,
                    DatasetVersion.id == LineageEdge.downstream_version_id,
                )
                .join(Dataset, Dataset.id == DatasetVersion.dataset_id)
                .where(
                    LineageEdge.upstream_version_id == silver_version_id,
                    Dataset.layer == "gold",
                    DatasetVersion.status == "published",
                )
            )
            if gold_version_id is None:
                return None
            gold_version = await session.scalar(
                select(DatasetVersion).where(DatasetVersion.id == gold_version_id)
            )
            if gold_version is None:
                return None
            run_id = await session.scalar(
                select(PipelineRun.id)
                .where(PipelineRun.dataset_version_id == gold_version_id)
                .order_by(PipelineRun.finished_at.desc())
                .limit(1)
            )
            return PipelineOutcome(
                status="unchanged",
                run_id=str(run_id or ""),
                bronze_version_id=str(bronze_version_id),
                silver_version_id=str(silver_version_id),
                gold_version_id=str(gold_version_id),
                raw_observations=retrieved.row_count,
                normalized_observations=gold_version.row_count,
                published_observations=gold_version.row_count,
                quarantined_observations=0,
                checksum=gold_version.checksum,
            )

    async def _ensure_catalog(
        self,
        session: AsyncSession,
        contract: IndicatorContract,
    ) -> dict[str, Dataset]:
        source = await session.scalar(select(Source).where(Source.code == "bps"))
        if source is None:
            source = Source(
                code="bps",
                name="Badan Pusat Statistik",
                base_url="https://webapi.bps.go.id/v1/api",
                owner="Data Engineering",
                attribution="Badan Pusat Statistik (BPS)",
            )
            session.add(source)
            await session.flush()

        definitions = {
            "bronze": (f"bps_{contract.code}_raw", f"BPS {contract.name} raw"),
            "silver": (f"{contract.code}_silver", f"{contract.name} normalized"),
            "gold": (f"{contract.code}_gold", f"{contract.name} curated"),
        }
        datasets: dict[str, Dataset] = {}
        for layer, (code, name) in definitions.items():
            dataset = await session.scalar(
                select(Dataset).where(Dataset.source_id == source.id, Dataset.code == code)
            )
            if dataset is None:
                dataset = Dataset(
                    source_id=source.id,
                    code=code,
                    name=name,
                    layer=layer,
                    owner="Data Engineering",
                    freshness_sla_seconds=32 * 24 * 60 * 60,
                    active=True,
                )
                session.add(dataset)
                await session.flush()
            datasets[layer] = dataset

        specification = _contract_specification(contract)
        contract_row = await session.scalar(
            select(DataContract).where(
                DataContract.dataset_id == datasets["silver"].id,
                DataContract.version == 1,
            )
        )
        if contract_row is None:
            session.add(
                DataContract(
                    dataset_id=datasets["silver"].id,
                    version=1,
                    specification=specification,
                    checksum=_json_checksum(specification),
                    effective_at=datetime.now(UTC),
                )
            )
        return datasets

    async def _ensure_dimensions(
        self,
        session: AsyncSession,
        contract: IndicatorContract,
    ) -> None:
        region_definitions = [*contract.regions]
        for region in region_definitions:
            existing = await session.get(Region, region.code)
            if existing is None:
                session.add(
                    Region(
                        code=region.code,
                        name=region.name,
                        level="province",
                        parent_code=None,
                        valid_from=datetime(2022, 1, 1, tzinfo=UTC).date(),
                        valid_to=None,
                    )
                )
        if await session.get(Region, contract.national_code) is None:
            session.add(
                Region(
                    code=contract.national_code,
                    name="INDONESIA",
                    level="national",
                    parent_code=None,
                    valid_from=datetime(1945, 8, 17, tzinfo=UTC).date(),
                    valid_to=None,
                )
            )
        if await session.get(Indicator, contract.code) is None:
            session.add(
                Indicator(
                    code=contract.code,
                    name=contract.name,
                    unit=contract.unit,
                    favorable_direction=contract.favorable_direction,
                    definition=contract.definition,
                    source_url=contract.source_url,
                    reference_period_rule=contract.reference_period_rule,
                )
            )
        await session.flush()

    async def _get_or_create_version(
        self,
        session: AsyncSession,
        *,
        dataset_id: uuid.UUID,
        source_identity: str,
        checksum: str,
        retrieved_at: datetime,
        row_count: int,
        status: str,
        processed_at: datetime | None = None,
    ) -> DatasetVersion:
        version = await session.scalar(
            select(DatasetVersion).where(
                DatasetVersion.dataset_id == dataset_id,
                DatasetVersion.source_identity == source_identity,
                DatasetVersion.checksum == checksum,
            )
        )
        if version is None:
            version = DatasetVersion(
                dataset_id=dataset_id,
                source_identity=source_identity,
                checksum=checksum,
                code_commit=None,
                source_reference_at=None,
                retrieved_at=retrieved_at,
                processed_at=processed_at,
                row_count=row_count,
                status=status,
            )
            session.add(version)
            await session.flush()
        return version

    def _coverage_rows(
        self,
        dataset_version_id: uuid.UUID,
        batch: Any,
        contract: IndicatorContract,
    ) -> list[CoverageSummary]:
        result: list[CoverageSummary] = []
        expected = len(contract.regions)
        for period in contract.periods:
            rows = [
                row
                for row in batch.observations
                if not row.is_national_aggregate and row.period.year == period.year
            ]
            observed = sum(row.value_status == "observed" for row in rows)
            result.append(
                CoverageSummary(
                    dataset_version_id=dataset_version_id,
                    indicator_code=contract.code,
                    period=datetime(period.year, period.month, 1, tzinfo=UTC).date(),
                    expected_regions=expected,
                    observed_regions=observed,
                    missing_regions=expected - observed,
                    coverage_percent=(Decimal(observed) * Decimal(100) / Decimal(expected)),
                )
            )
        return result
