"""④ Copywriter AI — viết nội dung chữ.

Đọc `ContentPlan` của Content Strategist, với mỗi hạng mục chọn generator phù
hợp ở tầng `generation/` (post MXH / blog / kịch bản video) và sinh
`ContentPiece` bằng Claude.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.generation import ALL_GENERATORS, ClaudeClient
from trendos.models import ContentFormat, ContentPiece, Trend

log = logging.getLogger("trendos.agent.copywriter")


class CopywriterAgent(BaseAgent):
    name = "copywriter"

    def is_ready(self, settings) -> bool:
        return bool(settings.anthropic_api_key)

    async def run(self, ctx: PipelineContext) -> None:
        client = ClaudeClient(ctx.settings)
        # Map định dạng → generator (instance hoá một lần).
        by_format = {g.format: g(client) for g in ALL_GENERATORS}
        trends_by_id: dict[str, Trend] = {t.id: t for t in ctx.trends}

        async def _gen(trend: Trend, fmt: ContentFormat) -> ContentPiece | None:
            generator = by_format.get(fmt)
            if generator is None:
                log.warning("Không có generator cho định dạng %s", fmt)
                return None
            return await generator.generate(trend)

        tasks = []
        for trend_id, plan in ctx.plans.items():
            trend = trends_by_id.get(trend_id)
            if trend is None:
                continue
            for item in plan.items:
                tasks.append(_gen(trend, item.format))

        results = await asyncio.gather(*tasks)
        content = [c for c in results if c is not None]
        ctx.content.extend(content)
        await ctx.repo.save_content(content)
        log.info("Viết %d mẩu nội dung", len(content))
