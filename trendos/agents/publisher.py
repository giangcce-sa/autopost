"""⑦ Publisher AI — đăng và lên lịch đa nền tảng.

Bọc một `PublishProvider`. Với mỗi mẩu nội dung, đăng/đặt lịch lên kênh đích
(lấy từ `ContentPiece.meta["channel"]`) kèm media tương ứng → `Publication`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import cast

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.agents.local_providers import LocalPublishProvider
from trendos.agents.providers import ProviderNotConfigured, PublishProvider
from trendos.models import ContentPiece, MediaAsset, Publication, PublishStatus
from trendos.provider_loader import load_provider

log = logging.getLogger("trendos.agent.publisher")


class PublisherAgent(BaseAgent):
    name = "publisher"

    def __init__(self, provider: PublishProvider | None = None) -> None:
        self._provider = provider

    def is_ready(self, settings) -> bool:
        return self._provider is not None or bool(settings.publish_provider_key)

    def _resolve(self, ctx: PipelineContext) -> PublishProvider:
        if self._provider is not None:
            return self._provider
        if ctx.settings.publish_provider_key == "local":
            return LocalPublishProvider(ctx.settings.output_dir)
        if ctx.settings.publish_provider_key:
            return cast(
                PublishProvider,
                load_provider(ctx.settings.publish_provider_key, ctx.settings),
            )
        raise ProviderNotConfigured(
            "Chưa cấu hình PublishProvider. Dùng PUBLISH_PROVIDER_KEY=local hoặc import path."
        )

    async def run(self, ctx: PipelineContext) -> None:
        provider = self._resolve(ctx)
        assets_by_content: dict[str, list[MediaAsset]] = {}
        for a in ctx.assets:
            assets_by_content.setdefault(a.content_id, []).append(a)

        async def _publish(piece: ContentPiece) -> Publication:
            channel = piece.meta.get("channel", "")
            assets = assets_by_content.get(piece.id, [])
            result = await provider.publish(piece, assets, channel)
            return Publication(
                content_id=piece.id,
                platform=result.get("platform", channel),
                status=PublishStatus(result.get("status", PublishStatus.PUBLISHED)),
                external_url=result.get("external_url"),
            )

        pubs = await asyncio.gather(*(_publish(p) for p in ctx.content))
        ctx.publications.extend(pubs)
        await ctx.repo.save_publications(list(pubs))
        log.info("Đăng/đặt lịch %d bài", len(pubs))
