"""Collector X (Twitter) — cần bearer token (API trả phí).

Cân nhắc chi phí: API v2 có hạn mức và giá. Triển khai sau khi các nguồn
miễn phí đã chạy ổn.
"""

from __future__ import annotations

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName


class TwitterCollector(BaseCollector):
    source = SourceName.TWITTER

    def is_configured(self) -> bool:
        return bool(self.settings.twitter_bearer_token)

    async def collect(self) -> list[Signal]:
        # TODO(impl): gọi API v2 (recent search / trends) với httpx + Bearer token.
        #   metric: like_count, retweet_count, reply_count (từ public_metrics).
        return []
