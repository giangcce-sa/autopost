"""Collector Hacker News — nguồn công khai, không cần key.

API Firebase:
  - {API}/topstories.json        → list[item_id]
  - {API}/item/{id}.json         → {title, url, score, descendants, type, ...}
"""

from __future__ import annotations

import asyncio

import httpx

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName
from trendos.text import extract_keywords

_API = "https://hacker-news.firebaseio.com/v0"
_TOP_LIMIT = 30  # số story lấy mỗi lần


def story_to_signal(item: dict) -> Signal | None:
    """Map một item HN thô → Signal. Trả None nếu không phải story hợp lệ.

    Hàm thuần (không I/O) để test được mà không cần mạng.
    """
    if not item or item.get("type") != "story" or not item.get("title"):
        return None
    title = item["title"]
    return Signal(
        source=SourceName.HACKER_NEWS,
        external_id=str(item["id"]),
        title=title,
        url=item.get("url"),
        keywords=extract_keywords(title),
        metrics={
            "score": float(item.get("score", 0)),
            "comments": float(item.get("descendants", 0)),
        },
    )


class HackerNewsCollector(BaseCollector):
    source = SourceName.HACKER_NEWS

    async def collect(self) -> list[Signal]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{_API}/topstories.json")
            resp.raise_for_status()
            story_ids = resp.json()[:_TOP_LIMIT]

            async def _fetch(sid: int) -> dict | None:
                try:
                    r = await client.get(f"{_API}/item/{sid}.json")
                    r.raise_for_status()
                    return r.json()
                except httpx.HTTPError:
                    return None  # bỏ qua item lỗi, không làm hỏng cả mẻ

            items = await asyncio.gather(*(_fetch(sid) for sid in story_ids))

        signals = [sig for item in items if (sig := story_to_signal(item or {})) is not None]
        return signals
