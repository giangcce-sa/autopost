"""③ Content Strategist AI — lập chiến lược nội dung.

Với mỗi xu hướng (kèm `ResearchBrief`), Claude quyết định nên làm những định
dạng nào, đăng kênh nào, góc và tone ra sao → `ContentPlan`. Kế hoạch này định
hướng fan-out sang Copywriter/Image/Video.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.generation.claude_client import ClaudeClient
from trendos.models import ContentFormat, ContentPlan, ContentPlanItem, Trend

log = logging.getLogger("trendos.agent.strategist")

_VALID_FORMATS = {f.value for f in ContentFormat}

_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": sorted(_VALID_FORMATS)},
                    "channel": {"type": "string"},
                    "angle": {"type": "string"},
                    "tone": {"type": "string"},
                },
                "required": ["format", "channel", "angle", "tone"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

_SYSTEM = (
    "Bạn là giám đốc nội dung. Dựa trên xu hướng và hồ sơ nghiên cứu, lập kế "
    "hoạch nội dung đa định dạng phù hợp từng nền tảng. Trả về đúng JSON theo schema."
)


class ContentStrategistAgent(BaseAgent):
    name = "content_strategist"

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self._client = client

    def is_ready(self, settings) -> bool:
        return bool(settings.anthropic_api_key) or self._client is not None

    async def run(self, ctx: PipelineContext) -> None:
        client = self._client or ClaudeClient(ctx.settings)

        async def _plan(trend: Trend) -> ContentPlan:
            brief = ctx.briefs.get(trend.id)
            brief_txt = ""
            if brief:
                brief_txt = (
                    f"Tóm tắt: {brief.summary}\n"
                    f"Góc gợi ý: {', '.join(brief.angles)}\n"
                )
            prompt = (
                f"Xu hướng: {trend.label}\n"
                f"Từ khoá: {', '.join(trend.keywords)}\n"
                f"{brief_txt}\n"
                f"Định dạng hỗ trợ: {', '.join(sorted(_VALID_FORMATS))}.\n"
                "Lập kế hoạch nội dung: chọn định dạng nào, kênh đăng, góc tiếp cận và tone."
            )
            data = await client.complete_json(prompt, schema=_PLAN_SCHEMA, system=_SYSTEM)
            items = [
                ContentPlanItem(
                    format=ContentFormat(it["format"]),
                    channel=it.get("channel", ""),
                    angle=it.get("angle", ""),
                    tone=it.get("tone", ""),
                )
                for it in data.get("items", [])
                if it.get("format") in _VALID_FORMATS
            ]
            return ContentPlan(trend_id=trend.id, items=items)

        plans = await asyncio.gather(*(_plan(t) for t in ctx.trends))
        for plan in plans:
            ctx.plans[plan.trend_id] = plan
        await ctx.repo.save_plans(plans)
        log.info("Lập %d kế hoạch nội dung", len(plans))
