"""Routes cho nội dung đã sinh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from trendos.api.deps import get_orchestrator, require_api_key
from trendos.models import (
    ContentApprovalStatus,
    ContentFormat,
    ContentPiece,
    MediaAsset,
    Publication,
)
from trendos.pipeline import Orchestrator

router = APIRouter(tags=["content"])


@router.get("/content", response_model=list[ContentPiece])
async def list_content(
    trend_id: str | None = None,
    format: ContentFormat | None = None,
    approval_status: ContentApprovalStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Nội dung đã sinh, lọc tuỳ chọn theo xu hướng và/hoặc định dạng."""
    return await orch.repo.list_content(
        trend_id=trend_id,
        fmt=format,
        approval_status=approval_status,
        limit=limit,
        offset=offset,
    )


@router.get("/content/{content_id}", response_model=ContentPiece)
async def get_content(
    content_id: str,
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Chi tiết một mẩu nội dung."""
    piece = await orch.repo.get_content(content_id)
    if piece is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return piece


@router.post(
    "/content/{content_id}/approve",
    response_model=ContentPiece,
    dependencies=[Depends(require_api_key)],
)
async def approve_content(
    content_id: str,
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Duyệt nội dung để sẵn sàng publish."""
    piece = await orch.repo.update_content_approval(content_id, ContentApprovalStatus.APPROVED)
    if piece is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return piece


@router.post(
    "/content/{content_id}/reject",
    response_model=ContentPiece,
    dependencies=[Depends(require_api_key)],
)
async def reject_content(
    content_id: str,
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Từ chối nội dung, không đưa vào publish thật."""
    piece = await orch.repo.update_content_approval(content_id, ContentApprovalStatus.REJECTED)
    if piece is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return piece


@router.get("/content/{content_id}/assets", response_model=list[MediaAsset])
async def list_content_assets(
    content_id: str,
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Media asset gắn với một mẩu nội dung."""
    return await orch.repo.list_assets(content_id=content_id)


@router.get("/publications", response_model=list[Publication])
async def list_publications(
    content_id: str | None = None,
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Danh sách publication, có thể lọc theo content_id."""
    return await orch.repo.list_publications(content_id=content_id)
