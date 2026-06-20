"""⑧ Analyst AI — đo lường hiệu suất sau khi đăng.

Bọc một `AnalyticsProvider` lấy metric của mỗi `Publication` (reach, like,
share...), rút insight đơn giản → `PerformanceReport`. Thường chạy ở lần sau
(có độ trễ dữ liệu), không cùng lượt với đăng bài.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.agents.providers import AnalyticsProvider, ProviderNotConfigured
from trendos.models import PerformanceReport, Publication

log = logging.getLogger("trendos.agent.analyst")


def derive_insights(metrics: dict[str, float]) -> list[str]:
    """Rút insight thô từ metric (heuristic; có thể thay bằng Claude sau)."""
    insights: list[str] = []
    eng = metrics.get("engagement_rate")
    if eng is not None:
        insights.append("Tương tác tốt" if eng >= 0.05 else "Tương tác thấp")
    if metrics.get("shares", 0) > metrics.get("likes", 0):
        insights.append("Lan truyền mạnh (share > like)")
    return insights


class AnalystAgent(BaseAgent):
    name = "analyst"

    def __init__(self, provider: AnalyticsProvider | None = None) -> None:
        self._provider = provider

    def _resolve(self) -> AnalyticsProvider:
        if self._provider is not None:
            return self._provider
        # TODO(impl): dựng adapter thật đọc analytics từng nền tảng.
        raise ProviderNotConfigured("Chưa có adapter AnalyticsProvider — hãy tiêm provider")

    async def run(self, ctx: PipelineContext) -> None:
        if not ctx.publications:
            log.info("Analyst: chưa có bài đăng để phân tích — bỏ qua")
            return
        provider = self._resolve()

        async def _report(pub: Publication) -> PerformanceReport:
            metrics = await provider.fetch(pub)
            return PerformanceReport(
                publication_id=pub.id,
                metrics=metrics,
                insights=derive_insights(metrics),
            )

        reports = await asyncio.gather(*(_report(p) for p in ctx.publications))
        ctx.reports.extend(reports)
        await ctx.repo.save_reports(list(reports))
        log.info("Phân tích %d bài đăng", len(reports))
