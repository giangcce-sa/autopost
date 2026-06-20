"""Collector YouTube — cần API key (Data API v3).

Lấy video phổ biến (videos.list chart=mostPopular) theo vùng/danh mục.
"""

from __future__ import annotations

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName


class YouTubeCollector(BaseCollector):
    source = SourceName.YOUTUBE

    def is_configured(self) -> bool:
        return bool(self.settings.youtube_api_key)

    async def collect(self) -> list[Signal]:
        # TODO(impl): videos.list(part="snippet,statistics", chart="mostPopular",
        #   regionCode=..., maxResults=50). metric: viewCount, likeCount, commentCount.
        #   keyword từ snippet.tags + title.
        return []
