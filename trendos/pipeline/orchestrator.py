"""Orchestrator — nhạc trưởng của dây chuyền 9 agent.

Tuần tự gọi từng agent trong `AGENT_PIPELINE`, truyền chung một `PipelineContext`
(blackboard). Mỗi agent được gọi trong khối bắt lỗi để một agent hỏng không làm
sập cả lượt chạy; agent chưa cấu hình (`is_ready()==False`) bị bỏ qua an toàn.

Cả API và CLI đều gọi vào đây — không nhân đôi logic. Logic collect/detect/
generate đã chuyển vào các agent tương ứng (Trend Hunter / Copywriter).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from trendos.agents import AGENT_PIPELINE, DRY_RUN_AGENTS, BaseAgent, PipelineContext
from trendos.config import Settings, get_settings
from trendos.models import PipelineRun, PipelineRunStatus
from trendos.storage import Repository, get_repository

log = logging.getLogger("trendos.pipeline")


class Orchestrator:
    def __init__(self, settings: Settings | None = None, repo: Repository | None = None) -> None:
        self.settings = settings or get_settings()
        self.repo = repo or get_repository(self.settings)
        self._run_lock = asyncio.Lock()

    async def create_run(self, *, dry_run: bool = False) -> PipelineRun:
        run = PipelineRun(dry_run=dry_run)
        await self.repo.save_run(run)
        return run

    async def run(self, *, dry_run: bool = False, run_id: str | None = None) -> dict:
        """Chạy một lượt dây chuyền agent.

        `dry_run=True` chỉ chạy các agent phân tích (Trend Hunter) — không gọi
        Claude/provider.
        """
        run = await self._start_run(dry_run=dry_run, run_id=run_id)
        if self._run_lock.locked():
            error = "Pipeline already running"
            await self._finish_run(run, status=PipelineRunStatus.FAILED, error=error)
            return {"error": error}

        ctx = PipelineContext(settings=self.settings, repo=self.repo)
        agent_classes = DRY_RUN_AGENTS if dry_run else AGENT_PIPELINE

        try:
            async with self._run_lock:
                for agent_cls in agent_classes:
                    agent: BaseAgent = agent_cls()
                    if not agent.is_ready(self.settings):
                        log.info("Bỏ qua agent %s (chưa cấu hình)", agent.name)
                        continue
                    try:
                        await agent.run(ctx)
                    except Exception as exc:  # cô lập lỗi từng agent
                        log.warning("Agent %s lỗi: %s", agent.name, exc)

                summary = self._summary(ctx)
            await self._finish_run(run, status=PipelineRunStatus.COMPLETED, summary=summary)
            return summary
        except Exception as exc:
            await self._finish_run(run, status=PipelineRunStatus.FAILED, error=str(exc))
            raise

    async def _start_run(self, *, dry_run: bool, run_id: str | None) -> PipelineRun:
        run = await self.repo.get_run(run_id) if run_id else None
        if run is None:
            run = PipelineRun(dry_run=dry_run)
        run.dry_run = dry_run
        run.status = PipelineRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        run.error = None
        await self.repo.save_run(run)
        return run

    async def _finish_run(
        self,
        run: PipelineRun,
        *,
        status: PipelineRunStatus,
        summary: dict | None = None,
        error: str | None = None,
    ) -> None:
        run.status = status
        run.finished_at = datetime.now(UTC)
        if summary is not None:
            run.summary = summary
        run.error = error
        await self.repo.save_run(run)

    @staticmethod
    def _summary(ctx: PipelineContext) -> dict:
        return {
            "trends": len(ctx.trends),
            "briefs": len(ctx.briefs),
            "plans": len(ctx.plans),
            "content": len(ctx.content),
            "assets": len(ctx.assets),
            "publications": len(ctx.publications),
            "reports": len(ctx.reports),
            "learning_updates": len(ctx.learning),
            "top_trends": [
                {"label": t.label, "score": round(t.score, 3)} for t in ctx.trends[:10]
            ],
        }
