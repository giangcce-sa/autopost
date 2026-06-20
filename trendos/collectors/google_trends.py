"""Collector Google Trends — qua `pytrends` (không official, dễ bị rate-limit).

Cung cấp `search_index` theo thời gian — tín hiệu velocity rất giá trị cho scorer.
"""

from __future__ import annotations

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName


class GoogleTrendsCollector(BaseCollector):
    source = SourceName.GOOGLE_TRENDS

    async def collect(self) -> list[Signal]:
        # TODO(impl): dùng pytrends — trending_searches() cho từ khoá đang lên,
        #   và interest_over_time() để lấy chuỗi search_index.
        #   pytrends là sync → chạy trong executor. Cẩn thận rate-limit (đặt sleep,
        #   cân nhắc proxy). metric: search_index (0-100).
        return []
