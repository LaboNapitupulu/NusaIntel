from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    DataContract,
    Dataset,
    DatasetVersion,
    Incident,
    PipelineRun,
    QualityCheckResult,
    QuarantineRecord,
    RawRegulationDocument,
    RegulationDocument,
    RegulationDocumentVersion,
    RegulationRelation,
    RegulationSection,
    Source,
)
from app.regulasilens.ingestion import FetchOutcome
from app.regulasilens.manifest import CorpusManifest, RegulationSource
from app.regulasilens.parser import (
    DocumentParseError,
    ParseOutcome,
    extract_pdf_pages,
    parse_regulation_pages,
)

FetchDocument = Callable[[RegulationSource, str | None], Awaitable[FetchOutcome]]

CONTRACT_SPECIFICATION: dict[str, Any] = {
    "schema_version": 1,
    "required_metadata": [
        "document_id",
        "document_type",
        "number",
        "year",
        "title",
        "issuer",
        "status",
        "source_page_url",
        "content_url",
        "expected_sha256",
    ],
    "critical_checks": [
        "checksum_match",
        "pdf_extractable",
        "sections_present",
        "pasal_present",
        "section_identity_unique",
        "source_anchor_coverage",
    ],
    "minimum_source_anchor_coverage": 0.95,
}
CONTRACT_CHECKSUM = hashlib.sha256(
    json.dumps(CONTRACT_SPECIFICATION, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


@dataclass(frozen=True, slots=True)
class CorpusDocumentOutcome:
    document_id: str
    status: Literal["published", "unchanged", "rejected"]
    dataset_version_id: str
    run_id: str
    checksum: str
    section_count: int
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CorpusRunOutcome:
    corpus_id: str
    corpus_version: str
    documents: tuple[CorpusDocumentOutcome, ...]

    @property
    def successful(self) -> bool:
        return all(item.status in {"published", "unchanged"} for item in self.documents)


class CorpusService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def run_manifest(
        self, manifest: CorpusManifest, fetch: FetchDocument
    ) -> CorpusRunOutcome:
        await self._synchronize_catalog(manifest)
        outcomes: list[CorpusDocumentOutcome] = []
        for document in manifest.documents:
            dataset_id = await self._dataset_id(document.document_id)
            known = await self._latest_published_checksum(dataset_id)
            fetched = await fetch(document, known)
            if fetched.status == "unchanged":
                outcomes.append(await self._record_unchanged(document, dataset_id, fetched))
                continue
            if fetched.status == "quarantined" or fetched.body is None:
                outcomes.append(
                    await self._record_rejection(
                        document,
                        dataset_id,
                        fetched,
                        fetched.reason or "missing_download_body",
                    )
                )
                continue
            try:
                parsed = parse_regulation_pages(
                    document.document_id,
                    extract_pdf_pages(fetched.body),
                )
            except DocumentParseError:
                outcomes.append(
                    await self._record_rejection(
                        document,
                        dataset_id,
                        fetched,
                        "pdf_extraction_failed",
                    )
                )
                continue
            outcomes.append(
                await self._persist_parsed(
                    manifest,
                    document,
                    dataset_id,
                    fetched,
                    parsed,
                )
            )
        return CorpusRunOutcome(
            corpus_id=manifest.corpus_id,
            corpus_version=manifest.corpus_version,
            documents=tuple(outcomes),
        )

    async def list_documents(self, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            documents = list(
                await session.scalars(
                    select(RegulationDocument)
                    .where(RegulationDocument.active.is_(True))
                    .order_by(RegulationDocument.year.desc(), RegulationDocument.document_id)
                    .limit(limit)
                    .offset(offset)
                )
            )
            return [await self._document_summary(session, document) for document in documents]

    async def get_document(
        self,
        document_id: str,
        *,
        section_limit: int = 200,
        section_offset: int = 0,
    ) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            document = await session.get(RegulationDocument, document_id)
            if document is None:
                return None
            summary = await self._document_summary(session, document)
            version = await self._latest_published_version(session, document_id)
            sections: list[RegulationSection] = []
            if version is not None:
                sections = list(
                    await session.scalars(
                        select(RegulationSection)
                        .where(RegulationSection.document_version_id == version.id)
                        .order_by(RegulationSection.section_order)
                        .limit(section_limit)
                        .offset(section_offset)
                    )
                )
            summary["sections"] = [self._serialize_section(section) for section in sections]
            summary["section_limit"] = section_limit
            summary["section_offset"] = section_offset
            return summary

    async def relations(self, document_id: str) -> list[dict[str, Any]] | None:
        async with self._session_factory() as session:
            if await session.get(RegulationDocument, document_id) is None:
                return None
            relations = list(
                await session.scalars(
                    select(RegulationRelation)
                    .where(RegulationRelation.source_document_id == document_id)
                    .order_by(RegulationRelation.relation_type, RegulationRelation.target_citation)
                )
            )
            return [
                {
                    "id": str(relation.id),
                    "relation_type": relation.relation_type,
                    "target_document_id": relation.target_document_id,
                    "target_citation": relation.target_citation,
                    "evidence_url": relation.evidence_url,
                    "resolved": relation.resolved,
                }
                for relation in relations
            ]

    async def _synchronize_catalog(self, manifest: CorpusManifest) -> None:
        async with self._session_factory() as session, session.begin():
            source = await session.scalar(select(Source).where(Source.code == "jdih_bpk"))
            if source is None:
                source = Source(
                    code="jdih_bpk",
                    name="Database Peraturan BPK",
                    base_url="https://peraturan.bpk.go.id/",
                    owner=manifest.source_policy.owner,
                    attribution=manifest.source_policy.attribution,
                )
                session.add(source)
                await session.flush()

            for item in manifest.documents:
                dataset = await session.scalar(
                    select(Dataset).where(
                        Dataset.source_id == source.id,
                        Dataset.code == f"regulation_{item.document_id}",
                    )
                )
                if dataset is None:
                    dataset = Dataset(
                        source_id=source.id,
                        code=f"regulation_{item.document_id}",
                        name=f"RegulasiLens {item.document_id}",
                        layer="regulation",
                        owner="RegulasiLens",
                        freshness_sla_seconds=manifest.update_policy.review_interval_days * 86400,
                        active=True,
                    )
                    session.add(dataset)
                    await session.flush()
                else:
                    dataset.freshness_sla_seconds = (
                        manifest.update_policy.review_interval_days * 86400
                    )
                    dataset.active = True

                document = await session.get(RegulationDocument, item.document_id)
                if document is None:
                    document = RegulationDocument(
                        document_id=item.document_id, dataset_id=dataset.id
                    )
                    session.add(document)
                self._apply_manifest_metadata(document, manifest, item)

                contract = await session.scalar(
                    select(DataContract).where(
                        DataContract.dataset_id == dataset.id,
                        DataContract.version == 1,
                    )
                )
                if contract is None:
                    session.add(
                        DataContract(
                            dataset_id=dataset.id,
                            version=1,
                            specification=CONTRACT_SPECIFICATION,
                            checksum=CONTRACT_CHECKSUM,
                            effective_at=datetime.now(UTC),
                        )
                    )

            document_ids = [item.document_id for item in manifest.documents]
            await session.execute(
                delete(RegulationRelation).where(
                    RegulationRelation.source_document_id.in_(document_ids)
                )
            )
            manifest_ids = set(document_ids)
            for item in manifest.documents:
                for relation in item.relations:
                    target_id = (
                        relation.target_document_id
                        if relation.target_document_id in manifest_ids
                        else None
                    )
                    session.add(
                        RegulationRelation(
                            source_document_id=item.document_id,
                            relation_type=relation.relation_type,
                            target_document_id=target_id,
                            target_citation=relation.target_citation,
                            evidence_url=relation.evidence_url,
                            resolved=target_id is not None,
                        )
                    )

    async def _dataset_id(self, document_id: str) -> uuid.UUID:
        async with self._session_factory() as session:
            value = await session.scalar(
                select(RegulationDocument.dataset_id).where(
                    RegulationDocument.document_id == document_id
                )
            )
            if value is None:
                raise RuntimeError(f"Missing synchronized dataset for {document_id}")
            return value

    async def _latest_published_checksum(self, dataset_id: uuid.UUID) -> str | None:
        async with self._session_factory() as session:
            checksum: str | None = await session.scalar(
                select(DatasetVersion.checksum)
                .where(
                    DatasetVersion.dataset_id == dataset_id,
                    DatasetVersion.status == "published",
                )
                .order_by(DatasetVersion.processed_at.desc())
                .limit(1)
            )
            return checksum

    async def _record_unchanged(
        self,
        document: RegulationSource,
        dataset_id: uuid.UUID,
        fetched: FetchOutcome,
    ) -> CorpusDocumentOutcome:
        async with self._session_factory() as session, session.begin():
            version = await session.scalar(
                select(DatasetVersion).where(
                    DatasetVersion.dataset_id == dataset_id,
                    DatasetVersion.checksum == fetched.checksum,
                    DatasetVersion.status == "published",
                )
            )
            if version is None:
                raise RuntimeError(
                    f"Unchanged result has no published version: {document.document_id}"
                )
            run = PipelineRun(
                dataset_version_id=version.id,
                run_type="regulation_ingestion",
                status="succeeded",
                started_at=fetched.retrieved_at,
                finished_at=datetime.now(UTC),
                correlation_id=f"regulation:{document.document_id}:{uuid.uuid4().hex}",
            )
            session.add(run)
            await session.flush()
            section_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(RegulationSection)
                    .join(
                        RegulationDocumentVersion,
                        RegulationDocumentVersion.id == RegulationSection.document_version_id,
                    )
                    .where(RegulationDocumentVersion.dataset_version_id == version.id)
                )
                or 0
            )
            return CorpusDocumentOutcome(
                document_id=document.document_id,
                status="unchanged",
                dataset_version_id=str(version.id),
                run_id=str(run.id),
                checksum=version.checksum,
                section_count=section_count,
            )

    async def _record_rejection(
        self,
        document: RegulationSource,
        dataset_id: uuid.UUID,
        fetched: FetchOutcome,
        reason: str,
    ) -> CorpusDocumentOutcome:
        checksum = (
            fetched.checksum
            or hashlib.sha256(
                f"{document.document_id}:{reason}:{fetched.retrieved_at.date()}".encode()
            ).hexdigest()
        )
        async with self._session_factory() as session, session.begin():
            version = await session.scalar(
                select(DatasetVersion).where(
                    DatasetVersion.dataset_id == dataset_id,
                    DatasetVersion.source_identity == document.content_url,
                    DatasetVersion.checksum == checksum,
                )
            )
            if version is None:
                version = DatasetVersion(
                    dataset_id=dataset_id,
                    source_identity=document.content_url,
                    checksum=checksum,
                    source_reference_at=datetime.combine(
                        document.effective_at, time.min, tzinfo=UTC
                    ),
                    retrieved_at=fetched.retrieved_at,
                    processed_at=datetime.now(UTC),
                    row_count=0,
                    status="rejected",
                )
                session.add(version)
                await session.flush()
            run = PipelineRun(
                dataset_version_id=version.id,
                run_type="regulation_ingestion",
                status="failed",
                started_at=fetched.retrieved_at,
                finished_at=datetime.now(UTC),
                correlation_id=f"regulation:{document.document_id}:{uuid.uuid4().hex}",
                error_category=reason,
            )
            session.add(run)
            await session.flush()
            check_code = "regulation_candidate_rejected"
            session.add(
                QualityCheckResult(
                    dataset_version_id=version.id,
                    pipeline_run_id=run.id,
                    check_code=check_code,
                    severity="critical",
                    status="failed",
                    expected={"manifest_checksum": document.expected_sha256},
                    observed={
                        "reason": reason,
                        "checksum": fetched.checksum,
                        "content_type": fetched.content_type,
                        "byte_count": fetched.byte_count,
                    },
                )
            )
            existing_quarantine = await session.scalar(
                select(QuarantineRecord.id).where(
                    QuarantineRecord.dataset_version_id == version.id,
                    QuarantineRecord.source_key == document.content_url,
                    QuarantineRecord.reason_code == reason,
                )
            )
            if existing_quarantine is None:
                session.add(
                    QuarantineRecord(
                        dataset_version_id=version.id,
                        pipeline_run_id=run.id,
                        reason_code=reason,
                        source_key=document.content_url,
                        safe_payload={
                            "document_id": document.document_id,
                            "content_type": fetched.content_type,
                            "byte_count": fetched.byte_count,
                        },
                    )
                )
            session.add(
                Incident(
                    dataset_id=dataset_id,
                    pipeline_run_id=run.id,
                    check_code=check_code,
                    severity="critical",
                    status="open",
                    title=f"Regulation candidate rejected: {document.document_id}",
                )
            )
            return CorpusDocumentOutcome(
                document_id=document.document_id,
                status="rejected",
                dataset_version_id=str(version.id),
                run_id=str(run.id),
                checksum=checksum,
                section_count=0,
                reason=reason,
            )

    async def _persist_parsed(
        self,
        manifest: CorpusManifest,
        document: RegulationSource,
        dataset_id: uuid.UUID,
        fetched: FetchOutcome,
        parsed: ParseOutcome,
    ) -> CorpusDocumentOutcome:
        assert fetched.body is not None
        assert fetched.checksum is not None
        checks = self._parse_checks(parsed)
        publishable = all(check[2] for check in checks)
        async with self._session_factory() as session, session.begin():
            existing = await session.scalar(
                select(DatasetVersion).where(
                    DatasetVersion.dataset_id == dataset_id,
                    DatasetVersion.source_identity == document.content_url,
                    DatasetVersion.checksum == fetched.checksum,
                )
            )
            if existing is not None and existing.status == "published":
                run = PipelineRun(
                    dataset_version_id=existing.id,
                    run_type="regulation_ingestion",
                    status="succeeded",
                    started_at=fetched.retrieved_at,
                    finished_at=datetime.now(UTC),
                    correlation_id=f"regulation:{document.document_id}:{uuid.uuid4().hex}",
                )
                session.add(run)
                await session.flush()
                return CorpusDocumentOutcome(
                    document_id=document.document_id,
                    status="unchanged",
                    dataset_version_id=str(existing.id),
                    run_id=str(run.id),
                    checksum=existing.checksum,
                    section_count=existing.row_count,
                )

            if existing is None:
                version = DatasetVersion(
                    dataset_id=dataset_id,
                    source_identity=document.content_url,
                    checksum=fetched.checksum,
                    source_reference_at=datetime.combine(
                        document.effective_at, time.min, tzinfo=UTC
                    ),
                    retrieved_at=fetched.retrieved_at,
                    processed_at=datetime.now(UTC),
                    row_count=len(parsed.sections),
                    status="published" if publishable else "rejected",
                )
                session.add(version)
                await session.flush()
            else:
                version = existing
                version.retrieved_at = fetched.retrieved_at
                version.processed_at = datetime.now(UTC)
                version.row_count = len(parsed.sections)
                version.status = "published" if publishable else "rejected"
            run = PipelineRun(
                dataset_version_id=version.id,
                run_type="regulation_ingestion",
                status="succeeded" if publishable else "failed",
                started_at=fetched.retrieved_at,
                finished_at=datetime.now(UTC),
                correlation_id=f"regulation:{document.document_id}:{uuid.uuid4().hex}",
                error_category=None if publishable else "parser_quality_failed",
            )
            session.add(run)
            raw_exists = await session.scalar(
                select(RawRegulationDocument.id).where(
                    RawRegulationDocument.dataset_version_id == version.id
                )
            )
            if raw_exists is None:
                session.add(
                    RawRegulationDocument(
                        dataset_version_id=version.id,
                        source_url=document.content_url,
                        content_type=fetched.content_type or document.content_type,
                        content_sha256=fetched.checksum,
                        byte_count=fetched.byte_count,
                        body=fetched.body,
                    )
                )
            confidence = (
                sum(
                    (Decimal(str(section.confidence)) for section in parsed.sections),
                    start=Decimal("0"),
                )
                / len(parsed.sections)
                if parsed.sections
                else Decimal("0")
            )
            document_version = await session.scalar(
                select(RegulationDocumentVersion).where(
                    RegulationDocumentVersion.document_id == document.document_id,
                    RegulationDocumentVersion.checksum == fetched.checksum,
                    RegulationDocumentVersion.parser_version == parsed.parser_version,
                )
            )
            new_document_version = document_version is None
            if document_version is None:
                document_version = RegulationDocumentVersion(
                    document_id=document.document_id,
                    dataset_version_id=version.id,
                    manifest_version=manifest.corpus_version,
                    checksum=fetched.checksum,
                    byte_count=fetched.byte_count,
                    content_type=fetched.content_type or document.content_type,
                    retrieved_at=fetched.retrieved_at,
                    parser_version=parsed.parser_version,
                    parser_status=parsed.status,
                    parser_confidence=confidence,
                    section_count=len(parsed.sections),
                    source_anchor_coverage=Decimal(str(parsed.source_anchor_coverage)),
                    published=publishable,
                )
                session.add(document_version)
                await session.flush()
            else:
                document_version.dataset_version_id = version.id
                document_version.manifest_version = manifest.corpus_version
                document_version.byte_count = fetched.byte_count
                document_version.content_type = fetched.content_type or document.content_type
                document_version.retrieved_at = fetched.retrieved_at
                document_version.parser_status = parsed.status
                document_version.parser_confidence = confidence
                document_version.section_count = len(parsed.sections)
                document_version.source_anchor_coverage = Decimal(
                    str(parsed.source_anchor_coverage)
                )
            if publishable:
                await session.execute(
                    update(RegulationDocumentVersion)
                    .where(
                        RegulationDocumentVersion.document_id == document.document_id,
                        RegulationDocumentVersion.published.is_(True),
                    )
                    .values(published=False)
                )
            document_version.published = publishable
            if new_document_version:
                session.add_all(
                    [
                        RegulationSection(
                            document_version_id=document_version.id,
                            section_key=section.section_id,
                            section_order=section.order,
                            kind=section.kind,
                            heading=section.heading,
                            text=section.text,
                            hierarchy=list(section.hierarchy),
                            page_number=section.page_number,
                            line_number=section.line_number,
                            source_anchor=section.source_anchor,
                            confidence=Decimal(str(section.confidence)),
                        )
                        for section in parsed.sections
                    ]
                )
            contract_id = await session.scalar(
                select(DataContract.id).where(
                    DataContract.dataset_id == dataset_id,
                    DataContract.version == 1,
                )
            )
            for code, severity, passed, expected, observed in checks:
                session.add(
                    QualityCheckResult(
                        dataset_version_id=version.id,
                        pipeline_run_id=run.id,
                        data_contract_id=contract_id,
                        check_code=code,
                        severity=severity,
                        status="passed" if passed else "failed",
                        expected=expected,
                        observed=observed,
                    )
                )
                if not passed:
                    session.add(
                        Incident(
                            dataset_id=dataset_id,
                            pipeline_run_id=run.id,
                            check_code=code,
                            severity=severity,
                            status="open",
                            title=f"Regulation parser quality failed: {document.document_id}",
                        )
                    )
            if not publishable:
                existing_quarantine = await session.scalar(
                    select(QuarantineRecord.id).where(
                        QuarantineRecord.dataset_version_id == version.id,
                        QuarantineRecord.source_key == document.content_url,
                        QuarantineRecord.reason_code == "parser_quality_failed",
                    )
                )
                if existing_quarantine is None:
                    session.add(
                        QuarantineRecord(
                            dataset_version_id=version.id,
                            pipeline_run_id=run.id,
                            reason_code="parser_quality_failed",
                            source_key=document.content_url,
                            safe_payload={
                                "document_id": document.document_id,
                                "reasons": list(parsed.reasons),
                                "section_count": len(parsed.sections),
                            },
                        )
                    )
            return CorpusDocumentOutcome(
                document_id=document.document_id,
                status="published" if publishable else "rejected",
                dataset_version_id=str(version.id),
                run_id=str(run.id),
                checksum=fetched.checksum,
                section_count=len(parsed.sections),
                reason=None if publishable else "parser_quality_failed",
            )

    @staticmethod
    def _parse_checks(
        parsed: ParseOutcome,
    ) -> list[tuple[str, str, bool, dict[str, Any], dict[str, Any]]]:
        orders = [section.order for section in parsed.sections]
        keys = [section.section_id for section in parsed.sections]
        return [
            (
                "sections_present",
                "critical",
                bool(parsed.sections),
                {"minimum": 1},
                {"count": len(parsed.sections)},
            ),
            (
                "pasal_present",
                "critical",
                any(section.kind == "pasal" for section in parsed.sections),
                {"minimum": 1},
                {"count": sum(section.kind == "pasal" for section in parsed.sections)},
            ),
            (
                "section_identity_unique",
                "critical",
                len(keys) == len(set(keys)) and orders == list(range(1, len(orders) + 1)),
                {"unique": True, "continuous_order": True},
                {"unique": len(keys) == len(set(keys)), "orders": len(orders)},
            ),
            (
                "source_anchor_coverage",
                "critical",
                parsed.source_anchor_coverage >= 0.95,
                {"minimum": 0.95},
                {"coverage": parsed.source_anchor_coverage},
            ),
            (
                "parser_status",
                "critical",
                parsed.status == "parsed",
                {"status": "parsed"},
                {"status": parsed.status, "reasons": list(parsed.reasons)},
            ),
        ]

    @staticmethod
    def _apply_manifest_metadata(
        document: RegulationDocument,
        manifest: CorpusManifest,
        item: RegulationSource,
    ) -> None:
        document.domain = manifest.domain
        document.document_type = item.document_type
        document.number = item.number
        document.year = item.year
        document.title = item.title
        document.issuer = item.issuer
        document.status = item.status
        document.effective_at = item.effective_at
        document.status_checked_at = item.status_checked_at
        document.source_page_url = item.source_page_url
        document.content_url = item.content_url
        document.attribution = item.attribution
        document.active = item.status != "unknown"

    async def _document_summary(
        self, session: AsyncSession, document: RegulationDocument
    ) -> dict[str, Any]:
        version = await self._latest_published_version(session, document.document_id)
        unresolved = int(
            await session.scalar(
                select(func.count())
                .select_from(RegulationRelation)
                .where(
                    RegulationRelation.source_document_id == document.document_id,
                    RegulationRelation.resolved.is_(False),
                )
            )
            or 0
        )
        return {
            "document_id": document.document_id,
            "domain": document.domain,
            "document_type": document.document_type,
            "number": document.number,
            "year": document.year,
            "title": document.title,
            "issuer": document.issuer,
            "status": document.status,
            "effective_at": document.effective_at,
            "status_checked_at": document.status_checked_at,
            "source_page_url": document.source_page_url,
            "attribution": document.attribution,
            "latest_version": (
                {
                    "id": str(version.id),
                    "dataset_version_id": str(version.dataset_version_id),
                    "manifest_version": version.manifest_version,
                    "checksum": version.checksum,
                    "retrieved_at": version.retrieved_at,
                    "parser_version": version.parser_version,
                    "parser_status": version.parser_status,
                    "parser_confidence": version.parser_confidence,
                    "section_count": version.section_count,
                    "source_anchor_coverage": version.source_anchor_coverage,
                }
                if version is not None
                else None
            ),
            "unresolved_relation_count": unresolved,
        }

    @staticmethod
    async def _latest_published_version(
        session: AsyncSession, document_id: str
    ) -> RegulationDocumentVersion | None:
        version: RegulationDocumentVersion | None = await session.scalar(
            select(RegulationDocumentVersion)
            .where(
                RegulationDocumentVersion.document_id == document_id,
                RegulationDocumentVersion.published.is_(True),
            )
            .order_by(RegulationDocumentVersion.retrieved_at.desc())
            .limit(1)
        )
        return version

    @staticmethod
    def _serialize_section(section: RegulationSection) -> dict[str, Any]:
        return {
            "section_id": section.section_key,
            "order": section.section_order,
            "kind": section.kind,
            "heading": section.heading,
            "text": section.text,
            "hierarchy": section.hierarchy,
            "page_number": section.page_number,
            "line_number": section.line_number,
            "source_anchor": section.source_anchor,
            "confidence": section.confidence,
        }
