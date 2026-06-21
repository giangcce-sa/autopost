"""Collector Google Trends — qua `pytrends` (không official, dễ bị rate-limit).

Cung cấp `search_index` theo thời gian — tín hiệu velocity rất giá trị cho scorer.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName
from trendos.text import extract_keywords

log = logging.getLogger("trendos.collector.google_trends")

_TODAY_GEO = {
    "united_states": "US",
    "vietnam": "VN",
}


def trend_to_signal(keyword: str, *, search_index: float = 100.0) -> Signal | None:
    keyword = keyword.strip()
    if not keyword:
        return None
    return Signal(
        source=SourceName.GOOGLE_TRENDS,
        external_id=keyword.lower(),
        title=keyword,
        keywords=extract_keywords(keyword),
        metrics={"search_index": float(search_index)},
    )


class GoogleTrendsCollector(BaseCollector):
    source = SourceName.GOOGLE_TRENDS

    async def collect(self) -> list[Signal]:
        try:
            from pytrends.request import TrendReq  # type: ignore[import-untyped]
        except ImportError:
            log.info("pytrends chưa cài (pip install 'trendos[sources]') — bỏ qua Google Trends")
            return []

        def _fetch() -> list[Signal]:
            pytrends = TrendReq(hl="en-US", tz=360)
            try:
                df = pytrends.trending_searches(pn=self.settings.google_trends_geo)
            except Exception:
                pn = _TODAY_GEO.get(
                    self.settings.google_trends_geo.lower(),
                    self.settings.google_trends_geo.upper(),
                )
                df = pytrends.today_searches(pn=pn)
            keywords = [str(v) for v in df.iloc[:, 0].head(25).tolist()]
            return [sig for kw in keywords if (sig := trend_to_signal(kw)) is not None]

        try:
            return await asyncio.to_thread(_fetch)
        except Exception as exc:
            log.warning("Google Trends lỗi: %s", exc)
            return []
