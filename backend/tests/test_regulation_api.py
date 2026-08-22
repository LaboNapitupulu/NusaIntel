from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


async def healthy_probe() -> None:
    return None


class StubCorpusService:
    async def list_documents(self, **_: Any) -> list[dict[str, Any]]:
        return [
            {
                "document_id": "uu-27-2022",
                "title": "Pelindungan Data Pribadi",
                "status": "in_force",
            }
        ]

    async def get_document(self, document_id: str, **_: Any) -> dict[str, Any] | None:
        if document_id != "uu-27-2022":
            return None
        return {
            "document_id": document_id,
            "title": "Pelindungan Data Pribadi",
            "sections": [
                {
                    "section_id": "section-1",
                    "heading": "Pasal 1",
                    "source_anchor": "page:1:line:1",
                }
            ],
        }

    async def relations(self, document_id: str) -> list[dict[str, Any]] | None:
        if document_id != "uu-27-2022":
            return None
        return []

    async def search(self, query: str, **_: Any) -> dict[str, Any]:
        return {
            "query": query,
            "method": "hybrid",
            "count": 1,
            "hits": [
                {
                    "section_ids": ["section-1"],
                    "source_anchor": "page:1:line:1",
                }
            ],
            "provenance": {"index_version": "index-v1"},
        }

    async def retrieval_manifest(self, **_: Any) -> dict[str, Any]:
        return {"index_version": "index-v1", "chunk_count": 1}


@pytest.mark.asyncio
async def test_regulation_catalog_detail_and_relations() -> None:
    app = create_app(Settings(app_env="test"), database_probe=healthy_probe)
    app.state.regulation_service = StubCorpusService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        catalog = await client.get("/api/v1/regulations")
        detail = await client.get("/api/v1/regulations/uu-27-2022")
        relations = await client.get("/api/v1/regulations/uu-27-2022/relations")
        missing = await client.get("/api/v1/regulations/missing")
        search = await client.post("/api/v1/regulations/search", json={"query": "hak akses data"})
        manifest = await client.get("/api/v1/regulations/retrieval/manifest")

    assert catalog.status_code == 200
    assert catalog.json()["items"][0]["status"] == "in_force"
    assert detail.status_code == 200
    assert detail.json()["sections"][0]["source_anchor"] == "page:1:line:1"
    assert relations.status_code == 200
    assert missing.status_code == 404
    assert search.status_code == 200
    assert search.json()["hits"][0]["source_anchor"] == "page:1:line:1"
    assert manifest.status_code == 200
    assert manifest.json()["index_version"] == "index-v1"


@pytest.mark.asyncio
async def test_regulation_api_is_unavailable_without_storage() -> None:
    app = create_app(Settings(app_env="test"), database_probe=healthy_probe)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/regulations")

    assert response.status_code == 503
