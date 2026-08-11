from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    DataContract,
    Dataset,
    DatasetVersion,
    Incident,
    LineageEdge,
    PipelineRun,
    QualityCheckResult,
    QualityException,
    SchemaDriftEvent,
    Source,
)


class ControlTowerService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_datasets(self, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            rows = await session.execute(
                select(Dataset, Source)
                .join(Source, Source.id == Dataset.source_id)
                .where(Dataset.active.is_(True))
                .order_by(Dataset.layer, Dataset.code)
                .limit(limit)
                .offset(offset)
            )
            return [
                await self._dataset_summary(session, dataset, source) for dataset, source in rows
            ]

    async def get_dataset(self, dataset_id: uuid.UUID) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    select(Dataset, Source)
                    .join(Source, Source.id == Dataset.source_id)
                    .where(Dataset.id == dataset_id)
                )
            ).one_or_none()
            if row is None:
                return None
            dataset, source = row
            summary = await self._dataset_summary(session, dataset, source)
            contract = await session.scalar(
                select(DataContract)
                .where(DataContract.dataset_id == dataset.id)
                .order_by(DataContract.version.desc())
                .limit(1)
            )
            drifts = await session.scalars(
                select(SchemaDriftEvent)
                .join(DatasetVersion, DatasetVersion.id == SchemaDriftEvent.dataset_version_id)
                .where(DatasetVersion.dataset_id == dataset.id)
                .order_by(SchemaDriftEvent.created_at.desc())
                .limit(20)
            )
            summary["contract"] = (
                {
                    "id": str(contract.id),
                    "version": contract.version,
                    "checksum": contract.checksum,
                    "effective_at": contract.effective_at,
                    "specification": contract.specification,
                }
                if contract is not None
                else None
            )
            summary["schema_drift"] = [
                {
                    "id": str(drift.id),
                    "change_type": drift.change_type,
                    "column_name": drift.column_name,
                    "expected": drift.expected,
                    "observed": drift.observed,
                    "created_at": drift.created_at,
                }
                for drift in drifts
            ]
            return summary

    async def quality_history(
        self,
        dataset_id: uuid.UUID,
        *,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            query = (
                select(QualityCheckResult, DataContract.version)
                .join(DatasetVersion, DatasetVersion.id == QualityCheckResult.dataset_version_id)
                .outerjoin(DataContract, DataContract.id == QualityCheckResult.data_contract_id)
                .where(DatasetVersion.dataset_id == dataset_id)
                .order_by(QualityCheckResult.created_at.desc())
                .limit(limit)
            )
            if severity is not None:
                query = query.where(QualityCheckResult.severity == severity)
            if status is not None:
                query = query.where(QualityCheckResult.status == status)
            rows = await session.execute(query)
            return [
                {
                    "id": str(check.id),
                    "dataset_version_id": str(check.dataset_version_id),
                    "pipeline_run_id": str(check.pipeline_run_id),
                    "contract_version": contract_version,
                    "check_code": check.check_code,
                    "severity": check.severity,
                    "status": check.status,
                    "expected": check.expected,
                    "observed": check.observed,
                    "safe_sample": check.safe_sample or [],
                    "created_at": check.created_at,
                }
                for check, contract_version in rows
            ]

    async def pipeline_runs(
        self, *, dataset_id: uuid.UUID | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            query = (
                select(PipelineRun, DatasetVersion, Dataset)
                .outerjoin(DatasetVersion, DatasetVersion.id == PipelineRun.dataset_version_id)
                .outerjoin(Dataset, Dataset.id == DatasetVersion.dataset_id)
                .order_by(PipelineRun.started_at.desc())
                .limit(limit)
            )
            if dataset_id is not None:
                query = query.where(Dataset.id == dataset_id)
            rows = await session.execute(query)
            return [
                {
                    "id": str(run.id),
                    "dataset_id": str(dataset.id) if dataset is not None else None,
                    "dataset_code": dataset.code if dataset is not None else None,
                    "dataset_version_id": (str(version.id) if version is not None else None),
                    "run_type": run.run_type,
                    "status": run.status,
                    "started_at": run.started_at,
                    "finished_at": run.finished_at,
                    "correlation_id": run.correlation_id,
                    "error_category": run.error_category,
                }
                for run, version, dataset in rows
            ]

    async def lineage(self, dataset_id: uuid.UUID) -> dict[str, list[dict[str, Any]]]:
        async with self._session_factory() as session:
            version_ids = select(DatasetVersion.id).where(DatasetVersion.dataset_id == dataset_id)
            edges = list(
                await session.scalars(
                    select(LineageEdge)
                    .where(
                        or_(
                            LineageEdge.upstream_version_id.in_(version_ids),
                            LineageEdge.downstream_version_id.in_(version_ids),
                        )
                    )
                    .order_by(LineageEdge.created_at.desc())
                    .limit(100)
                )
            )
            connected_ids = {
                version_id
                for edge in edges
                for version_id in (edge.upstream_version_id, edge.downstream_version_id)
            }
            nodes: list[dict[str, Any]] = []
            if connected_ids:
                node_rows = await session.execute(
                    select(DatasetVersion, Dataset)
                    .join(Dataset, Dataset.id == DatasetVersion.dataset_id)
                    .where(DatasetVersion.id.in_(connected_ids))
                )
                nodes = [
                    {
                        "version_id": str(version.id),
                        "dataset_id": str(dataset.id),
                        "dataset_code": dataset.code,
                        "layer": dataset.layer,
                        "status": version.status,
                    }
                    for version, dataset in node_rows
                ]
            return {
                "nodes": nodes,
                "edges": [
                    {
                        "id": str(edge.id),
                        "upstream_version_id": str(edge.upstream_version_id),
                        "downstream_version_id": str(edge.downstream_version_id),
                        "transformation_version": edge.transformation_version,
                        "run_id": str(edge.run_id),
                    }
                    for edge in edges
                ],
            }

    async def incidents(
        self, *, status: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            query = (
                select(Incident, Dataset)
                .join(Dataset, Dataset.id == Incident.dataset_id)
                .order_by(Incident.created_at.desc())
                .limit(limit)
            )
            if status is not None:
                query = query.where(Incident.status == status)
            rows = await session.execute(query)
            return [
                {
                    "id": str(incident.id),
                    "dataset_id": str(dataset.id),
                    "dataset_code": dataset.code,
                    "pipeline_run_id": str(incident.pipeline_run_id),
                    "check_code": incident.check_code,
                    "severity": incident.severity,
                    "status": incident.status,
                    "title": incident.title,
                    "resolution_note": incident.resolution_note,
                    "created_at": incident.created_at,
                    "resolved_at": incident.resolved_at,
                }
                for incident, dataset in rows
            ]

    async def resolve_incident(
        self, incident_id: uuid.UUID, *, status: str, resolution_note: str
    ) -> dict[str, Any] | None:
        async with self._session_factory() as session, session.begin():
            incident = await session.get(Incident, incident_id)
            if incident is None:
                return None
            incident.status = status
            incident.resolution_note = resolution_note
            incident.resolved_at = (
                datetime.now(UTC) if status in {"resolved", "ignored-with-reason"} else None
            )
            await session.flush()
            return {
                "id": str(incident.id),
                "status": incident.status,
                "resolution_note": incident.resolution_note,
                "resolved_at": incident.resolved_at,
            }

    async def create_exception(
        self,
        dataset_id: uuid.UUID,
        *,
        check_code: str,
        reason: str,
        owner: str,
        expires_at: datetime,
    ) -> dict[str, Any] | None:
        async with self._session_factory() as session, session.begin():
            if await session.get(Dataset, dataset_id) is None:
                return None
            exception = QualityException(
                dataset_id=dataset_id,
                check_code=check_code,
                reason=reason,
                owner=owner,
                expires_at=expires_at,
                active=True,
            )
            session.add(exception)
            await session.flush()
            return {
                "id": str(exception.id),
                "dataset_id": str(exception.dataset_id),
                "check_code": exception.check_code,
                "reason": exception.reason,
                "owner": exception.owner,
                "expires_at": exception.expires_at,
                "active": exception.active,
            }

    async def _dataset_summary(
        self, session: AsyncSession, dataset: Dataset, source: Source
    ) -> dict[str, Any]:
        latest = await session.scalar(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset.id)
            .order_by(DatasetVersion.retrieved_at.desc(), DatasetVersion.created_at.desc())
            .limit(1)
        )
        last_good = await session.scalar(
            select(DatasetVersion)
            .where(
                DatasetVersion.dataset_id == dataset.id,
                DatasetVersion.status.in_(["ingested", "validated", "published"]),
            )
            .order_by(DatasetVersion.processed_at.desc(), DatasetVersion.retrieved_at.desc())
            .limit(1)
        )
        last_run = await session.scalar(
            select(PipelineRun)
            .join(DatasetVersion, DatasetVersion.id == PipelineRun.dataset_version_id)
            .where(DatasetVersion.dataset_id == dataset.id)
            .order_by(PipelineRun.started_at.desc())
            .limit(1)
        )
        last_successful_run = await session.scalar(
            select(PipelineRun)
            .join(DatasetVersion, DatasetVersion.id == PipelineRun.dataset_version_id)
            .where(
                DatasetVersion.dataset_id == dataset.id,
                PipelineRun.status == "succeeded",
            )
            .order_by(PipelineRun.finished_at.desc())
            .limit(1)
        )
        open_incidents = int(
            await session.scalar(
                select(func.count())
                .select_from(Incident)
                .where(
                    Incident.dataset_id == dataset.id,
                    Incident.status.in_(["open", "acknowledged"]),
                )
            )
            or 0
        )
        failed_checks = 0
        if latest is not None:
            failed_checks = int(
                await session.scalar(
                    select(func.count())
                    .select_from(QualityCheckResult)
                    .where(
                        QualityCheckResult.dataset_version_id == latest.id,
                        QualityCheckResult.status == "failed",
                    )
                )
                or 0
            )
        now = datetime.now(UTC)
        freshness_status = "unknown"
        if latest is not None:
            freshness_status = (
                "fresh"
                if (now - latest.retrieved_at).total_seconds() <= dataset.freshness_sla_seconds
                else "stale"
            )
        if open_incidents:
            health = "critical"
        elif (
            freshness_status == "stale"
            or failed_checks
            or (last_run and last_run.status == "failed")
        ):
            health = "warning"
        elif latest is None:
            health = "unknown"
        else:
            health = "healthy"
        return {
            "id": str(dataset.id),
            "code": dataset.code,
            "name": dataset.name,
            "layer": dataset.layer,
            "owner": dataset.owner,
            "source": {"code": source.code, "name": source.name},
            "freshness_sla_seconds": dataset.freshness_sla_seconds,
            "health": health,
            "freshness": {
                "status": freshness_status,
                "source_reference_at": latest.source_reference_at if latest else None,
                "retrieved_at": latest.retrieved_at if latest else None,
                "processed_at": latest.processed_at if latest else None,
            },
            "latest_version_id": str(latest.id) if latest else None,
            "latest_version_status": latest.status if latest else None,
            "last_known_good_version_id": str(last_good.id) if last_good else None,
            "last_run_status": last_run.status if last_run else None,
            "last_successful_run_at": (
                last_successful_run.finished_at if last_successful_run is not None else None
            ),
            "open_incident_count": open_incidents,
            "failed_check_count": failed_checks,
        }
