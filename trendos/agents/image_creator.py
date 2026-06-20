"""⑤ Image Creator AI — tạo hình ảnh cho nội dung.

Claude không sinh ảnh → agent bọc một `ImageProvider` (text-to-image). Với mỗi
mẩu nội dung dạng post/blog, sinh một `MediaAsset` loại ảnh.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.agents.providers import ImageProvider, ProviderNotConfigured
from trendos.models import AssetType, ContentFormat, ContentPiece, MediaAsset

log = logging.getLogger("trendos.agent.image_creator")

# Định dạng nội dung cần ảnh đi kèm.
_NEEDS_IMAGE = {ContentFormat.SOCIAL_POST, ContentFormat.BLOG_ARTICLE}


class ImageCreatorAgent(BaseAgent):
    name = "image_creator"

    def __init__(self, provider: ImageProvider | None = None) -> None:
        self._provider = provider

    def is_ready(self, settings) -> bool:
        # Cần khoá provider ảnh; chưa có → bỏ qua an toàn ở orchestrator.
        return bool(settings.image_provider_key)

    def _resolve(self) -> ImageProvider:
        if self._provider is not None:
            return self._provider
        # TODO(impl): dựng adapter thật từ settings (vd. Stability/DALL·E).
        raise ProviderNotConfigured("Chưa có adapter ImageProvider — hãy tiêm provider")

    async def run(self, ctx: PipelineContext) -> None:
        provider = self._resolve()
        targets = [c for c in ctx.content if c.format in _NEEDS_IMAGE]

        async def _make(piece: ContentPiece) -> MediaAsset:
            prompt = f"Ảnh minh hoạ cho nội dung: {piece.title}"
            uri = await provider.generate(prompt)
            return MediaAsset(content_id=piece.id, type=AssetType.IMAGE, uri=uri)

        assets = await asyncio.gather(*(_make(p) for p in targets))
        ctx.assets.extend(assets)
        await ctx.repo.save_assets(list(assets))
        log.info("Tạo %d ảnh", len(assets))
