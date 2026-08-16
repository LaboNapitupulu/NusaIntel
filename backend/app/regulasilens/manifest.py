from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

DOCUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

DocumentStatus = Literal["in_force", "amended", "revoked", "superseded", "unknown"]
RelationType = Literal["amends", "amended_by", "revokes", "revoked_by", "implements"]


class ManifestError(ValueError):
    """Raised when a source manifest violates a corpus safety rule."""


class UpdatePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mechanism: Literal["manual-review"]
    review_interval_days: int = Field(ge=1, le=365)
    change_detection: Literal["checksum-and-metadata"]


class SourcePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str = Field(min_length=2, max_length=255)
    purpose: str = Field(min_length=10, max_length=1000)
    attribution: str = Field(min_length=5, max_length=1000)
    approved_hosts: tuple[str, ...] = Field(min_length=1)
    redistribution: Literal["link-and-local-cache-only"]
    request_policy: str = Field(min_length=10, max_length=1000)


class RegulationRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relation_type: RelationType
    target_document_id: str | None = None
    target_citation: str
    evidence_url: str


class RegulationSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: Literal["undang-undang", "peraturan-pemerintah", "peraturan-menteri"]
    number: str = Field(min_length=1, max_length=32)
    year: int = Field(ge=1945, le=2200)
    title: str = Field(min_length=10, max_length=1000)
    issuer: str = Field(min_length=2, max_length=255)
    status: DocumentStatus
    effective_at: date
    status_checked_at: date
    source_page_url: str
    content_url: str
    content_type: Literal["application/pdf", "application/octet-stream"]
    file_format: Literal["pdf"]
    expected_sha256: str
    expected_byte_count: int = Field(gt=0, le=50_000_000)
    attribution: str = Field(min_length=5, max_length=1000)
    inclusion_reason: str = Field(min_length=10, max_length=1000)
    relations: tuple[RegulationRelation, ...] = ()

    @model_validator(mode="after")
    def validate_identity(self) -> RegulationSource:
        if not DOCUMENT_ID_PATTERN.fullmatch(self.document_id):
            raise ValueError("document_id must be lowercase kebab-case")
        if not SHA256_PATTERN.fullmatch(self.expected_sha256):
            raise ValueError("expected_sha256 must be a lowercase SHA-256 digest")
        return self


class CorpusManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    corpus_id: str
    corpus_version: str
    domain: Literal["personal-data-protection"]
    language: Literal["id"]
    scope_decision: str = Field(min_length=20, max_length=2000)
    inclusion_criteria: tuple[str, ...] = Field(min_length=1)
    exclusion_criteria: tuple[str, ...] = Field(min_length=1)
    status_vocabulary: dict[DocumentStatus, str]
    source_policy: SourcePolicy
    update_policy: UpdatePolicy
    documents: tuple[RegulationSource, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_manifest_graph(self) -> CorpusManifest:
        if not DOCUMENT_ID_PATTERN.fullmatch(self.corpus_id):
            raise ValueError("corpus_id must be lowercase kebab-case")

        document_ids = [document.document_id for document in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("document_id values must be unique")

        approved_hosts = set(self.source_policy.approved_hosts)
        for document in self.documents:
            for field_name, url in (
                ("source_page_url", document.source_page_url),
                ("content_url", document.content_url),
            ):
                parsed = urlparse(url)
                if parsed.scheme != "https" or parsed.hostname not in approved_hosts:
                    raise ValueError(
                        f"{document.document_id}.{field_name} must use an approved HTTPS host"
                    )
            for relation in document.relations:
                evidence = urlparse(relation.evidence_url)
                if evidence.scheme != "https" or evidence.hostname not in approved_hosts:
                    raise ValueError(
                        f"{document.document_id} relation evidence must use an approved HTTPS host"
                    )
                if relation.target_document_id == document.document_id:
                    raise ValueError("a document cannot relate to itself")
        return self


def load_manifest(path: Path) -> CorpusManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CorpusManifest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ManifestError(f"Invalid regulation manifest: {path.name}") from exc
