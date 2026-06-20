"""⑤ Image Creator AI — tạo hình ảnh cho nội dung.

Claude không sinh ảnh → agent này bọc một provider text-to-image (vd. dịch vụ
ảnh bên thứ ba). Với mỗi `ContentPiece` cần hình, tạo `MediaAsset` loại image.
"""

from __future__ import annotations

import logging

from trendos.agents.base import BaseAgent, PipelineContext

log = logging.getLogger("trendos.agent.image_creator")


class ImageCreatorAgent(BaseAgent):
    name = "image_creator"

    def is_ready(self, settings) -> bool:
        # Cần khoá provider ảnh; chưa có → bỏ qua an toàn.
        return bool(settings.image_provider_key)

    async def run(self, ctx: PipelineContext) -> None:
        # TODO(impl): với content cần ảnh, dựng prompt ảnh từ trend+nội dung,
        #   gọi provider text-to-image, lưu file, tạo MediaAsset(type=IMAGE, uri=...).
        log.info("Image Creator: chưa cài provider — bỏ qua")
