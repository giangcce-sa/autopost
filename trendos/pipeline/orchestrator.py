"""Orchestrator — nhạc trưởng của dây chuyền 9 agent.

Tuần tự gọi từng agent trong `AGENT_PIPELINE`, truyền chung một `PipelineContext`
(blackboard). Mỗi agent được gọi trong khối bắt lỗi để một agent hỏng không làm
sập cả lượt chạy; agent chưa cấu hình (`is_ready()==False`) bị bỏ qua an toàn.

Cả API và CLI đều gọi vào đây — không nhân đôi logic. Logic collect/detect/
generate đã chuyển vào các agent tương ứng (Trend Hunter / Copywriter).
"""

from __future__ import annotations

import logging

from trendos.agents import AGENT_PIPELINE, DRY_RUN_AGENTS, BaseAgent, PipelineContext
from trendos.config import Settings, get_settings
from trendos.storage import InMemoryRepository, Repository

log = logging.getLogger("trendos.pipeline")


class Orchestrator:
    def __init__(self, settings: Settings | None = None, repo: Repository | None = None) -> None:
        self.settings = settings or get_settings()
        self.repo = repo or InMemoryRepository()

    async def run(self, *, dry_run: bool = False) -> dict:
        """Chạy một lượt dây chuyền agent.

        `dry_run=True` chỉ chạy các agent phân tích (Trend Hunter) — không gọi
        Claude/provider.
        """
        ctx = PipelineContext(settings=self.settings, repo=self.repo)
        agent_classes = DRY_RUN_AGENTS if dry_run else AGENT_PIPELINE

        for agent_cls in agent_classes:
            agent: BaseAgent = agent_cls()
            if not agent.is_ready(self.settings):
                log.info("Bỏ qua agent %s (chưa cấu hình)", agent.name)
                continue
            try:
                await agent.run(ctx)
            except Exception as exc:  # cô lập lỗi từng agent
                log.warning("Agent %s lỗi: %s", agent.name, exc)

        return self._summary(ctx)

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
            "top_trends": [
                {"label": t.label, "score": round(t.score, 3)} for t in ctx.trends[:10]
            ],
        }
