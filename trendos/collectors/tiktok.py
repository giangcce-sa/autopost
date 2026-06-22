"""Collector TikTok through a configured provider adapter.

TikTok does not expose a stable public trends API for this use case. The core
collector therefore accepts a provider import path and standardises returned
video/trend dictionaries into `Signal` objects.
"""

from __future__ import annotations

import inspect

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName
from trendos.provider_loader import load_provider
from trendos.text import extract_keywords


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def tiktok_to_signal(item: dict) -> Signal | None:
    external_id = item.get("id") or item.get("aweme_id") or item.get("video_id")
    title = item.get("title") or item.get("desc") or item.get("description")
    if not external_id or not title:
        return None

    stats = item.get("stats") or item.get("statistics") or {}
    hashtags = [
        tag.get("name") if isinstance(tag, dict) else tag
        for tag in item.get("hashtags", [])
        if isinstance(tag, (str, dict))
    ]
    tags = [str(tag) for tag in hashtags if tag]
    text = " ".join([str(title), str(item.get("description") or ""), *tags])
    return Signal(
        source=SourceName.TIKTOK,
        external_id=str(external_id),
        title=str(title),
        url=item.get("url") or item.get("share_url") or item.get("web_url"),
        summary=item.get("description") or item.get("desc") or None,
        keywords=list(dict.fromkeys(tags + extract_keywords(text))),
        metrics={
            "views": _num(stats.get("play_count") or stats.get("views")),
            "likes": _num(stats.get("digg_count") or stats.get("likes")),
            "shares": _num(stats.get("share_count") or stats.get("shares")),
            "comments": _num(stats.get("comment_count") or stats.get("comments")),
        },
    )


class TikTokCollector(BaseCollector):
    source = SourceName.TIKTOK

    def is_configured(self) -> bool:
        return bool(self.settings.tiktok_provider_key)

    async def collect(self) -> list[Signal]:
        provider = load_provider(self.settings.tiktok_provider_key, self.settings)
        collect = getattr(provider, "collect", None)
        if collect is None:
            raise TypeError("TikTok provider must expose a collect() method")
        result = collect()
        items = await result if inspect.isawaitable(result) else result
        signals: list[Signal] = []
        for item in items:
            if isinstance(item, Signal):
                signals.append(item)
                continue
            signal = tiktok_to_signal(item)
            if signal is not None:
                signals.append(signal)
        return signals
