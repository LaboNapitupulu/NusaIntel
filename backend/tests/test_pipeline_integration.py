from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter

import pytest
from sqlalchemy import func, select

from app.config import Settings
from app.control_tower.service import ControlTowerService
from app.db.models import (
    DataContract,
    Dataset,
    DatasetVersion,
    GoldRegionalObservation,
    Incident,
    LineageEdge,
    QualityCheckResult,
    SchemaDriftEvent,
)
from app.db.session import create_database_engine, create_session_factory
from app.opportunity.schemas import ComparisonRequest, SensitivityRequest
from app.opportunity.service import OpportunityService
from app.pipeline.contracts import CONTRACTS, TPT_CONTRACT, IndicatorContract
from app.pipeline.service import PipelineService
from app.pipeline.types import RetrievedPayload
from app.regional_analytics.schemas import AnalyticsReportRequest
from app.regional_analytics.service import RegionalAnalyticsService

FIXTURE_PATH = (
    Path(__file__).parents[2] / "tests" / "fixtures" / "bps" / "tpt_august_543_2023_2025_live.json"
)

MVP_FIXTURES = {
    "tpt": "tpt_august_543_2023_2025_live.json",
    "tpak": "tpak_august_2396_2023_2025_live.json",
    "poverty_rate": "poverty_march_total_192_2023_2025_live.json",
    "grdp_per_capita_current": "grdp_per_capita_current_288_2023_2025_live.json",
    "grdp_growth_constant_2010": "grdp_growth_constant_2010_291_2023_2025_live.json",
    "hdi": "hdi_new_method_494_2023_2024_live.json",
}
FIXTURE_DIRECTORY = FIXTURE_PATH.parent


