"""⑥ Video Producer AI — dựng video ngắn.

Bọc một `VideoProvider` (TTS + ghép cảnh). Với mỗi kịch bản (ContentPiece định
dạng video_script), dựng video từ kịch bản + ảnh đã có → `MediaAsset` loại video.
"""

from __future__ import annotations

import asyncio
import logging
from typing import cast

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.agents.local_providers import LocalVideoProvider
from trendos.agents.providers import ProviderNotConfigured, VideoProvider
from trendos.models import AssetType, ContentFormat, ContentPiece, MediaAsset
from trendos.provider_loader import load_provider

log = logging.getLogger("trendos.agent.video_producer")


class VideoProducerAgent(BaseAgent):
    name = "video_producer"

    def __init__(self, provider: VideoProvider | None = None) -> None:
        self._provider = provider

    def is_ready(self, settings) -> bool:
        return self._provider is not None or bool(settings.video_provider_key)

    def _resolve(self, ctx: PipelineContext) -> VideoProvider:
        if self._provider is not None:
            return self._provider
        if ctx.settings.video_provider_key == "local":
            return LocalVideoProvider(ctx.settings.output_dir)
        if ctx.settings.video_provider_key:
            return cast(VideoProvider, load_provider(ctx.settings.video_provider_key, ctx.settings))
        raise ProviderNotConfigured(
            "Chưa cấu hình VideoProvider. Dùng VIDEO_PROVIDER_KEY=local hoặc import path."
        )

    async def run(self, ctx: PipelineContext) -> None:
        provider = self._resolve(ctx)
        scripts = [c for c in ctx.content if c.format == ContentFormat.VIDEO_SCRIPT]
        image_uris = [a.uri for a in ctx.assets if a.type == AssetType.IMAGE]

        async def _make(piece: ContentPiece) -> MediaAsset:
            uri = await provider.produce(piece.body, image_uris)
            return MediaAsset(content_id=piece.id, type=AssetType.VIDEO, uri=uri)

        assets = await asyncio.gather(*(_make(p) for p in scripts))
        ctx.assets.extend(assets)
        await ctx.repo.save_assets(list(assets))
        log.info("Dựng %d video", len(assets))
