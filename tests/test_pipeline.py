"""Test khung — kiểm chứng các bất biến kiến trúc, không gọi mạng/Claude."""

from __future__ import annotations

import pytest

from trendos.config import ScoringWeights
from trendos.detection import TrendScorer, cluster_signals, rank_and_filter
from trendos.models import Signal, SourceName, Trend
from trendos.storage import InMemoryRepository


def _signal(source: SourceName, ext_id: str, title: str, score: float = 1.0) -> Signal:
    return Signal(source=source, external_id=ext_id, title=title, metrics={"score": score})


def test_cluster_creates_one_trend_per_signal_placeholder():
    signals = [
        _signal(SourceName.HACKER_NEWS, "1", "AI agents"),
        _signal(SourceName.REDDIT, "2", "Rust 2.0"),
    ]
    trends = cluster_signals(signals)
    assert len(trends) == 2


def test_cross_source_scoring_rewards_multiple_sources():
    scorer = TrendScorer(ScoringWeights())
    multi = Trend(
        label="x",
        signals=[
            _signal(SourceName.HACKER_NEWS, "1", "x"),
            _signal(SourceName.REDDIT, "2", "x"),
            _signal(SourceName.GITHUB, "3", "x"),
        ],
    )
    single = Trend(label="y", signals=[_signal(SourceName.HACKER_NEWS, "9", "y")])
    scorer.score(multi)
    scorer.score(single)
    assert multi.score > single.score  # đa nguồn được thưởng điểm


def test_ranker_filters_and_limits():
    trends = [Trend(label=f"t{i}", score=i / 10) for i in range(10)]
    out = rank_and_filter(trends, top_n=3, min_score=0.5)
    assert len(out) == 3
    assert [t.score for t in out] == [0.9, 0.8, 0.7]  # giảm dần, đã lọc < 0.5


@pytest.mark.asyncio
async def test_in_memory_repo_keeps_signal_history():
    repo = InMemoryRepository()
    s1 = _signal(SourceName.HACKER_NEWS, "1", "x", score=10)
    s2 = _signal(SourceName.HACKER_NEWS, "1", "x", score=20)  # cùng dedup_key
    await repo.save_signals([s1])
    await repo.save_signals([s2])
    history = await repo.get_signal_history([s1.dedup_key])
    assert len(history[s1.dedup_key]) == 2  # giữ chuỗi thời gian cho scorer
