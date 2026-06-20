"""⑦ Publisher AI — đăng và lên lịch đa nền tảng.

Bọc một `PublishProvider`. Với mỗi mẩu nội dung, đăng/đặt lịch lên kênh đích
(lấy từ `ContentPiece.meta["channel"]`) kèm media tương ứng → `Publication`.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.agents.providers import ProviderNotConfigured, PublishProvider
from trendos.models import ContentPiece, MediaAsset, Publication, PublishStatus

log = logging.getLogger("trendos.agent.publisher")


class PublisherAgent(BaseAgent):
    name = "publisher"

    def __init__(self, provider: PublishProvider | None = None) -> None:
        self._provider = provider

    def is_ready(self, settings) -> bool:
        return any(
            [
                settings.facebook_token,
                settings.twitter_bearer_token,
                settings.youtube_api_key,
                settings.tiktok_token,
            ]
        )

    def _resolve(self) -> PublishProvider:
        if self._provider is not None:
            return self._provider
        # TODO(impl): dựng adapter thật (Meta Graph API, X API, YouTube, ...).
        # Lưu ý: đăng bài là hành động khó đảo ngược — cân nhắc cổng xác nhận.
        raise ProviderNotConfigured("Chưa có adapter PublishProvider — hãy tiêm provider")

    async def run(self, ctx: PipelineContext) -> None:
        provider = self._resolve()
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
