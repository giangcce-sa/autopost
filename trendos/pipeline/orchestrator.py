"""Orchestrator — nối ba giai đoạn: COLLECT → DETECT → GENERATE.

Đây là logic nghiệp vụ trung tâm; cả API và CLI đều gọi vào đây (không nhân
đôi logic). Mỗi collector được chạy trong khối bắt lỗi để một nguồn hỏng
không làm sập cả lần chạy (ARCHITECTURE.md §3).
"""

from __future__ import annotations

import asyncio
import logging

from trendos.collectors import ALL_COLLECTORS, BaseCollector
from trendos.config import Settings, get_settings
from trendos.detection import TrendScorer, cluster_signals, rank_and_filter
from trendos.generation import ALL_GENERATORS, ClaudeClient
from trendos.models import ContentPiece, Signal, Trend
from trendos.storage import InMemoryRepository, Repository

log = logging.getLogger("trendos.pipeline")


class Orchestrator:
    def __init__(self, settings: Settings | None = None, repo: Repository | None = None) -> None:
        self.settings = settings or get_settings()
        self.repo = repo or InMemoryRepository()
        self.collectors: list[BaseCollector] = [c(self.settings) for c in ALL_COLLECTORS]
        self.scorer = TrendScorer(self.settings.scoring_weights)

    # ─── Giai đoạn 1: COLLECT ────────────────────────────────────────────
    async def collect(self) -> list[Signal]:
        async def _safe(collector: BaseCollector) -> list[Signal]:
            if not collector.is_configured():
                log.info("Bỏ qua %s (chưa cấu hình)", collector.name)
                return []
            try:
                signals = await collector.collect()
                log.info("%s: %d tín hiệu", collector.name, len(signals))
                return signals
            except Exception as exc:  # cô lập lỗi từng nguồn
                log.warning("Collector %s lỗi: %s", collector.name, exc)
                return []

        results = await asyncio.gather(*(_safe(c) for c in self.collectors))
        return [sig for batch in results for sig in batch]

    # ─── Giai đoạn 2: DETECT ─────────────────────────────────────────────
    async def detect(self, signals: list[Signal]) -> list[Trend]:
        await self.repo.save_signals(signals)
        trends = cluster_signals(signals)

        history = await self.repo.get_signal_history(
            [sig.dedup_key for t in trends for sig in t.signals]
        )
        for trend in trends:
            self.scorer.score(trend, history)

        ranked = rank_and_filter(
            trends,
            top_n=self.settings.top_n_trends,
            min_score=self.settings.min_trend_score,
        )
        await self.repo.save_trends(ranked)
        return ranked

    # ─── Giai đoạn 3: GENERATE ───────────────────────────────────────────
    async def generate(self, trends: list[Trend]) -> list[ContentPiece]:
        client = ClaudeClient(self.settings)
        generators = [g(client) for g in ALL_GENERATORS]

        async def _for_trend(trend: Trend) -> list[ContentPiece]:
            pieces = await asyncio.gather(*(g.generate(trend) for g in generators))
            return list(pieces)

        nested = await asyncio.gather(*(_for_trend(t) for t in trends))
        content = [p for batch in nested for p in batch]
        await self.repo.save_content(content)
        return content

    # ─── Chạy toàn bộ pipeline ───────────────────────────────────────────
    async def run(self, *, dry_run: bool = False) -> dict:
        """Một lần chạy đầy đủ. `dry_run=True` bỏ qua giai đoạn GENERATE (không gọi Claude)."""
        signals = await self.collect()
        trends = await self.detect(signals)
        content: list[ContentPiece] = []
        if not dry_run:
            content = await self.generate(trends)
        return {
            "signals": len(signals),
            "trends": len(trends),
            "content": len(content),
            "top_trends": [{"label": t.label, "score": round(t.score, 3)} for t in trends[:10]],
        }
