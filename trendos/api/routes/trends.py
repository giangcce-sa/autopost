"""Routes cho xu hướng và kích hoạt pipeline."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from trendos.api.deps import get_orchestrator, require_api_key
from trendos.models import PipelineRun, Trend
from trendos.pipeline import Orchestrator

router = APIRouter(tags=["trends"])


@router.get("/trends", response_model=list[Trend])
async def list_trends(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Danh sách xu hướng đã phát hiện, sắp theo điểm giảm dần."""
    return await orch.repo.list_trends(limit=limit, offset=offset)


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
    _: None = Depends(require_api_key),
):
    """Kích hoạt một lần chạy pipeline ở chế độ nền.

    `dry_run=true` bỏ qua giai đoạn sinh nội dung (không gọi Claude API).
    """
    run = await orch.create_run(dry_run=dry_run)
    background.add_task(orch.run, dry_run=dry_run, run_id=run.id)
    return {"status": "đã lên lịch", "run_id": run.id, "dry_run": dry_run}


@router.get("/runs", response_model=list[PipelineRun])
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    orch: Orchestrator = Depends(get_orchestrator),
):
    """Danh sách lượt chạy pipeline gần nhất."""
    return await orch.repo.list_runs(limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=PipelineRun)
async def get_run(run_id: str, orch: Orchestrator = Depends(get_orchestrator)):
    """Trạng thái/summary một lượt chạy pipeline."""
    run = await orch.repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt chạy")
    return run
