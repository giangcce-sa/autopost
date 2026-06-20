"""Collector Reddit — cần API key (PRAW).

Lấy bài 'hot'/'rising' từ các subreddit quan tâm. 'rising' đặc biệt hợp với
sứ mệnh "trước đám đông" vì bắt bài đang lên nhanh.
"""

from __future__ import annotations

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName


class RedditCollector(BaseCollector):
    source = SourceName.REDDIT

    def is_configured(self) -> bool:
        return bool(self.settings.reddit_client_id and self.settings.reddit_client_secret)

    async def collect(self) -> list[Signal]:
        # TODO(impl): khởi tạo praw.Reddit(client_id, client_secret, user_agent),
        #   duyệt subreddit.rising(limit=...) → Signal.
        #   metric: ups, num_comments, upvote_ratio; ưu tiên 'rising' hơn 'hot'.
        #   PRAW sync → chạy trong executor.
        return []
