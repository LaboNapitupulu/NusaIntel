from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db.models import GoldRegionalObservation, Incident, QualityCheckResult
from app.db.session import create_database_engine, create_session_factory
from app.pipeline.contracts import TPT_CONTRACT
from app.pipeline.service import PipelineService
from app.pipeline.types import RetrievedPayload


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the isolated quality-incident case study.")
    parser.add_argument("--database", required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    return parser.parse_args()


def retrieved(endpoint: str, payload: dict[str, object]) -> RetrievedPayload:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    data_content = payload["datacontent"]
    if not isinstance(data_content, dict):
        raise ValueError("Fixture datacontent must be an object.")
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
        row_count=len(data_content),
    )


async def run_case(database_url: str, valid_payload: dict[str, object]) -> dict[str, object]:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    service = PipelineService(session_factory)
    identity = uuid.uuid4().hex
    first = await service.run(
        retrieved(f"fixture://quality-case/{identity}/valid", valid_payload),
        TPT_CONTRACT,
    )
    repeated = await service.run(
        retrieved(f"fixture://quality-case/{identity}/valid", valid_payload),
        TPT_CONTRACT,
    )
    invalid_payload = copy.deepcopy(valid_payload)
    invalid_payload["datacontent"]["11005430123190"] = "invalid"
    rejected = await service.run(
        retrieved(f"fixture://quality-case/{identity}/invalid", invalid_payload),
        TPT_CONTRACT,
    )

    async with session_factory() as session:
        gold_rows = await session.scalar(
            select(func.count())
            .select_from(GoldRegionalObservation)
            .where(
                GoldRegionalObservation.dataset_version_id == uuid.UUID(first.gold_version_id or "")
            )
        )
        incident_rows = list(
            (
                await session.execute(
                    select(Incident.check_code, Incident.severity)
                    .where(Incident.pipeline_run_id == uuid.UUID(rejected.run_id))
                    .order_by(Incident.check_code)
                )
            ).all()
        )
        failed_checks = await session.scalar(
            select(func.count())
            .select_from(QualityCheckResult)
            .where(
                QualityCheckResult.pipeline_run_id == uuid.UUID(rejected.run_id),
                QualityCheckResult.status == "failed",
            )
        )
    await engine.dispose()

    if first.status != "published" or repeated.status != "unchanged":
        raise RuntimeError("Valid fixture did not preserve idempotent publication.")
    if rejected.status != "rejected" or rejected.gold_version_id is not None:
        raise RuntimeError("Invalid fixture was not rejected before Gold publication.")
    if gold_rows != 117 or not incident_rows or failed_checks != len(incident_rows):
        raise RuntimeError("Incident or last-known-good evidence did not match expectations.")

    return {
        "valid_status": first.status,
        "repeated_status": repeated.status,
        "invalid_status": rejected.status,
        "failed_checks": failed_checks,
        "incidents": [
            {"check_code": check_code, "severity": severity}
            for check_code, severity in incident_rows
        ],
        "last_known_good_rows": gold_rows,
        "invalid_gold_version": rejected.gold_version_id,
    }


def main() -> None:
    options = arguments()
    base_url = make_url(get_settings().resolved_database_url)
    scratch_url = base_url.set(database=options.database).render_as_string(hide_password=False)
    os.environ["DATABASE_URL"] = scratch_url
    get_settings.cache_clear()

    alembic_config = Config("/app/alembic.ini")
    command.upgrade(alembic_config, "head")
    payload = json.loads(options.fixture.read_bytes())
    evidence = asyncio.run(run_case(scratch_url, payload))
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
