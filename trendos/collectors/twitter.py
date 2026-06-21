"""Collector X (Twitter) — cần bearer token (API trả phí).

Cân nhắc chi phí: API v2 có hạn mức và giá. Triển khai sau khi các nguồn
miễn phí đã chạy ổn.
"""

from __future__ import annotations

import httpx

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName
from trendos.text import extract_keywords

_API = "https://api.twitter.com/2/tweets/search/recent"


def tweet_to_signal(item: dict) -> Signal | None:
    tweet_id = item.get("id")
    text = item.get("text")
    if not tweet_id or not text:
        return None
    metrics = item.get("public_metrics") or {}
    return Signal(
        source=SourceName.TWITTER,
        external_id=str(tweet_id),
        title=str(text).replace("\n", " ")[:160],
        url=f"https://twitter.com/i/web/status/{tweet_id}",
        summary=str(text),
        keywords=extract_keywords(str(text)),
        metrics={
            "likes": float(metrics.get("like_count", 0) or 0),
            "retweets": float(metrics.get("retweet_count", 0) or 0),
            "replies": float(metrics.get("reply_count", 0) or 0),
            "quotes": float(metrics.get("quote_count", 0) or 0),
        },
    )


class TwitterCollector(BaseCollector):
    source = SourceName.TWITTER

    def is_configured(self) -> bool:
        return bool(self.settings.twitter_bearer_token)

    async def collect(self) -> list[Signal]:
        params: dict[str, str | int] = {
            "query": self.settings.twitter_query,
            "max_results": 50,
            "tweet.fields": "public_metrics,created_at,lang",
        }
        headers = {"Authorization": f"Bearer {self.settings.twitter_bearer_token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(_API, params=params, headers=headers)
            resp.raise_for_status()
            items = resp.json().get("data", [])
        return [sig for item in items if (sig := tweet_to_signal(item)) is not None]
