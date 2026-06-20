"""Collector RSS / News — không cần API key (cài `pip install 'trendos[sources]'`).

Đọc danh sách feed trong `settings.rss_feeds` bằng `feedparser`. feedparser là
sync nên chạy trong thread (`asyncio.to_thread`). Nếu chưa cài feedparser →
log và bỏ qua an toàn.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName
from trendos.text import extract_keywords

log = logging.getLogger("trendos.collector.rss")


def entry_to_signal(entry: Any, feed_url: str) -> Signal | None:
    """Map một entry feed → Signal. Hàm thuần (không I/O) để test được.

    `entry` là object kiểu feedparser (có .get / thuộc tính title, link, id...).
    """
    get = entry.get if hasattr(entry, "get") else lambda k, d=None: getattr(entry, k, d)
    title = get("title")
    if not title:
        return None
    link = get("link")
    summary = get("summary")
    ext_id = get("id") or link or f"{feed_url}:{title}"
    return Signal(
        source=SourceName.RSS,
        external_id=str(ext_id),
        title=title,
        url=link,
        summary=summary,
        keywords=extract_keywords(f"{title} {summary or ''}"),
        # RSS không có lượt xem; recency là proxy — momentum chủ yếu đến từ
        # việc một chủ đề lặp lại qua nhiều feed/lần chạy (cross_source/novelty).
        metrics={},
    )


class RSSCollector(BaseCollector):
    source = SourceName.RSS

    async def collect(self) -> list[Signal]:
        try:
            import feedparser  # lazy: chỉ cần khi thật sự chạy RSS
        except ImportError:
            log.info("feedparser chưa cài (pip install 'trendos[sources]') — bỏ qua RSS")
            return []

        async def _parse(url: str) -> list[Signal]:
            try:
                feed = await asyncio.to_thread(feedparser.parse, url)
            except Exception as exc:
                log.warning("RSS feed %s lỗi: %s", url, exc)
                return []
            out = [s for e in feed.entries if (s := entry_to_signal(e, url)) is not None]
            return out

        batches = await asyncio.gather(*(_parse(u) for u in self.settings.rss_feeds))
        return [sig for batch in batches for sig in batch]
