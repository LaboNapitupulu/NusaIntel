from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.regulasilens.service import CorpusService

router = APIRouter(prefix="/regulations", tags=["regulations"])


class RegulationSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    method: Literal["bm25", "dense", "hybrid", "hybrid_rerank"] = "hybrid_rerank"
    chunker: Literal["structure", "fixed"] = "fixed"
    limit: int = Field(default=10, ge=1, le=50)


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


@router.post("/search")
async def regulation_search(request: Request, payload: RegulationSearchRequest) -> dict[str, Any]:
    try:
        return await _service(request).search(
            payload.query,
            method=payload.method,
            chunker=payload.chunker,
            limit=payload.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/retrieval/manifest")
async def regulation_retrieval_manifest(
    request: Request,
    chunker: Literal["structure", "fixed"] = Query(default="fixed"),
) -> dict[str, Any]:
    return await _service(request).retrieval_manifest(chunker=chunker)


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
