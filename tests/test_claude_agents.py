"""Test các agent dùng Claude (②③④) với client giả lập — không gọi API thật."""

from __future__ import annotations

import pytest

from trendos.agents.base import PipelineContext
from trendos.agents.copywriter import CopywriterAgent
from trendos.agents.research import ResearchAgent
from trendos.agents.strategist import ContentStrategistAgent
from trendos.config import get_settings
from trendos.generation.claude_client import ClaudeClient
from trendos.models import ContentFormat, ContentPlan, ContentPlanItem, Trend
from trendos.storage import InMemoryRepository
from trendos.text import extract_hashtags


class FakeClaude:
    """Giả lập ClaudeClient: trả giá trị định sẵn, không gọi mạng."""

    def __init__(self, *, json_value=None, text_value: str = "nội dung mẫu") -> None:
        self._json = json_value
        self._text = text_value

    async def complete(self, prompt, *, system=None, max_tokens=None, stream=False) -> str:
        return self._text

    async def complete_json(self, prompt, *, schema, system=None, max_tokens=None):
        return self._json


def _ctx(trend: Trend) -> PipelineContext:
    ctx = PipelineContext(settings=get_settings(), repo=InMemoryRepository())
    ctx.trends = [trend]
    return ctx


@pytest.mark.asyncio
async def test_research_builds_brief_from_claude_json():
    fake = FakeClaude(
        json_value={"summary": "Tóm tắt", "facts": ["f1"], "sources": ["s1"], "angles": ["a1"]}
    )
    trend = Trend(label="AI agents")
    ctx = _ctx(trend)
    await ResearchAgent(client=fake).run(ctx)
    assert ctx.briefs[trend.id].summary == "Tóm tắt"
    assert ctx.briefs[trend.id].angles == ["a1"]


@pytest.mark.asyncio
async def test_strategist_builds_plan_with_valid_formats():
    fake = FakeClaude(
        json_value={
            "items": [
                {"format": "social_post", "channel": "facebook", "angle": "a", "tone": "vui"},
                {"format": "khong_hop_le", "channel": "x", "angle": "", "tone": ""},
            ]
        }
    )
    trend = Trend(label="x")
    ctx = _ctx(trend)
    await ContentStrategistAgent(client=fake).run(ctx)
    items = ctx.plans[trend.id].items
    assert len(items) == 1  # định dạng không hợp lệ bị loại
    assert items[0].format == ContentFormat.SOCIAL_POST
    assert items[0].channel == "facebook"


@pytest.mark.asyncio
async def test_copywriter_generates_content_and_extracts_hashtags():
    fake = FakeClaude(text_value="Hook mạnh!\nNội dung.\nCTA #AI #Trend")
    trend = Trend(label="x")
    ctx = _ctx(trend)
    ctx.plans[trend.id] = ContentPlan(
        trend_id=trend.id,
        items=[ContentPlanItem(format=ContentFormat.SOCIAL_POST, channel="facebook")],
    )
    await CopywriterAgent(client=fake).run(ctx)
    assert len(ctx.content) == 1
    piece = ctx.content[0]
    assert "Hook mạnh" in piece.body
    assert piece.meta["hashtags"] == "#AI #Trend"
    assert piece.meta["channel"] == "facebook"


def test_extract_hashtags_dedups():
    assert extract_hashtags("a #x b #y #x") == ["#x", "#y"]


def test_claude_json_parser_accepts_markdown_wrapped_object():
    text = "```json\n{\"summary\": \"ok\", \"facts\": []}\n```"
    assert ClaudeClient._json_from_text(text)["summary"] == "ok"
