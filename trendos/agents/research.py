"""② Research AI — đào sâu mỗi xu hướng.

Với mỗi `Trend`, dùng Claude (structured output) tổng hợp một `ResearchBrief`
gồm tóm tắt, sự thật chính, nguồn gợi ý và các góc khai thác. Brief này nuôi
Content Strategist ở bước sau.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.generation.claude_client import ClaudeClient
from trendos.models import ResearchBrief, Trend

log = logging.getLogger("trendos.agent.research")

_BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "facts": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}},
        "angles": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "facts", "angles"],
    "additionalProperties": False,
}

_SYSTEM = (
    "Bạn là chuyên viên nghiên cứu xu hướng. Tổng hợp ngắn gọn, trung thực, "
    "nêu các góc khai thác nội dung khả thi. Trả về đúng JSON theo schema."
)


class ResearchAgent(BaseAgent):
    name = "research"

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self._client = client

    def is_ready(self, settings) -> bool:
        return bool(settings.anthropic_api_key) or self._client is not None

    async def run(self, ctx: PipelineContext) -> None:
        client = self._client or ClaudeClient(ctx.settings)

        async def _brief(trend: Trend) -> ResearchBrief:
            sources = ", ".join(s.value for s in trend.sources)
            titles = "\n".join(f"- {sig.title}" for sig in trend.signals[:8])
            prompt = (
                f"Xu hướng: {trend.label}\n"
                f"Từ khoá: {', '.join(trend.keywords)}\n"
                f"Nguồn: {sources}\n"
                f"Tín hiệu:\n{titles}\n\n"
                "Hãy nghiên cứu xu hướng này: tóm tắt nó là gì, các sự thật chính, "
                "nguồn nên tham khảo, và 3-5 góc khai thác nội dung."
            )
            # TODO(impl): bật server tool web_search để xác minh facts/nguồn theo
            #   thời gian thực (cần mạng + xử lý pause_turn).
            data = await client.complete_json(prompt, schema=_BRIEF_SCHEMA, system=_SYSTEM)
            return ResearchBrief(
                trend_id=trend.id,
                summary=data.get("summary", ""),
                facts=data.get("facts", []),
                sources=data.get("sources", []),
                angles=data.get("angles", []),
            )

        briefs = await asyncio.gather(*(_brief(t) for t in ctx.trends))
        for brief in briefs:
            ctx.briefs[brief.trend_id] = brief
        await ctx.repo.save_briefs(briefs)
        log.info("Tạo %d hồ sơ nghiên cứu", len(briefs))
