from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.config import Settings
from app.db.models import GoldRegionalObservation, QualityCheckResult
from app.db.session import create_database_engine, create_session_factory
from app.pipeline.contracts import TPT_CONTRACT
from app.pipeline.service import PipelineService
from app.pipeline.types import RetrievedPayload

FIXTURE_PATH = (
    Path(__file__).parents[2] / "tests" / "fixtures" / "bps" / "tpt_august_543_2023_2025_live.json"
)


def _retrieved(endpoint: str, payload: dict[str, object]) -> RetrievedPayload:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    datacontent = payload["datacontent"]
    assert isinstance(datacontent, dict)
    return RetrievedPayload(
        endpoint=endpoint,
        safe_parameters=TPT_CONTRACT.safe_parameters,
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

    first = await service.run(
        _retrieved("fixture://integration/valid", valid_payload), TPT_CONTRACT
    )
    repeated = await service.run(
        _retrieved("fixture://integration/valid", valid_payload), TPT_CONTRACT
    )

    invalid_payload = json.loads(FIXTURE_PATH.read_bytes())
    invalid_payload["datacontent"]["11005430123190"] = "invalid"
    rejected = await service.run(
        _retrieved("fixture://integration/invalid", invalid_payload), TPT_CONTRACT
    )

    async with session_factory() as session:
        gold_rows = await session.scalar(select(func.count()).select_from(GoldRegionalObservation))
        failed_checks = await session.scalar(
            select(func.count())
            .select_from(QualityCheckResult)
            .where(QualityCheckResult.status == "failed")
        )
    await engine.dispose()

    assert first.status == "published"
    assert repeated.status == "unchanged"
    assert repeated.gold_version_id == first.gold_version_id
    assert rejected.status == "rejected"
    assert rejected.gold_version_id is None
    assert gold_rows == 117
    assert failed_checks == 2
