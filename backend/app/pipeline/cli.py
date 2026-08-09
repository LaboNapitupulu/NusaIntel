from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.bps.client import BPSClient
from app.bps.errors import BPSError
from app.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.pipeline.contracts import CONTRACTS, IndicatorContract
from app.pipeline.service import PipelineService
from app.pipeline.types import RetrievedPayload


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a NusaIntel BPS ingestion pipeline.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--indicator", choices=sorted(CONTRACTS))
    target.add_argument("--all", action="store_true", help="Run every contracted indicator.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true", help="Retrieve data from BPS WebAPI.")
    source.add_argument("--fixture", type=Path, help="Read a captured BPS JSON response.")
    return parser.parse_args()


def _fixture_payload(path: Path, contract: IndicatorContract) -> RetrievedPayload:
    body = path.read_bytes()
    try:
        payload: Any = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Fixture must contain valid UTF-8 JSON.") from error
    if not isinstance(payload, dict):
        raise ValueError("Fixture root must be a JSON object.")
    datacontent = payload.get("datacontent")
    if not isinstance(datacontent, dict):
        raise ValueError("Fixture datacontent must be a JSON object.")
    return RetrievedPayload(
        endpoint="fixture://bps/list",
        safe_parameters=contract.safe_parameters,
        http_status=200,
        response_headers={"content-type": "application/json"},
        retrieved_at=datetime.now(UTC),
        body_text=body.decode("utf-8"),
        payload=payload,
        checksum=hashlib.sha256(body).hexdigest(),
        byte_count=len(body),
        row_count=len(datacontent),
    )


async def _run(arguments: argparse.Namespace) -> int:
    settings = get_settings()
    contracts = list(CONTRACTS.values()) if arguments.all else [CONTRACTS[arguments.indicator]]
    outcomes = []
    try:
        engine = create_database_engine(settings.resolved_database_url)
        try:
            service = PipelineService(create_session_factory(engine))
            if arguments.live:
                async with BPSClient(settings) as client:
                    for contract in contracts:
                        retrieved = await client.fetch(contract)
                        outcomes.append(await service.run(retrieved, contract))
            else:
                if len(contracts) != 1:
                    raise ValueError("--fixture requires one --indicator.")
                retrieved = _fixture_payload(arguments.fixture, contracts[0])
                outcomes.append(await service.run(retrieved, contracts[0]))
        finally:
            await engine.dispose()
    except (BPSError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    except SQLAlchemyError:
        print(json.dumps({"status": "failed", "error": "Database operation failed."}))
        return 1

    serialized = [asdict(outcome) for outcome in outcomes]
    output: object = serialized[0] if len(serialized) == 1 else serialized
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0 if all(outcome.status in {"published", "unchanged"} for outcome in outcomes) else 2


def main() -> None:
    raise SystemExit(asyncio.run(_run(_arguments())))


if __name__ == "__main__":
    main()
