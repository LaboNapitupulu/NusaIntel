from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.regulasilens.service import CorpusService

router = APIRouter(prefix="/regulations", tags=["regulations"])


def _service(request: Request) -> CorpusService:
    service: CorpusService | None = request.app.state.regulation_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Regulation corpus storage is unavailable",
        )
    return service


@router.get("")
async def regulations(
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = await _service(request).list_documents(limit=limit, offset=offset)
    return {"items": items, "count": len(items), "limit": limit, "offset": offset}


@router.get("/{document_id}")
async def regulation_detail(
    request: Request,
    document_id: str,
    section_limit: int = Query(default=200, ge=1, le=500),
    section_offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    item = await _service(request).get_document(
        document_id,
        section_limit=section_limit,
        section_offset=section_offset,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return item


@router.get("/{document_id}/relations")
async def regulation_relations(request: Request, document_id: str) -> dict[str, Any]:
    items = await _service(request).relations(document_id)
    if items is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return {"items": items, "count": len(items)}
