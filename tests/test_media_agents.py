"""Test agent media & phân phối (⑤⑥⑦⑧) với provider giả lập — không gọi dịch vụ thật."""

from __future__ import annotations

import pytest

from trendos.agents.analyst import AnalystAgent, derive_insights
from trendos.agents.base import PipelineContext
from trendos.agents.image_creator import ImageCreatorAgent
from trendos.agents.learning import LearningAgent, summarize
from trendos.agents.publisher import PublisherAgent
from trendos.agents.video_producer import VideoProducerAgent
from trendos.config import get_settings
from trendos.models import (
    AssetType,
    ContentApprovalStatus,
    ContentFormat,
    ContentPiece,
    PerformanceReport,
    Publication,
)
from trendos.storage import InMemoryRepository


class FakeImage:
    async def generate(self, prompt: str) -> str:
        return "https://img.example/x.png"


class FakeVideo:
    async def produce(self, script: str, image_uris: list[str]) -> str:
        return "https://vid.example/x.mp4"


class FakePublish:
    async def publish(self, piece, assets, channel) -> dict:
        return {
            "platform": channel or "facebook",
            "external_url": "https://p/1",
            "status": "published",
        }


class FakeAnalytics:
    async def fetch(self, publication) -> dict:
        return {"likes": 10.0, "shares": 20.0, "engagement_rate": 0.08}


def _ctx() -> PipelineContext:
    return PipelineContext(settings=get_settings(), repo=InMemoryRepository())


def _piece(fmt: ContentFormat, channel: str = "facebook") -> ContentPiece:
    return ContentPiece(trend_id="t1", format=fmt, title="x", body="b", meta={"channel": channel})


@pytest.mark.asyncio
async def test_image_creator_only_for_post_and_blog():
    ctx = _ctx()
    ctx.content = [_piece(ContentFormat.SOCIAL_POST), _piece(ContentFormat.VIDEO_SCRIPT)]
    await ImageCreatorAgent(provider=FakeImage()).run(ctx)
    assert len(ctx.assets) == 1  # chỉ post cần ảnh (video_script không)
    assert ctx.assets[0].type == AssetType.IMAGE


@pytest.mark.asyncio
async def test_video_producer_makes_video_from_script():
    ctx = _ctx()
    ctx.content = [_piece(ContentFormat.VIDEO_SCRIPT)]
    await VideoProducerAgent(provider=FakeVideo()).run(ctx)
    assert any(a.type == AssetType.VIDEO for a in ctx.assets)


@pytest.mark.asyncio
async def test_publisher_creates_publication_per_piece():
    ctx = _ctx()
    ctx.content = [_piece(ContentFormat.SOCIAL_POST, channel="facebook")]
    await PublisherAgent(provider=FakePublish()).run(ctx)
    assert len(ctx.publications) == 1
    assert ctx.publications[0].platform == "facebook"
    assert ctx.publications[0].external_url == "https://p/1"


@pytest.mark.asyncio
async def test_publisher_requires_approval_for_production_provider_key():
    ctx = _ctx()
    ctx.settings = ctx.settings.model_copy(
        update={"publish_provider_key": "my.providers:Publisher"}
    )
    draft = _piece(ContentFormat.SOCIAL_POST, channel="facebook")
    approved = _piece(ContentFormat.SOCIAL_POST, channel="facebook").model_copy(
        update={"approval_status": ContentApprovalStatus.APPROVED}
    )
    ctx.content = [draft, approved]

    await PublisherAgent(provider=FakePublish()).run(ctx)

    assert len(ctx.publications) == 1
    assert ctx.publications[0].content_id == approved.id


@pytest.mark.asyncio
async def test_analyst_builds_report_with_insights():
    ctx = _ctx()
    ctx.publications = [Publication(content_id="c1", platform="facebook")]
    await AnalystAgent(provider=FakeAnalytics()).run(ctx)
    assert len(ctx.reports) == 1
    assert "Lan truyền mạnh (share > like)" in ctx.reports[0].insights


def test_derive_insights_rules():
    assert "Tương tác tốt" in derive_insights({"engagement_rate": 0.1})
    assert "Tương tác thấp" in derive_insights({"engagement_rate": 0.01})


def test_provider_agents_not_ready_without_injected_adapter():
    settings = get_settings()
    assert not ImageCreatorAgent().is_ready(settings)
    assert not VideoProducerAgent().is_ready(settings)
    assert not PublisherAgent().is_ready(settings)
    assert not AnalystAgent().is_ready(settings)
    assert ImageCreatorAgent(provider=FakeImage()).is_ready(settings)
    assert VideoProducerAgent(provider=FakeVideo()).is_ready(settings)
    assert PublisherAgent(provider=FakePublish()).is_ready(settings)
    assert AnalystAgent(provider=FakeAnalytics()).is_ready(settings)


def test_provider_agents_ready_with_import_path_config():
    settings = get_settings().model_copy(
        update={
            "image_provider_key": "trendos.agents.local_providers:image_provider",
            "video_provider_key": "trendos.agents.local_providers:video_provider",
            "publish_provider_key": "trendos.agents.local_providers:publish_provider",
            "analytics_provider_key": "trendos.agents.local_providers:analytics_provider",
        }
    )
    assert ImageCreatorAgent().is_ready(settings)
    assert VideoProducerAgent().is_ready(settings)
    assert PublisherAgent().is_ready(settings)
    assert AnalystAgent().is_ready(settings)


@pytest.mark.asyncio
async def test_local_provider_adapters_create_artifacts(tmp_path):
    settings = get_settings().model_copy(
        update={
            "image_provider_key": "local",
            "video_provider_key": "local",
            "publish_provider_key": "local",
            "analytics_provider_key": "local",
            "output_dir": str(tmp_path),
        }
    )
    ctx = PipelineContext(settings=settings, repo=InMemoryRepository())
    ctx.content = [
        _piece(ContentFormat.SOCIAL_POST, channel="local"),
        _piece(ContentFormat.VIDEO_SCRIPT, channel="local"),
    ]

    await ImageCreatorAgent().run(ctx)
    await VideoProducerAgent().run(ctx)
    await PublisherAgent().run(ctx)
    await AnalystAgent().run(ctx)

    assert len(ctx.assets) == 2
    assert len(ctx.publications) == 2
    assert len(ctx.reports) == 2
    assert all(a.uri for a in ctx.assets)
    assert all(p.external_url for p in ctx.publications)


# ─── ⑨ Learning ────────────────────────────────────────────────────────────


def test_summarize_suggests_weight_bump_when_engagement_low():
    reports = [
        PerformanceReport(publication_id="p1", metrics={"engagement_rate": 0.01}),
        PerformanceReport(publication_id="p2", metrics={"engagement_rate": 0.02}),
    ]
    update = summarize(reports)
    # Engagement thấp → nhấn acceleration & novelty (bắt trend sớm hơn).
    assert update.weight_adjustments.get("acceleration", 0) > 0
    assert update.weight_adjustments.get("novelty", 0) > 0


def test_summarize_empty_reports_is_noop():
    update = summarize([])
    assert update.weight_adjustments == {} and update.prompt_notes == []


@pytest.mark.asyncio
async def test_learning_agent_appends_update():
    ctx = _ctx()
    ctx.reports = [PerformanceReport(publication_id="p1", metrics={"engagement_rate": 0.2})]
    await LearningAgent().run(ctx)
    assert len(ctx.learning) == 1
