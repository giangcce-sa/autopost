"""⑥ Video Producer AI — dựng video ngắn.

Bọc pipeline TTS + ghép cảnh: từ kịch bản (ContentPiece định dạng video_script)
+ ảnh từ Image Creator → video. Tạo `MediaAsset` loại video.
"""

from __future__ import annotations

import logging

from trendos.agents.base import BaseAgent, PipelineContext

log = logging.getLogger("trendos.agent.video_producer")


class VideoProducerAgent(BaseAgent):
    name = "video_producer"

    def is_ready(self, settings) -> bool:
        return bool(settings.video_provider_key)

    async def run(self, ctx: PipelineContext) -> None:
        # TODO(impl): lấy kịch bản video trong ctx.content, sinh voiceover (TTS),
        #   ghép với ảnh/clip, render ra file, tạo MediaAsset(type=VIDEO, uri=...).
        log.info("Video Producer: chưa cài provider — bỏ qua")
