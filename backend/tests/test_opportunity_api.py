from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from app.opportunity.schemas import ScoreRequest, SensitivityRequest
from app.opportunity.service import OpportunityService


async def healthy_probe() -> None:
    return None


class StubOpportunityService:
    async def indicator_catalog(self) -> list[dict[str, Any]]:
        return [{"code": "hdi", "unit": "Poin", "quality_status": "healthy"}]

    async def region_catalog(self) -> list[dict[str, str]]:
        return [{"code": "1100", "name": "ACEH"}, {"code": "1200", "name": "SUMUT"}]

    async def compare(self, payload: Any) -> dict[str, Any]:
        return {"year": payload.year, "regions": []}

    async def score(self, payload: Any) -> dict[str, Any]:
        return {"year": payload.year, "results": [], "configuration": {}}

    async def sensitivity(self, payload: Any) -> dict[str, Any]:
        return {"year": payload.year, "scenario_count": 2, "stability": []}

    async def export_report(self, payload: Any) -> dict[str, Any]:
        return {
            "generated_at": "2026-08-11T00:00:00Z",
            "configuration": payload.model_dump(mode="json"),
            "dataset_versions": {"hdi": {"version_id": "version-1"}},
        }


class ExportHarness(OpportunityService):
    def __init__(self) -> None:
        self.received_score_request: ScoreRequest | None = None

    async def score(self, request: ScoreRequest) -> dict[str, Any]:
        self.received_score_request = request
        return {"dataset_versions": {}, "sources": {}, "results": []}

    async def sensitivity(self, request: SensitivityRequest) -> dict[str, Any]:
        return {
            "perturbation": request.perturbation,
            "scenario_count": 0,
            "stability": [],
            "disclaimer": "not confidence",
        }


@pytest.fixture
def opportunity_app() -> Any:
    app = create_app(Settings(app_env="test"), database_probe=healthy_probe)
    app.state.opportunity_service = StubOpportunityService()
    return app


@pytest.mark.asyncio
async def test_catalog_region_and_analysis_endpoints(opportunity_app: Any) -> None:
    payload = {
        "region_codes": ["1100", "1200"],
        "year": 2025,
        "normalization": "min_max",
        "coverage_threshold": "1",
        "indicators": [{"code": "hdi", "weight": "100", "direction": "higher"}],
    }
    async with AsyncClient(
        transport=ASGITransport(app=opportunity_app), base_url="http://test"
    ) as client:
        indicators = await client.get("/api/v1/opportunity/indicators")
        regions = await client.get("/api/v1/opportunity/regions")
        compare = await client.post(
            "/api/v1/opportunity/compare",
            json={
                "region_codes": payload["region_codes"],
                "indicator_codes": ["hdi"],
                "year": payload["year"],
                "normalization": "min_max",
            },
        )
        score = await client.post("/api/v1/opportunity/score", json=payload)
        sensitivity = await client.post(
            "/api/v1/opportunity/sensitivity", json={**payload, "perturbation": "0.10"}
        )
        exported = await client.post(
            "/api/v1/opportunity/export", json={**payload, "perturbation": "0.10"}
        )

    assert indicators.status_code == 200
    assert regions.status_code == 200
    assert compare.status_code == 200
    assert score.status_code == 200
    assert sensitivity.json()["scenario_count"] == 2
    assert exported.json()["dataset_versions"]["hdi"]["version_id"] == "version-1"


@pytest.mark.asyncio
async def test_api_rejects_invalid_region_count_weight_and_unknown_fields(
    opportunity_app: Any,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=opportunity_app), base_url="http://test"
    ) as client:
        invalid_regions = await client.post(
            "/api/v1/opportunity/score",
            json={
                "region_codes": ["1100"],
                "year": 2025,
                "indicators": [{"code": "hdi", "weight": 100, "direction": "higher"}],
            },
        )
        negative_weight = await client.post(
            "/api/v1/opportunity/score",
            json={
                "region_codes": ["1100", "1200"],
                "year": 2025,
                "indicators": [{"code": "hdi", "weight": -1, "direction": "higher"}],
            },
        )
        extra_field = await client.post(
            "/api/v1/opportunity/compare",
            json={
                "region_codes": ["1100", "1200"],
                "indicator_codes": ["hdi"],
                "year": 2025,
                "secret": "not accepted",
            },
        )

    assert invalid_regions.status_code == 422
    assert negative_weight.status_code == 422
    assert extra_field.status_code == 422


@pytest.mark.asyncio
async def test_export_builds_score_request_without_sensitivity_only_fields() -> None:
    service = ExportHarness()
    request = SensitivityRequest.model_validate(
        {
            "region_codes": ["1100", "1200"],
            "year": 2024,
            "coverage_threshold": "1",
            "perturbation": "0.10",
            "indicators": [{"code": "hdi", "weight": "100", "direction": "higher"}],
        }
    )

    exported = await service.export_report(request)

    assert service.received_score_request is not None
    assert service.received_score_request.model_fields_set == {
        "region_codes",
        "year",
        "coverage_threshold",
        "normalization",
        "indicators",
    }
    assert exported["configuration"]["perturbation"] == "0.10"
