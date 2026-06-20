"""Collector Hacker News — KHUYẾN NGHỊ CÀI ĐẶT ĐẦU TIÊN.

HN có API Firebase công khai, không cần key, schema ổn định:
  - https://hacker-news.firebaseio.com/v0/topstories.json  → list[item_id]
  - https://hacker-news.firebaseio.com/v0/item/{id}.json    → {title, url, score, ...}

Đây là nơi tốt nhất để hiện thực hoá pipeline thật vì rào cản gần bằng 0.
"""

from __future__ import annotations

import httpx

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName

_API = "https://hacker-news.firebaseio.com/v0"


class HackerNewsCollector(BaseCollector):
    source = SourceName.HACKER_NEWS

    async def collect(self) -> list[Signal]:
        # TODO(impl): lấy top story ids, fetch chi tiết từng item (giới hạn ~30),
        #             map score/descendants → metrics, trích keyword từ title.
        # Khung tham khảo dưới đây cho thấy hình dạng cài đặt thật.
        signals: list[Signal] = []
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{_API}/topstories.json")
            resp.raise_for_status()
            story_ids = resp.json()[:30]
            for sid in story_ids:
                item = (await client.get(f"{_API}/item/{sid}.json")).json()
                if not item or item.get("type") != "story":
                    continue
                signals.append(
                    Signal(
                        source=self.source,
                        external_id=str(sid),
                        title=item.get("title", ""),
                        url=item.get("url"),
                        metrics={
                            "score": float(item.get("score", 0)),
                            "comments": float(item.get("descendants", 0)),
                        },
                        # TODO(impl): keyword extraction (vd. rake/keybert) thay vì để trống
                    )
                )
        return signals
