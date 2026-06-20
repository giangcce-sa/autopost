"""Collector RSS / News — không cần API key.

Dùng `feedparser` đọc danh sách feed trong `settings.rss_feeds`. Nguồn dễ
triển khai thứ hai sau Hacker News.
"""

from __future__ import annotations

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName


class RSSCollector(BaseCollector):
    source = SourceName.RSS

    async def collect(self) -> list[Signal]:
        # TODO(impl): với mỗi url trong self.settings.rss_feeds:
        #   feed = feedparser.parse(url)  (chạy trong thread executor vì feedparser sync)
        #   map mỗi entry → Signal(external_id=entry.id, title=entry.title,
        #                          url=entry.link, summary=entry.summary)
        #   metric gợi ý: độ mới (recency) làm proxy, vì RSS không có lượt xem.
        return []
