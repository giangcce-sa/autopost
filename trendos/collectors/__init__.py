"""Tầng COLLECT — các nguồn dữ liệu.

`ALL_COLLECTORS` là registry để orchestrator khởi tạo toàn bộ collector.
Thêm nguồn mới = viết một lớp `BaseCollector` rồi thêm vào danh sách này.
"""

from __future__ import annotations

from trendos.collectors.base import BaseCollector
from trendos.collectors.github import GitHubCollector
from trendos.collectors.google_trends import GoogleTrendsCollector
from trendos.collectors.hackernews import HackerNewsCollector
from trendos.collectors.reddit import RedditCollector
from trendos.collectors.rss import RSSCollector
from trendos.collectors.tiktok import TikTokCollector
from trendos.collectors.twitter import TwitterCollector
from trendos.collectors.youtube import YouTubeCollector

ALL_COLLECTORS: list[type[BaseCollector]] = [
    HackerNewsCollector,
    RSSCollector,
    GitHubCollector,
    GoogleTrendsCollector,
    RedditCollector,
    TwitterCollector,
    YouTubeCollector,
    TikTokCollector,
]

__all__ = ["BaseCollector", "ALL_COLLECTORS"]
