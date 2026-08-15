from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

from app.regulasilens.ingestion import fetch_regulation
from app.regulasilens.manifest import RegulationSource, load_manifest

MANIFEST_PATH = (
    Path(__file__).parents[2] / "regulations" / "manifests" / "personal-data-protection.v1.json"
)


def _document_for(body: bytes) -> RegulationSource:
    document = load_manifest(MANIFEST_PATH).documents[0]
    return document.model_copy(
        update={
            "expected_sha256": hashlib.sha256(body).hexdigest(),
            "expected_byte_count": len(body),
        }
    )


@pytest.mark.asyncio
async def test_fetch_accepts_only_pinned_official_pdf() -> None:
    body = b"%PDF-1.7\nfixture"
    document = _document_for(body)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=body,
            headers={
                "content-type": document.content_type,
                "content-length": str(len(body)),
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        outcome = await fetch_regulation(document, client=client)

    assert outcome.status == "accepted"
    assert outcome.body == body
    assert outcome.checksum == document.expected_sha256


@pytest.mark.asyncio
async def test_fetch_detects_unchanged_checksum_without_returning_body() -> None:
    body = b"%PDF-1.7\nfixture"
    document = _document_for(body)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": document.content_type})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        outcome = await fetch_regulation(
            document,
            client=client,
            known_checksum=document.expected_sha256,
        )

    assert outcome.status == "unchanged"
    assert outcome.body is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "content_type", "reason"),
    [
        (b"<html>blocked</html>", "text/html", "unexpected_content_type"),
        (b"not-a-pdf", "application/octet-stream", "invalid_pdf_signature"),
        (
            b"%PDF-1.7\nchanged",
            "application/octet-stream",
            "checksum_mismatch_requires_manifest_review",
        ),
    ],
)
async def test_fetch_quarantines_unsafe_or_changed_content(
    body: bytes, content_type: str, reason: str
) -> None:
    expected_body = b"%PDF-1.7\nfixture"
    document = _document_for(expected_body)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": content_type})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        outcome = await fetch_regulation(document, client=client)

    assert outcome.status == "quarantined"
    assert outcome.reason == reason
    assert outcome.body is None
