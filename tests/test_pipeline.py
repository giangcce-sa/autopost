"""Test tầng DETECT — clustering + chấm điểm momentum, không gọi mạng/Claude."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trendos.config import ScoringWeights
from trendos.detection import TrendScorer, cluster_signals, rank_and_filter
from trendos.models import Signal, SourceName, Trend
from trendos.storage import InMemoryRepository


def _signal(
    source: SourceName,
    ext_id: str,
    title: str,
    score: float = 1.0,
    captured_at: datetime | None = None,
) -> Signal:
    kw = {"captured_at": captured_at} if captured_at else {}
    return Signal(
        source=source, external_id=ext_id, title=title, metrics={"score": score}, **kw
    )


# ─── Clustering ──────────────────────────────────────────────────────────


def test_similar_titles_cluster_across_sources():
    """Cùng chủ đề trên 2 nguồn khác nhau → gộp thành 1 xu hướng đa nguồn."""
    signals = [
        _signal(SourceName.HACKER_NEWS, "1", "OpenAI launches new agent framework"),
        _signal(SourceName.REDDIT, "2", "New agent framework from OpenAI is impressive"),
    ]
    trends = cluster_signals(signals)
    assert len(trends) == 1
    assert trends[0].sources == {SourceName.HACKER_NEWS, SourceName.REDDIT}


def test_unrelated_titles_stay_separate():
    signals = [
        _signal(SourceName.HACKER_NEWS, "1", "Rust compiler performance gains"),
        _signal(SourceName.HACKER_NEWS, "2", "New coffee brewing technique"),
    ]
    assert len(cluster_signals(signals)) == 2


# ─── Scoring ───────────────────────────────────────────────────────────────


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
    assert multi.score > single.score


def test_velocity_positive_when_metric_grows_over_time():
    """Tín hiệu có metric tăng theo thời gian → velocity > 0 (momentum dương)."""
    scorer = TrendScorer(ScoringWeights())
    t0 = datetime.now(UTC) - timedelta(hours=2)
    t1 = datetime.now(UTC) - timedelta(hours=1)
    old = _signal(SourceName.HACKER_NEWS, "1", "x", score=10, captured_at=t0)
    new = _signal(SourceName.HACKER_NEWS, "1", "x", score=100, captured_at=t1)
    trend = Trend(label="x", signals=[new])
    scorer.score(trend, history={new.dedup_key: [old, new]})
    assert trend.momentum > 0  # velocity đã được tính từ chuỗi thời gian


def test_novelty_decays_with_age():
    """Xu hướng cũ có novelty thấp hơn xu hướng vừa xuất hiện."""
    scorer = TrendScorer(ScoringWeights())
    fresh = Trend(label="x", signals=[], first_seen=datetime.now(UTC))
    old = Trend(label="y", signals=[], first_seen=datetime.now(UTC) - timedelta(hours=48))
    scorer.score(fresh)
    scorer.score(old)
    assert fresh.novelty > old.novelty


def test_ranker_filters_and_limits():
    trends = [Trend(label=f"t{i}", score=i / 10) for i in range(10)]
    out = rank_and_filter(trends, top_n=3, min_score=0.5)
    assert len(out) == 3
    assert [t.score for t in out] == [0.9, 0.8, 0.7]


# ─── Storage ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_in_memory_repo_keeps_signal_history():
    repo = InMemoryRepository()
    s1 = _signal(SourceName.HACKER_NEWS, "1", "x", score=10)
    s2 = _signal(SourceName.HACKER_NEWS, "1", "x", score=20)  # cùng dedup_key
    await repo.save_signals([s1])
    await repo.save_signals([s2])
    history = await repo.get_signal_history([s1.dedup_key])
    assert len(history[s1.dedup_key]) == 2  # giữ chuỗi thời gian cho scorer
