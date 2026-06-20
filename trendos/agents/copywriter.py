"""④ Copywriter AI — viết nội dung chữ.

Đọc `ContentPlan` của Content Strategist, với mỗi hạng mục chọn generator phù
hợp ở tầng `generation/` (post MXH / blog / kịch bản video) và sinh
`ContentPiece` bằng Claude, mang theo góc/tone/kênh từ kế hoạch.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.generation import ALL_GENERATORS, ClaudeClient
from trendos.models import ContentFormat, ContentPiece, ContentPlanItem, Trend

log = logging.getLogger("trendos.agent.copywriter")


class CopywriterAgent(BaseAgent):
    name = "copywriter"

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self._client = client

    def is_ready(self, settings) -> bool:
        return bool(settings.anthropic_api_key) or self._client is not None

    async def run(self, ctx: PipelineContext) -> None:
        client = self._client or ClaudeClient(ctx.settings)
        by_format = {g.format: g(client) for g in ALL_GENERATORS}
        trends_by_id: dict[str, Trend] = {t.id: t for t in ctx.trends}

        async def _gen(trend: Trend, item: ContentPlanItem) -> ContentPiece | None:
            generator = by_format.get(item.format)
            if generator is None:
                log.warning("Không có generator cho định dạng %s", item.format)
                return None
            return await generator.generate(trend, item)

        tasks = []
        for trend_id, plan in ctx.plans.items():
            trend = trends_by_id.get(trend_id)
            if trend is None:
                continue
            for item in plan.items:
                if item.format in ContentFormat:
                    tasks.append(_gen(trend, item))

        results = await asyncio.gather(*tasks)
        content = [c for c in results if c is not None]
        ctx.content.extend(content)
        await ctx.repo.save_content(content)
        log.info("Viết %d mẩu nội dung", len(content))
