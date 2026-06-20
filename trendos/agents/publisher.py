"""⑦ Publisher AI — đăng và lên lịch đa nền tảng.

Đẩy `ContentPiece` (kèm `MediaAsset`) lên các nền tảng theo kênh trong
`ContentPlan`, hoặc lên lịch đăng. Mỗi lần đăng tạo một `Publication`.
"""

from __future__ import annotations

import logging

from trendos.agents.base import BaseAgent, PipelineContext

log = logging.getLogger("trendos.agent.publisher")


class PublisherAgent(BaseAgent):
    name = "publisher"

    def is_ready(self, settings) -> bool:
        # Cần ít nhất một khoá đăng bài của nền tảng nào đó.
        return any(
            [
                settings.facebook_token,
                settings.twitter_bearer_token,
                settings.youtube_api_key,
                settings.tiktok_token,
            ]
        )

    async def run(self, ctx: PipelineContext) -> None:
        # TODO(impl): với mỗi content + kênh đích, gọi API nền tảng (đăng ngay
        #   hoặc đặt lịch), gắn external_url, tạo Publication(status=...).
        #   Lưu ý hành động khó đảo ngược → cân nhắc xác nhận trước khi đăng thật.
        log.info("Publisher: chưa cấu hình nền tảng — bỏ qua")