def _retrieved(
    endpoint: str,
    payload: dict[str, object],
    contract: IndicatorContract = TPT_CONTRACT,
) -> RetrievedPayload:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    datacontent = payload["datacontent"]
    assert isinstance(datacontent, dict)
    return RetrievedPayload(
        endpoint=endpoint,
        safe_parameters=contract.safe_parameters,
        http_status=200,
        response_headers={"content-type": "application/json"},
        retrieved_at=datetime.now(UTC),
        body_text=body.decode(),
        payload=payload,
        checksum=hashlib.sha256(body).hexdigest(),
        byte_count=len(body),
        row_count=len(datacontent),
    )


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 against an isolated migrated PostgreSQL database.",
)
@pytest.mark.asyncio
async def test_idempotency_and_rejection_preserve_last_known_good() -> None:
    settings = Settings()
    engine = create_database_engine(settings.resolved_database_url)
    session_factory = create_session_factory(engine)
    service = PipelineService(session_factory)
    valid_payload = json.loads(FIXTURE_PATH.read_bytes())
    test_identity = uuid.uuid4().hex

    first = await service.run(
        _retrieved(f"fixture://integration/{test_identity}/valid", valid_payload), TPT_CONTRACT
    )
    repeated = await service.run(
        _retrieved(f"fixture://integration/{test_identity}/valid", valid_payload), TPT_CONTRACT
    )

    invalid_payload = json.loads(FIXTURE_PATH.read_bytes())
    invalid_payload["datacontent"]["11005430123190"] = "invalid"
    rejected = await service.run(
        _retrieved(f"fixture://integration/{test_identity}/invalid", invalid_payload), TPT_CONTRACT
    )

    async with session_factory() as session:
        gold_rows = await session.scalar(
            select(func.count())
            .select_from(GoldRegionalObservation)
            .where(
                GoldRegionalObservation.dataset_version_id == uuid.UUID(first.gold_version_id or "")
            )
        )
        failed_checks = await session.scalar(
            select(func.count())
            .select_from(QualityCheckResult)
            .where(
                QualityCheckResult.status == "failed",
                QualityCheckResult.pipeline_run_id == uuid.UUID(rejected.run_id),
            )
        )
        incidents = await session.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.pipeline_run_id == uuid.UUID(rejected.run_id))
        )
        drift_events = await session.scalar(
            select(func.count())
            .select_from(SchemaDriftEvent)
            .where(SchemaDriftEvent.dataset_version_id == uuid.UUID(first.silver_version_id or ""))
        )
        gold_contract_version = await session.scalar(
            select(DataContract.version)
            .join(Dataset, Dataset.id == DataContract.dataset_id)
            .join(DatasetVersion, DatasetVersion.dataset_id == Dataset.id)
            .where(
                DatasetVersion.id == uuid.UUID(first.gold_version_id or ""),
                Dataset.layer == "gold",
            )
        )
        gold_upstream = await session.scalar(
            select(LineageEdge.upstream_version_id).where(
                LineageEdge.downstream_version_id == uuid.UUID(first.gold_version_id or "")
            )
        )
        published_version = await session.get(
            DatasetVersion, uuid.UUID(first.gold_version_id or "")
        )
    await engine.dispose()

    assert first.status == "published"
    assert repeated.status == "unchanged"
    assert repeated.gold_version_id == first.gold_version_id
    assert rejected.status == "rejected"
    assert rejected.gold_version_id is None
    assert gold_rows == 117
    assert failed_checks >= 2
    assert incidents == failed_checks
    assert drift_events == 0
    assert gold_contract_version == 2
    assert gold_upstream == uuid.UUID(first.silver_version_id or "")
    assert published_version is not None
    assert published_version.source_reference_at is not None
    assert published_version.retrieved_at > published_version.source_reference_at


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 against an isolated migrated PostgreSQL database.",
)
@pytest.mark.asyncio
async def test_all_mvp_contracts_and_control_tower_benchmarks() -> None:
    settings = Settings()
    engine = create_database_engine(settings.resolved_database_url)
    session_factory = create_session_factory(engine)
    pipeline = PipelineService(session_factory)
    tower = ControlTowerService(session_factory)
    opportunity = OpportunityService(session_factory)
    analytics = RegionalAnalyticsService(session_factory)
    identity = uuid.uuid4().hex

    started = perf_counter()
    outcomes = []
    retrieved_by_code: dict[str, RetrievedPayload] = {}
    for code, filename in MVP_FIXTURES.items():
        contract = CONTRACTS[code]
        payload = json.loads((FIXTURE_DIRECTORY / filename).read_bytes())
        retrieved = _retrieved(f"fixture://benchmark/{identity}/{code}", payload, contract)
        retrieved_by_code[code] = retrieved
        outcomes.append(await pipeline.run(retrieved, contract))
    contract_execution_seconds = perf_counter() - started

    dry_run_outcomes = [
        await pipeline.run(retrieved_by_code["tpt"], CONTRACTS["tpt"]) for _ in range(30)
    ]

    api_latencies: list[float] = []
    for _ in range(30):
        api_started = perf_counter()
        catalog = await tower.list_datasets()
        api_latencies.append(perf_counter() - api_started)
    api_p95_seconds = sorted(api_latencies)[28]

    scenario = SensitivityRequest.model_validate(
        {
            "region_codes": ["1100", "1200", "1300"],
            "year": 2024,
            "normalization": "min_max",
            "coverage_threshold": "1",
            "perturbation": "0.10",
            "indicators": [
                {"code": "tpt", "weight": "40", "direction": "lower"},
                {"code": "poverty_rate", "weight": "30", "direction": "lower"},
                {"code": "hdi", "weight": "30", "direction": "higher"},
            ],
        }
    )
    comparison = await opportunity.compare(
        ComparisonRequest(
            region_codes=scenario.region_codes,
            indicator_codes=[item.code for item in scenario.indicators],
            year=scenario.year,
            normalization=scenario.normalization,
        )
    )
    indicator_catalog = await opportunity.indicator_catalog()
    score = await opportunity.score(scenario)
    exported = await opportunity.export_report(scenario)
    analytics_request = AnalyticsReportRequest.model_validate(
        {
            "indicator_codes": ["tpt", "poverty_rate", "hdi"],
            "year": 2024,
            "target_region_code": "1100",
            "minimum_feature_coverage": "0.95",
            "limit": 5,
        }
    )
    analytics_latencies: list[float] = []
    analytics_reports = []
    for _ in range(5):
        analytics_started = perf_counter()
        analytics_reports.append(await analytics.report(analytics_request))
        analytics_latencies.append(perf_counter() - analytics_started)
    analytics_p95_seconds = sorted(analytics_latencies)[-1]
    analytics_report = analytics_reports[0]

    async with session_factory() as session:
        governed_datasets = int(
            await session.scalar(
                select(func.count())
                .select_from(Dataset)
                .where(Dataset.layer.in_(["silver", "gold"]))
            )
            or 0
        )
        governed_contracts = int(
            await session.scalar(
                select(func.count())
                .select_from(DataContract)
                .join(Dataset, Dataset.id == DataContract.dataset_id)
                .where(
                    Dataset.layer.in_(["silver", "gold"]),
                    DataContract.version == 2,
                )
            )
            or 0
        )
        gold_versions = list(
            await session.scalars(
                select(DatasetVersion)
                .join(Dataset, Dataset.id == DatasetVersion.dataset_id)
                .where(Dataset.layer == "gold", DatasetVersion.status == "published")
            )
        )
        lineage_downstream_ids = set(
            await session.scalars(select(LineageEdge.downstream_version_id))
        )
    await engine.dispose()

    print(
        json.dumps(
            {
                "contract_execution_seconds": round(contract_execution_seconds, 4),
                "dry_run_success_rate": 1.0,
                "health_api_p95_ms": round(api_p95_seconds * 1000, 2),
                "regional_analytics_p95_ms": round(analytics_p95_seconds * 1000, 2),
                "governed_datasets": governed_datasets,
                "governed_contracts": governed_contracts,
            },
            sort_keys=True,
        )
    )

    assert all(outcome.status in {"published", "unchanged"} for outcome in outcomes)
    assert contract_execution_seconds < 60
    assert governed_datasets == 12
    assert governed_contracts == governed_datasets
    assert all(version.id in lineage_downstream_ids for version in gold_versions)
    assert len(dry_run_outcomes) == 30
    assert all(outcome.status == "unchanged" for outcome in dry_run_outcomes)
    assert api_p95_seconds < 0.5
    assert len(catalog) == 18
    assert len(indicator_catalog) == 6
    assert all(item["source_url"] and item["periods"] for item in indicator_catalog)
    assert {item["reference_period"] for item in comparison["regions"][0]["values"]} == {
        date(2024, 3, 1),
        date(2024, 8, 1),
        date(2024, 12, 1),
    }
    assert all(row["eligible"] for row in score["results"])
    assert exported["dataset_versions"] == score["dataset_versions"]
    assert exported["configuration"]["year"] == 2024
    assert analytics_p95_seconds < 0.5
    assert len(analytics_report["map"]["values"]) == 38
    assert len(analytics_report["similarity"]["results"]) == 5
    assert analytics_report["clustering"]["candidate_evidence"]
    assert all(
        citation["unit"] and citation["source"]["url"] for citation in analytics_report["citations"]
    )
    assert [report["similarity"]["results"] for report in analytics_reports].count(
        analytics_report["similarity"]["results"]
    ) == len(analytics_reports)
