"""Collector YouTube — cần API key (Data API v3).

Lấy video phổ biến (videos.list chart=mostPopular) theo vùng/danh mục.
"""

from __future__ import annotations

import httpx

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName
from trendos.text import extract_keywords

_API = "https://www.googleapis.com/youtube/v3/videos"
_MAX_RESULTS = 25


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def video_to_signal(item: dict) -> Signal | None:
    video_id = item.get("id")
    snippet = item.get("snippet") or {}
    stats = item.get("statistics") or {}
    title = snippet.get("title")
    if not video_id or not title:
        return None
    tags = [t for t in snippet.get("tags", []) if isinstance(t, str)]
    text = " ".join([title, snippet.get("description", ""), *tags])
    return Signal(
        source=SourceName.YOUTUBE,
        external_id=str(video_id),
        title=str(title),
        url=f"https://www.youtube.com/watch?v={video_id}",
        summary=snippet.get("description") or None,
        keywords=list(dict.fromkeys(tags + extract_keywords(text))),
        metrics={
            "views": _num(stats.get("viewCount")),
            "likes": _num(stats.get("likeCount")),
            "comments": _num(stats.get("commentCount")),
        },
    )


class YouTubeCollector(BaseCollector):
    source = SourceName.YOUTUBE

    def is_configured(self) -> bool:
        return bool(self.settings.youtube_api_key)

    async def collect(self) -> list[Signal]:
        params: dict[str, str | int] = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": self.settings.youtube_region_code,
            "maxResults": _MAX_RESULTS,
            "key": self.settings.youtube_api_key,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(_API, params=params)
            resp.raise_for_status()
            items = resp.json().get("items", [])
        return [sig for item in items if (sig := video_to_signal(item)) is not None]
