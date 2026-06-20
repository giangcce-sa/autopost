"""Routes cho nội dung đã sinh."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from trendos.api.deps import get_orchestrator
from trendos.models import ContentFormat, ContentPiece
from trendos.pipeline import Orchestrator

router = APIRouter(tags=["content"])


@router.get("/content", response_model=list[ContentPiece])
async def list_content(
    trend_id: str | None = None,
    format: ContentFormat | None = None,
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Nội dung đã sinh, lọc tuỳ chọn theo xu hướng và/hoặc định dạng."""
    return await orch.repo.list_content(trend_id=trend_id, fmt=format)
