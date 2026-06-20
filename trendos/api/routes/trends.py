"""Routes cho xu hướng và kích hoạt pipeline."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from trendos.api.deps import get_orchestrator
from trendos.models import Trend
from trendos.pipeline import Orchestrator

router = APIRouter(tags=["trends"])


@router.get("/trends", response_model=list[Trend])
async def list_trends(limit: int = 50, orch: Orchestrator = Depends(get_orchestrator)):
    """Danh sách xu hướng đã phát hiện, sắp theo điểm giảm dần."""
    return await orch.repo.list_trends(limit=limit)


@router.get("/trends/{trend_id}", response_model=Trend)
async def get_trend(trend_id: str, orch: Orchestrator = Depends(get_orchestrator)):
    """Chi tiết một xu hướng kèm các tín hiệu nguồn."""
    trend = await orch.repo.get_trend(trend_id)
    if trend is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy xu hướng")
    return trend


@router.post("/pipeline/run")
async def run_pipeline(
    background: BackgroundTasks,
    dry_run: bool = False,
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Kích hoạt một lần chạy pipeline ở chế độ nền.

    `dry_run=true` bỏ qua giai đoạn sinh nội dung (không gọi Claude API).
    """
    background.add_task(orch.run, dry_run=dry_run)
    return {"status": "đã lên lịch", "dry_run": dry_run}
