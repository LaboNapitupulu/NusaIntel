from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.control_tower.contracts import DatasetContractSchema
from app.control_tower.service import ControlTowerService

router = APIRouter(tags=["control-tower"])


def _service(request: Request) -> ControlTowerService:
    service: ControlTowerService | None = request.app.state.control_tower_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Control Tower storage is unavailable",
        )
    return service


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["acknowledged", "resolved", "ignored-with-reason"]
    resolution_note: str = Field(min_length=3, max_length=2000)


class ExceptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_code: str = Field(pattern=r"^[a-z][a-z0-9_]{2,127}$")
    reason: str = Field(min_length=3, max_length=2000)
    owner: str = Field(min_length=2, max_length=255)
    expires_at: datetime


@router.post("/contracts/validate")
async def validate_contract(contract: DatasetContractSchema) -> dict[str, Any]:
    return {
        "valid": True,
        "schema_version": contract.schema_version,
        "contract_version": contract.contract_version,
        "dataset_code": contract.dataset_code,
        "rule_count": (
            len(contract.columns)
            + len(contract.uniqueness)
            + len(contract.values)
            + len(contract.custom_checks)
            + 2
        ),
    }


@router.get("/datasets")
async def datasets(
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = await _service(request).list_datasets(limit=limit, offset=offset)
    return {"items": items, "count": len(items), "limit": limit, "offset": offset}


@router.get("/datasets/{dataset_id}")
async def dataset_detail(request: Request, dataset_id: uuid.UUID) -> dict[str, Any]:
    item = await _service(request).get_dataset(dataset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return item


@router.get("/datasets/{dataset_id}/quality")
async def dataset_quality(
    request: Request,
    dataset_id: uuid.UUID,
    severity: Literal["info", "warning", "critical"] | None = None,
    check_status: Literal["passed", "failed", "waived"] | None = Query(
        default=None, alias="status"
    ),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = await _service(request).quality_history(
        dataset_id, severity=severity, status=check_status, limit=limit
    )
    return {"items": items, "count": len(items)}


@router.post("/datasets/{dataset_id}/exceptions", status_code=201)
async def create_quality_exception(
    request: Request, dataset_id: uuid.UUID, payload: ExceptionCreate
) -> dict[str, Any]:
    if payload.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Exception expiry must be in the future")
    item = await _service(request).create_exception(
        dataset_id,
        check_code=payload.check_code,
        reason=payload.reason,
        owner=payload.owner,
        expires_at=payload.expires_at,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return item


@router.get("/pipeline-runs")
async def pipeline_runs(
    request: Request,
    dataset_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = await _service(request).pipeline_runs(dataset_id=dataset_id, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/lineage/{dataset_id}")
async def lineage(request: Request, dataset_id: uuid.UUID) -> dict[str, Any]:
    return await _service(request).lineage(dataset_id)


@router.get("/incidents")
async def incidents(
    request: Request,
    incident_status: Literal["open", "acknowledged", "resolved", "ignored-with-reason"]
    | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = await _service(request).incidents(status=incident_status, limit=limit)
    return {"items": items, "count": len(items)}


@router.patch("/incidents/{incident_id}")
async def update_incident(
    request: Request, incident_id: uuid.UUID, payload: IncidentUpdate
) -> dict[str, Any]:
    item = await _service(request).resolve_incident(
        incident_id, status=payload.status, resolution_note=payload.resolution_note
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return item
