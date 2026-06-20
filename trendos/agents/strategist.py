"""③ Content Strategist AI — lập chiến lược nội dung.

Với mỗi xu hướng (kèm `ResearchBrief`), Claude quyết định: làm những định dạng
nào, đăng kênh nào, góc tiếp cận và tone ra sao → `ContentPlan`. Đây là agent
điều phối: kế hoạch của nó định hướng fan-out sang Copywriter/Image/Video.
"""

from __future__ import annotations

import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.models import ContentFormat, ContentPlan, ContentPlanItem

log = logging.getLogger("trendos.agent.strategist")


class ContentStrategistAgent(BaseAgent):
    name = "content_strategist"

    def is_ready(self, settings) -> bool:
        return bool(settings.anthropic_api_key)

    async def run(self, ctx: PipelineContext) -> None:
        # TODO(impl): cho Claude xem trend + brief, trả về kế hoạch có cấu trúc
        #   (structured outputs) gồm các (format, channel, angle, tone) phù hợp
        #   với từng nền tảng và mức độ "nóng" của xu hướng.
        for trend in ctx.trends:
            plan = ContentPlan(
                trend_id=trend.id,
                items=[
                    # Placeholder: mặc định một post MXH mỗi xu hướng.
                    ContentPlanItem(format=ContentFormat.SOCIAL_POST, channel="facebook"),
                ],
            )
            ctx.plans[trend.id] = plan
        await ctx.repo.save_plans(list(ctx.plans.values()))
        log.info("Lập %d kế hoạch nội dung", len(ctx.plans))
