"""Collector TikTok — KHÓ NHẤT, không có API công khai ổn định.

Lựa chọn: API bên thứ ba (trả phí) hoặc thư viện unofficial (dễ vỡ).
Để cuối cùng trong lộ trình triển khai.
"""

from __future__ import annotations

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName


class TikTokCollector(BaseCollector):
    source = SourceName.TIKTOK

    def is_configured(self) -> bool:
        # Chưa có nguồn truy cập ổn định → coi như chưa cấu hình cho tới khi
        # chọn được provider. Orchestrator sẽ bỏ qua một cách an toàn.
        return False

    async def collect(self) -> list[Signal]:
        # TODO(impl): tích hợp provider đã chọn (vd. API thương mại).
        #   metric: play_count, digg_count (likes), share_count, comment_count.
        return []
