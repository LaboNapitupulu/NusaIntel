from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request

from app.opportunity.engine import CompatibilityError, OpportunityError
from app.opportunity.schemas import ComparisonRequest, ScoreRequest, SensitivityRequest
from app.opportunity.service import OpportunityService

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
    except OpportunityError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


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
