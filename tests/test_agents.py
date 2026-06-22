"""Test tầng agent — kiểm interface dây chuyền 9 agent, không gọi mạng/Claude."""

from __future__ import annotations

import pytest

from trendos.agents import AGENT_PIPELINE, PipelineContext
from trendos.agents.base import BaseAgent
from trendos.agents.trend_hunter import TrendHunterAgent
from trendos.config import get_settings
from trendos.models import Signal, SourceName, Trend
from trendos.storage import InMemoryRepository


def test_pipeline_has_nine_agents_in_order():
    assert len(AGENT_PIPELINE) == 9
    names = [a.name for a in AGENT_PIPELINE]
    assert names[0] == "trend_hunter"
    assert names[-1] == "learning"
    assert len(set(names)) == 9  # tên không trùng


def test_every_agent_implements_interface():
    for agent_cls in AGENT_PIPELINE:
        assert issubclass(agent_cls, BaseAgent)
        agent = agent_cls()
        assert isinstance(agent.name, str) and agent.name
        assert hasattr(agent, "run")


def _ctx_with_trends() -> PipelineContext:
    settings = get_settings()
    repo = InMemoryRepository()
    ctx = PipelineContext(settings=settings, repo=repo)
    ctx.trends = [Trend(label="AI agents", signals=[])]
    return ctx


@pytest.mark.asyncio
async def test_trend_hunter_writes_trends_to_context(monkeypatch):
    """Trend Hunter ghi ctx.trends mà không cần mạng (collector trả tín hiệu mẫu)."""

    async def fake_collect(self, ctx):
        return [
            Signal(source=SourceName.HACKER_NEWS, external_id="1", title="x", metrics={"score": 5})
        ]

    monkeypatch.setattr(TrendHunterAgent, "_collect", fake_collect)

    # Hạ ngưỡng về 0 để xu hướng đi qua ranker (scorer hiện là stub, trả điểm 0).
    settings = get_settings().model_copy(update={"min_trend_score": 0.0})
    ctx = PipelineContext(settings=settings, repo=InMemoryRepository())
    await TrendHunterAgent().run(ctx)
    assert len(ctx.trends) >= 1


@pytest.mark.asyncio
async def test_stub_agents_run_without_error_on_empty_context():
    """Các agent stub không được ném lỗi khi context rỗng (chạy được end-to-end)."""
    from trendos.agents.analyst import AnalystAgent
    from trendos.agents.learning import LearningAgent

    ctx = _ctx_with_trends()
    await AnalystAgent().run(ctx)   # chưa có publications → bỏ qua êm
    await LearningAgent().run(ctx)  # chưa có reports → bỏ qua êm
