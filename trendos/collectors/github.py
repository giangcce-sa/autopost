"""Collector GitHub — token tuỳ chọn (chỉ để tăng rate limit).

Phát hiện repo đang được chú ý: trending, hoặc tăng star đột biến.
"""

from __future__ import annotations

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName


class GitHubCollector(BaseCollector):
    source = SourceName.GITHUB

    async def collect(self) -> list[Signal]:
        # TODO(impl): GitHub không có API "trending" chính thức. Hai cách:
        #   1) Search API: q="created:>YYYY-MM-DD" sort=stars  → repo mới nhiều star.
        #   2) Crawl https://github.com/trending (HTML) hoặc dùng dịch vụ proxy.
        #   metric gợi ý: stars, stars_today (đà tăng) → rất hợp với scorer momentum.
        #   Dùng self.settings.github_token cho Authorization nếu có.
        return []
