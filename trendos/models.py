"""Domain models — ba kiểu dữ liệu xương sống nối ba giai đoạn của pipeline.

    Signal  (COLLECT)  ──►  Trend  (DETECT)  ──►  ContentPiece  (GENERATE)

Mỗi giai đoạn nhận/đưa các model này, nhờ vậy các giai đoạn được tách rời và
test độc lập. Xem ARCHITECTURE.md §2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SourceName(str, Enum):
    """Định danh các nguồn dữ liệu được hỗ trợ."""

    HACKER_NEWS = "hacker_news"
    RSS = "rss"
    GITHUB = "github"
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class ContentFormat(str, Enum):
    """Các định dạng nội dung TrendOS có thể sinh ra."""

    SOCIAL_POST = "social_post"
    BLOG_ARTICLE = "blog_article"
    VIDEO_SCRIPT = "video_script"


class Signal(BaseModel):
    """Một quan sát thô từ một nguồn, đã được chuẩn hoá về dạng chung.

    `metrics` là dict mở để mỗi nguồn báo cáo số liệu riêng (views, upvotes,
    search_index, stars...) mà không phá vỡ schema chung. Engine chấm điểm
    đọc các metric này qua thời gian để tính velocity/acceleration.
    """

    source: SourceName
    external_id: str = Field(..., description="ID của item trên nền tảng gốc")
    title: str
    url: str | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=_now)

    @property
    def dedup_key(self) -> str:
        """Khoá nhận dạng một item qua nhiều lần thu thập (cho chuỗi thời gian)."""
        return f"{self.source.value}:{self.external_id}"


class Trend(BaseModel):
    """Một cụm tín hiệu được nhận diện là cùng một xu hướng, kèm điểm số."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    label: str = Field(..., description="Nhãn ngắn gọn cho xu hướng")
    keywords: list[str] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)

    # Kết quả chấm điểm (do detection/scorer.py điền).
    score: float = 0.0
    momentum: float = 0.0  # velocity tổng hợp
    acceleration: float = 0.0
    novelty: float = 0.0

    first_seen: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @property
    def sources(self) -> set[SourceName]:
        """Tập các nguồn độc lập cùng nhắc tới xu hướng (tín hiệu đa nguồn)."""
        return {s.source for s in self.signals}


class ContentPiece(BaseModel):
    """Một mẩu nội dung được sinh ra cho một xu hướng."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    trend_id: str
    format: ContentFormat
    title: str
    body: str
    meta: dict[str, str] = Field(default_factory=dict, description="hashtag, CTA, SEO...")
    created_at: datetime = Field(default_factory=_now)
