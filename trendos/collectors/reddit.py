"""Collector Reddit — cần API key (PRAW).

Lấy bài 'rising'/'hot' từ các subreddit quan tâm. 'rising' đặc biệt hợp với
sứ mệnh "trước đám đông" vì bắt bài đang lên nhanh — nên được lấy trước.

PRAW là đồng bộ → toàn bộ phần gọi mạng chạy trong thread (`asyncio.to_thread`),
giống cách RSS collector dùng feedparser. Nếu chưa cài `praw` → bỏ qua an toàn.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from trendos.collectors.base import BaseCollector
from trendos.models import Signal, SourceName
from trendos.text import extract_keywords

log = logging.getLogger("trendos.collector.reddit")

_LIMIT_PER_LISTING = 25  # số bài mỗi listing (rising/hot) mỗi subreddit


def post_to_signal(submission: Any) -> Signal | None:
    """Map một submission Reddit → Signal. Hàm thuần (không I/O), test được.

    `submission` là object kiểu PRAW (hoặc bất kỳ object nào có các thuộc tính
    id/title/permalink/score/num_comments/upvote_ratio).
    """
    title = getattr(submission, "title", None)
    sub_id = getattr(submission, "id", None)
    if not title or not sub_id:
        return None
    permalink = getattr(submission, "permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else getattr(submission, "url", None)
    return Signal(
        source=SourceName.REDDIT,
        external_id=str(sub_id),
        title=title,
        url=url,
        keywords=extract_keywords(title),
        metrics={
            "upvotes": float(getattr(submission, "score", 0) or 0),
            "comments": float(getattr(submission, "num_comments", 0) or 0),
            "upvote_ratio": float(getattr(submission, "upvote_ratio", 0.0) or 0.0),
        },
    )


class RedditCollector(BaseCollector):
    source = SourceName.REDDIT

    def is_configured(self) -> bool:
        return bool(self.settings.reddit_client_id and self.settings.reddit_client_secret)

    async def collect(self) -> list[Signal]:
        try:
            import praw  # lazy: chỉ cần khi thật sự chạy Reddit
        except ImportError:
            log.info("praw chưa cài (pip install 'trendos[sources]') — bỏ qua Reddit")
            return []

        def _fetch() -> list[Signal]:
            reddit = praw.Reddit(
                client_id=self.settings.reddit_client_id,
                client_secret=self.settings.reddit_client_secret,
                user_agent=self.settings.reddit_user_agent,
                check_for_async=False,
            )
            reddit.read_only = True
            signals: list[Signal] = []
            for name in self.settings.reddit_subreddits:
                try:
                    subreddit = reddit.subreddit(name)
                    # 'rising' trước (bắt sớm), rồi 'hot' bổ sung.
                    submissions = list(subreddit.rising(limit=_LIMIT_PER_LISTING)) + list(
                        subreddit.hot(limit=_LIMIT_PER_LISTING)
                    )
                except Exception as exc:  # subreddit lỗi không làm hỏng các sub khác
                    log.warning("Subreddit r/%s lỗi: %s", name, exc)
                    continue
                signals.extend(
                    sig for s in submissions if (sig := post_to_signal(s)) is not None
                )
            return signals

        return await asyncio.to_thread(_fetch)
