"""① Trend Hunter AI — săn xu hướng.

Điều phối tầng capability `collectors/` + `detection/`: thu tín hiệu từ mọi
nguồn (cô lập lỗi từng nguồn), gom cụm, chấm điểm momentum, lọc top-N, rồi ghi
`ctx.trends`. Đây là "bộ não phát hiện" — phần hiện thực hoá sứ mệnh
"trước đám đông".
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.collectors import ALL_COLLECTORS, BaseCollector
from trendos.detection import TrendScorer, cluster_signals, rank_and_filter
from trendos.models import Signal

log = logging.getLogger("trendos.agent.trend_hunter")


class TrendHunterAgent(BaseAgent):
    name = "trend_hunter"

    async def run(self, ctx: PipelineContext) -> None:
        signals = await self._collect(ctx)
        await ctx.repo.save_signals(signals)

        trends = cluster_signals(signals)
        history = await ctx.repo.get_signal_history(
            [sig.dedup_key for t in trends for sig in t.signals]
        )
        scorer = TrendScorer(ctx.settings.scoring_weights)
        for trend in trends:
            scorer.score(trend, history)

        ranked = rank_and_filter(
            trends,
            top_n=ctx.settings.top_n_trends,
            min_score=ctx.settings.min_trend_score,
        )
        await ctx.repo.save_trends(ranked)
        ctx.trends = ranked
        log.info("Phát hiện %d xu hướng (từ %d tín hiệu)", len(ranked), len(signals))

    async def _collect(self, ctx: PipelineContext) -> list[Signal]:
        collectors: list[BaseCollector] = [c(ctx.settings) for c in ALL_COLLECTORS]

        async def _safe(collector: BaseCollector) -> list[Signal]:
            if not collector.is_configured():
                log.info("Bỏ qua nguồn %s (chưa cấu hình)", collector.name)
                return []
            try:
                out = await collector.collect()
                log.info("%s: %d tín hiệu", collector.name, len(out))
                return out
            except Exception as exc:  # cô lập lỗi từng nguồn
                log.warning("Nguồn %s lỗi: %s", collector.name, exc)
                return []

        batches = await asyncio.gather(*(_safe(c) for c in collectors))
        return [sig for batch in batches for sig in batch]
