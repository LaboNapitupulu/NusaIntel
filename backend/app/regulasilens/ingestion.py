from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import httpx

from app.regulasilens.manifest import RegulationSource

MAX_DOCUMENT_BYTES = 50_000_000


@dataclass(frozen=True, slots=True)
class FetchOutcome:
    status: Literal["accepted", "unchanged", "quarantined"]
    document_id: str
    retrieved_at: datetime
    checksum: str | None
    byte_count: int
    content_type: str | None
    body: bytes | None
    reason: str | None = None


async def fetch_regulation(
    document: RegulationSource,
    *,
    client: httpx.AsyncClient,
    known_checksum: str | None = None,
    max_bytes: int = MAX_DOCUMENT_BYTES,
) -> FetchOutcome:
    retrieved_at = datetime.now(UTC)
    try:
        async with client.stream("GET", document.content_url) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            declared_length = response.headers.get("content-length")
            if declared_length and int(declared_length) > max_bytes:
                return _quarantine(
                    document, retrieved_at, content_type, "declared_size_exceeds_limit"
                )

            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    return _quarantine(
                        document, retrieved_at, content_type, "download_size_exceeds_limit"
                    )
    except (httpx.HTTPError, ValueError):
        return _quarantine(document, retrieved_at, None, "retrieval_failed")

    downloaded = bytes(body)
    checksum = hashlib.sha256(downloaded).hexdigest()
    if content_type != document.content_type:
        return _quarantine(
            document,
            retrieved_at,
            content_type,
            "unexpected_content_type",
            checksum=checksum,
            byte_count=len(downloaded),
        )
    if not downloaded.startswith(b"%PDF-"):
        return _quarantine(
            document,
            retrieved_at,
            content_type,
            "invalid_pdf_signature",
            checksum=checksum,
            byte_count=len(downloaded),
        )
    if checksum != document.expected_sha256:
        return _quarantine(
            document,
            retrieved_at,
            content_type,
            "checksum_mismatch_requires_manifest_review",
            checksum=checksum,
            byte_count=len(downloaded),
        )
    if len(downloaded) != document.expected_byte_count:
        return _quarantine(
            document,
            retrieved_at,
            content_type,
            "byte_count_mismatch_requires_manifest_review",
            checksum=checksum,
            byte_count=len(downloaded),
        )

    status: Literal["accepted", "unchanged"] = (
        "unchanged" if known_checksum == checksum else "accepted"
    )
    return FetchOutcome(
        status=status,
        document_id=document.document_id,
        retrieved_at=retrieved_at,
        checksum=checksum,
        byte_count=len(downloaded),
        content_type=content_type,
        body=None if status == "unchanged" else downloaded,
    )


def _quarantine(
    document: RegulationSource,
    retrieved_at: datetime,
    content_type: str | None,
    reason: str,
    *,
    checksum: str | None = None,
    byte_count: int = 0,
) -> FetchOutcome:
    return FetchOutcome(
        status="quarantined",
        document_id=document.document_id,
        retrieved_at=retrieved_at,
        checksum=checksum,
        byte_count=byte_count,
        content_type=content_type,
        body=None,
        reason=reason,
    )
