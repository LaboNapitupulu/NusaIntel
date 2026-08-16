from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from app.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.regulasilens.ingestion import FetchOutcome, fetch_regulation
from app.regulasilens.manifest import RegulationSource, load_manifest
from app.regulasilens.service import CorpusService


async def run(manifest_path: Path) -> int:
    manifest = load_manifest(manifest_path)
    settings = get_settings()
    engine = create_database_engine(settings.resolved_database_url)
    service = CorpusService(create_session_factory(engine))
    timeout = httpx.Timeout(30.0, connect=10.0)
    headers = {"User-Agent": "NusaIntel/0.5 governed-corpus-ingestion"}
    try:
        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        ) as client:

            async def fetch(
                document: RegulationSource, known_checksum: str | None
            ) -> FetchOutcome:
                return await fetch_regulation(
                    document,
                    client=client,
                    known_checksum=known_checksum,
                )

            outcome = await service.run_manifest(manifest, fetch)
        print(
            json.dumps(
                {
                    "corpus_id": outcome.corpus_id,
                    "corpus_version": outcome.corpus_version,
                    "successful": outcome.successful,
                    "documents": [
                        {
                            "document_id": item.document_id,
                            "status": item.status,
                            "dataset_version_id": item.dataset_version_id,
                            "run_id": item.run_id,
                            "checksum": item.checksum,
                            "section_count": item.section_count,
                            "reason": item.reason,
                        }
                        for item in outcome.documents
                    ],
                },
                sort_keys=True,
            )
        )
        return 0 if outcome.successful else 2
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the governed RegulasiLens corpus pipeline"
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=REPOSITORY_ROOT
        / "regulations"
        / "manifests"
        / "personal-data-protection.v1.json",
    )
    arguments = parser.parse_args()
    return asyncio.run(run(arguments.manifest))


if __name__ == "__main__":
    raise SystemExit(main())
