from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request

from app.opportunity.engine import CompatibilityError, OpportunityError
from app.opportunity.schemas import ComparisonRequest, ScoreRequest, SensitivityRequest
from app.opportunity.service import OpportunityService
from app.regional_analytics.engine import AnalyticsError
from app.regional_analytics.schemas import AnalyticsReportRequest, ClusterRequest, SimilarityRequest
from app.regional_analytics.service import RegionalAnalyticsService

router = APIRouter(prefix="/opportunity", tags=["regional-opportunity"])


def _service(request: Request) -> OpportunityService:
    service = getattr(request.app.state, "opportunity_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Opportunity service is unavailable")
    return cast(OpportunityService, service)


async def _execute(operation: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    try:
        result: dict[str, Any] = await operation
        return result
    except CompatibilityError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (OpportunityError, AnalyticsError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _analytics_service(request: Request) -> RegionalAnalyticsService:
    service = getattr(request.app.state, "regional_analytics_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Regional analytics service is unavailable")
    return cast(RegionalAnalyticsService, service)


@router.get("/indicators")
async def indicators(request: Request) -> dict[str, Any]:
    items = await _service(request).indicator_catalog()
    return {"items": items, "count": len(items)}


@router.get("/regions")
async def regions(request: Request) -> dict[str, Any]:
    items = await _service(request).region_catalog()
    return {"items": items, "count": len(items)}


@router.post("/compare")
async def compare(request: Request, payload: ComparisonRequest) -> dict[str, Any]:
    return await _execute(_service(request).compare(payload))


@router.post("/score")
async def score(request: Request, payload: ScoreRequest) -> dict[str, Any]:
    return await _execute(_service(request).score(payload))


@router.post("/sensitivity")
async def sensitivity(request: Request, payload: SensitivityRequest) -> dict[str, Any]:
    return await _execute(_service(request).sensitivity(payload))


@router.post("/export")
async def export_report(request: Request, payload: SensitivityRequest) -> dict[str, Any]:
    return await _execute(_service(request).export_report(payload))


@router.post("/analytics/similarity")
async def similarity(request: Request, payload: SimilarityRequest) -> dict[str, Any]:
    return await _execute(_analytics_service(request).similarity(payload))


@router.post("/analytics/clusters")
async def clusters(request: Request, payload: ClusterRequest) -> dict[str, Any]:
    return await _execute(_analytics_service(request).clusters(payload))


@router.post("/analytics/report")
async def analytics_report(request: Request, payload: AnalyticsReportRequest) -> dict[str, Any]:
    return await _execute(_analytics_service(request).report(payload))


@router.get("/regions/{region_code}")
async def region_detail(request: Request, region_code: str, year: int = 2024) -> dict[str, Any]:
    return await _execute(_analytics_service(request).region_detail(region_code, year))
