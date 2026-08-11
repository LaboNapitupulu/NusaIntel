from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.control_tower.contracts import build_indicator_contract
from app.main import create_app


async def healthy_probe() -> None:
    return None


class StubControlTower:
    def __init__(self) -> None:
        self.dataset_id = uuid.uuid4()
        self.incident_id = uuid.uuid4()

    async def list_datasets(self, **_: Any) -> list[dict[str, Any]]:
        return [
            {
                "id": str(self.dataset_id),
                "code": "tpt_silver",
                "name": "TPT normalized",
                "health": "healthy",
            }
        ]

    async def get_dataset(self, dataset_id: uuid.UUID) -> dict[str, Any] | None:
        if dataset_id != self.dataset_id:
            return None
        return {"id": str(dataset_id), "code": "tpt_silver"}

    async def quality_history(self, *_: Any, **__: Any) -> list[dict[str, Any]]:
        return []

    async def pipeline_runs(self, **_: Any) -> list[dict[str, Any]]:
        return []

    async def lineage(self, _: uuid.UUID) -> dict[str, list[dict[str, Any]]]:
        return {"nodes": [], "edges": []}

    async def incidents(self, **_: Any) -> list[dict[str, Any]]:
        return []

    async def resolve_incident(
        self, incident_id: uuid.UUID, *, status: str, resolution_note: str
    ) -> dict[str, Any] | None:
        if incident_id != self.incident_id:
            return None
        return {
            "id": str(incident_id),
            "status": status,
            "resolution_note": resolution_note,
        }

    async def create_exception(self, *_: Any, **__: Any) -> dict[str, Any]:
        return {"id": str(uuid.uuid4()), "active": True}


@pytest.fixture
def stub_app() -> tuple[Any, StubControlTower]:
    app = create_app(Settings(app_env="test"), database_probe=healthy_probe)
    stub = StubControlTower()
    app.state.control_tower_service = stub
    return app, stub


@pytest.mark.asyncio
async def test_catalog_and_dataset_detail(stub_app: tuple[Any, StubControlTower]) -> None:
    app, stub = stub_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        catalog = await client.get("/api/v1/datasets")
        detail = await client.get(f"/api/v1/datasets/{stub.dataset_id}")

    assert catalog.status_code == 200
    assert catalog.json()["items"][0]["code"] == "tpt_silver"
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_contract_validation_endpoint_rejects_unknown_columns(
    stub_app: tuple[Any, StubControlTower],
) -> None:
    app, _ = stub_app
    contract = build_indicator_contract("tpt_silver", layer="silver").model_dump(mode="json")
    contract["values"][0]["column"] = "unknown"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        valid = await client.post(
            "/api/v1/contracts/validate",
            json=build_indicator_contract("tpt_silver", layer="silver").model_dump(mode="json"),
        )
        invalid = await client.post("/api/v1/contracts/validate", json=contract)

    assert valid.status_code == 200
    assert valid.json()["contract_version"] == 2
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_incident_resolution_requires_audit_note(
    stub_app: tuple[Any, StubControlTower],
) -> None:
    app, stub = stub_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing_note = await client.patch(
            f"/api/v1/incidents/{stub.incident_id}",
            json={"status": "resolved", "resolution_note": ""},
        )
        resolved = await client.patch(
            f"/api/v1/incidents/{stub.incident_id}",
            json={"status": "resolved", "resolution_note": "Fixture source corrected"},
        )

    assert missing_note.status_code == 422
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_expired_exception_is_rejected_at_api_boundary(
    stub_app: tuple[Any, StubControlTower],
) -> None:
    app, stub = stub_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/datasets/{stub.dataset_id}/exceptions",
            json={
                "check_code": "column_region_code",
                "reason": "Temporary source transition",
                "owner": "Data Steward",
                "expires_at": datetime(2020, 1, 1, tzinfo=UTC).isoformat(),
            },
        )

    assert response.status_code == 422
