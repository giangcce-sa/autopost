"""Collector GitHub — token tuỳ chọn (chỉ để tăng rate limit).

Phát hiện repo đang được chú ý qua **Search API**: repo tạo gần đây mà đã có
nhiều star (`created:>... stars:>...`, sắp xếp theo star). GitHub không có API
"trending" chính thức, nhưng truy vấn này bắt đúng repo mới nổi nhanh.

Đà tăng star thật (velocity/acceleration) do scorer tính khi lần chạy sau so
sánh `stars` với lịch sử trong storage. Lần đầu: `novelty` cao bù cho velocity=0.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName
from trendos.text import extract_keywords

_API = "https://api.github.com/search/repositories"
_WINDOW_DAYS = 7     # repo tạo trong N ngày gần đây
_MIN_STARS = 20      # lọc nhiễu
_PER_PAGE = 30


def repo_to_signal(item: dict) -> Signal | None:
    """Map một repo (item Search API) → Signal. Hàm thuần (không I/O), test được.

    Bỏ qua item thiếu `full_name`.
    """
    full_name = item.get("full_name")
    if not full_name:
        return None
    description = item.get("description") or ""
    topics = [t for t in item.get("topics", []) if isinstance(t, str)]
    keywords = list(dict.fromkeys(topics + extract_keywords(f"{full_name} {description}")))
    return Signal(
        source=SourceName.GITHUB,
        external_id=full_name,
        title=full_name,
        url=item.get("html_url"),
        summary=description or None,
        keywords=keywords,
        metrics={
            "stars": float(item.get("stargazers_count", 0)),
            "forks": float(item.get("forks_count", 0)),
            "watchers": float(item.get("watchers_count", 0)),
        },
    )


class GitHubCollector(BaseCollector):
    source = SourceName.GITHUB

    async def collect(self) -> list[Signal]:
        since = (datetime.now(UTC) - timedelta(days=_WINDOW_DAYS)).date().isoformat()
        params = {
            "q": f"created:>{since} stars:>{_MIN_STARS}",
            "sort": "stars",
            "order": "desc",
            "per_page": _PER_PAGE,
        }
        headers = {"Accept": "application/vnd.github+json"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(_API, params=params, headers=headers)
            resp.raise_for_status()
            items = resp.json().get("items", [])

        return [sig for item in items if (sig := repo_to_signal(item)) is not None]
