"""⑥ Video Producer AI — dựng video ngắn.

Bọc một `VideoProvider` (TTS + ghép cảnh). Với mỗi kịch bản (ContentPiece định
dạng video_script), dựng video từ kịch bản + ảnh đã có → `MediaAsset` loại video.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.agents.providers import ProviderNotConfigured, VideoProvider
from trendos.models import AssetType, ContentFormat, ContentPiece, MediaAsset

log = logging.getLogger("trendos.agent.video_producer")


class VideoProducerAgent(BaseAgent):
    name = "video_producer"

    def __init__(self, provider: VideoProvider | None = None) -> None:
        self._provider = provider

    def is_ready(self, settings) -> bool:
        return bool(settings.video_provider_key)

    def _resolve(self) -> VideoProvider:
        if self._provider is not None:
            return self._provider
        # TODO(impl): dựng adapter thật (vd. TTS ElevenLabs + ffmpeg/Shotstack).
        raise ProviderNotConfigured("Chưa có adapter VideoProvider — hãy tiêm provider")

    async def run(self, ctx: PipelineContext) -> None:
        provider = self._resolve()
        scripts = [c for c in ctx.content if c.format == ContentFormat.VIDEO_SCRIPT]
        image_uris = [a.uri for a in ctx.assets if a.type == AssetType.IMAGE]

        async def _make(piece: ContentPiece) -> MediaAsset:
            uri = await provider.produce(piece.body, image_uris)
            return MediaAsset(content_id=piece.id, type=AssetType.VIDEO, uri=uri)

        assets = await asyncio.gather(*(_make(p) for p in scripts))
        ctx.assets.extend(assets)
        await ctx.repo.save_assets(list(assets))
        log.info("Dựng %d video", len(assets))
