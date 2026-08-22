from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.config import Settings
from app.control_tower.service import ControlTowerService
from app.db.models import (
    DatasetVersion,
    Incident,
    QuarantineRecord,
    RawRegulationDocument,
    RegulationDocument,
    RegulationDocumentVersion,
    RegulationRelation,
    RegulationSection,
)
from app.db.session import create_database_engine, create_session_factory
from app.regulasilens.ingestion import FetchOutcome
from app.regulasilens.manifest import RegulationSource, load_manifest
from app.regulasilens.parser import PageText, parse_regulation_pages
from app.regulasilens.service import CorpusService

MANIFEST_PATH = (
    Path(__file__).parents[2] / "regulations" / "manifests" / "personal-data-protection.v1.json"
)


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 against an isolated migrated PostgreSQL database.",
)
@pytest.mark.asyncio
async def test_corpus_publish_idempotency_and_rejection_preserve_last_good(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = load_manifest(MANIFEST_PATH)
    pp = next(item for item in manifest.documents if item.document_id == "pp-71-2019")
    pp = pp.model_copy(update={"document_id": f"pp-71-2019-test-{uuid.uuid4().hex}"})
    manifest = manifest.model_copy(update={"documents": (pp,)})
    body = b"%PDF-1.7\nfixture"
    parsed = parse_regulation_pages(
        pp.document_id,
        (
            PageText(
                page_number=1,
                text="BAB I\nKETENTUAN UMUM\nPasal 1\nSistem Elektronik adalah sistem elektronik.",
            ),
        ),
    )
    monkeypatch.setattr(
        "app.regulasilens.service.extract_pdf_pages",
        lambda _: (PageText(page_number=1, text="fixture"),),
    )
    monkeypatch.setattr("app.regulasilens.service.parse_regulation_pages", lambda *_: parsed)

    engine = create_database_engine(Settings().resolved_database_url)
    session_factory = create_session_factory(engine)
    service = CorpusService(session_factory)
    tower = ControlTowerService(session_factory)
    calls = 0

    async def fetch(document: RegulationSource, known_checksum: str | None) -> FetchOutcome:
        nonlocal calls
        calls += 1
        if calls == 3:
            return FetchOutcome(
                status="quarantined",
                document_id=document.document_id,
                retrieved_at=datetime.now(UTC),
                checksum="f" * 64,
                byte_count=len(body),
                content_type=document.content_type,
                body=None,
                reason="checksum_mismatch_requires_manifest_review",
            )
        if known_checksum == document.expected_sha256:
            return FetchOutcome(
                status="unchanged",
                document_id=document.document_id,
                retrieved_at=datetime.now(UTC),
                checksum=document.expected_sha256,
                byte_count=len(body),
                content_type=document.content_type,
                body=None,
            )
        return FetchOutcome(
            status="accepted",
            document_id=document.document_id,
            retrieved_at=datetime.now(UTC),
            checksum=document.expected_sha256,
            byte_count=len(body),
            content_type=document.content_type,
            body=body,
        )

    first = await service.run_manifest(manifest, fetch)
    repeated = await service.run_manifest(manifest, fetch)
    rejected = await service.run_manifest(manifest, fetch)
    catalog = await service.list_documents(limit=500)
    detail = await service.get_document(pp.document_id)
    relations = await service.relations(pp.document_id)
    search = await service.search("definisi sistem elektronik")
    retrieval_manifest = await service.retrieval_manifest()
    datasets = await tower.list_datasets(limit=200)

    published_version_id = first.documents[0].dataset_version_id
    async with session_factory() as session:
        pp_document = await session.get(RegulationDocument, pp.document_id)
        assert pp_document is not None
        raw_count = int(
            await session.scalar(
                select(func.count())
                .select_from(RawRegulationDocument)
                .where(RawRegulationDocument.dataset_version_id == uuid.UUID(published_version_id))
            )
            or 0
        )
        section_count = int(
            await session.scalar(
                select(func.count())
                .select_from(RegulationSection)
                .join(
                    RegulationDocumentVersion,
                    RegulationDocumentVersion.id == RegulationSection.document_version_id,
                )
                .where(RegulationDocumentVersion.document_id == pp.document_id)
            )
            or 0
        )
        published_count = int(
            await session.scalar(
                select(func.count())
                .select_from(RegulationDocumentVersion)
                .where(
                    RegulationDocumentVersion.document_id == pp.document_id,
                    RegulationDocumentVersion.published.is_(True),
                )
            )
            or 0
        )
        quarantine_count = int(
            await session.scalar(
                select(func.count())
                .select_from(QuarantineRecord)
                .join(
                    DatasetVersion,
                    DatasetVersion.id == QuarantineRecord.dataset_version_id,
                )
                .where(DatasetVersion.dataset_id == pp_document.dataset_id)
            )
            or 0
        )
        incident_count = int(
            await session.scalar(
                select(func.count())
                .select_from(Incident)
                .where(Incident.dataset_id == pp_document.dataset_id)
            )
            or 0
        )
        relation_count = int(
            await session.scalar(
                select(func.count())
                .select_from(RegulationRelation)
                .where(RegulationRelation.source_document_id == pp.document_id)
            )
            or 0
        )
        published_version = await session.get(DatasetVersion, uuid.UUID(published_version_id))
    await engine.dispose()

    assert first.documents[0].status == "published"
    assert repeated.documents[0].status == "unchanged"
    assert rejected.documents[0].status == "rejected"
    assert repeated.documents[0].dataset_version_id == published_version_id
    assert raw_count == 1
    assert section_count == len(parsed.sections)
    assert published_count == 1
    assert quarantine_count == 1
    assert incident_count >= 1
    assert relation_count == 1
    catalog_document = next(item for item in catalog if item["document_id"] == pp.document_id)
    assert catalog_document["latest_version"]["dataset_version_id"] == published_version_id
    assert detail is not None and detail["sections"]
    assert relations is not None and relations[0]["resolved"] is False
    assert search["method"] == "hybrid_rerank"
    assert search["hits"][0]["document_id"] == pp.document_id
    assert search["hits"][0]["source_anchor"].startswith("page:")
    assert search["provenance"]["chunker_version"] == "fixed-1600-char-v1"
    assert retrieval_manifest["chunk_count"] >= 1
    assert retrieval_manifest["index_version"] == search["provenance"]["index_version"]
    assert any(item["code"] == f"regulation_{pp.document_id}" for item in datasets)
    assert published_version is not None and published_version.status == "published"
