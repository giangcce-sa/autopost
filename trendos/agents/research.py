"""② Research AI — đào sâu mỗi xu hướng.

Với mỗi `Trend` ở `ctx.trends`, dùng Claude (kèm web search/fetch) để thu thập
sự thật, nguồn dẫn, và các góc khai thác → `ResearchBrief`. Brief này nuôi
Content Strategist ở bước sau.
"""

from __future__ import annotations

import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.models import ResearchBrief

log = logging.getLogger("trendos.agent.research")


class ResearchAgent(BaseAgent):
    name = "research"

    def is_ready(self, settings) -> bool:
        return bool(settings.anthropic_api_key)

    async def run(self, ctx: PipelineContext) -> None:
        # TODO(impl): với mỗi trend, gọi Claude (claude-opus-4-8) kèm server tool
        #   web_search/web_fetch để xác minh facts + thu nguồn; parse thành
        #   ResearchBrief(summary, facts, sources, angles). Chạy song song có
        #   giới hạn để kiểm soát chi phí.
        for trend in ctx.trends:
            brief = ResearchBrief(trend_id=trend.id, summary="")  # placeholder rỗng
            ctx.briefs[trend.id] = brief
        await ctx.repo.save_briefs(list(ctx.briefs.values()))
        log.info("Tạo %d hồ sơ nghiên cứu", len(ctx.briefs))
