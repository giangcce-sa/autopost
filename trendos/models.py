"""Domain models — ba kiểu dữ liệu xương sống nối ba giai đoạn của pipeline.

    Signal  (COLLECT)  ──►  Trend  (DETECT)  ──►  ContentPiece  (GENERATE)

Mỗi giai đoạn nhận/đưa các model này, nhờ vậy các giai đoạn được tách rời và
test độc lập. Xem ARCHITECTURE.md §2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


class SourceName(StrEnum):
    """Định danh các nguồn dữ liệu được hỗ trợ."""

    HACKER_NEWS = "hacker_news"
    RSS = "rss"
    GITHUB = "github"
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class ContentFormat(StrEnum):
    """Các định dạng nội dung TrendOS có thể sinh ra."""

    SOCIAL_POST = "social_post"
    BLOG_ARTICLE = "blog_article"
    VIDEO_SCRIPT = "video_script"


class AssetType(StrEnum):
    """Loại tài nguyên media do Image/Video agent tạo ra."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class PublishStatus(StrEnum):
    """Trạng thái một lần đăng bài (Publisher agent)."""

    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class PipelineRunStatus(StrEnum):
    """Trạng thái một lượt chạy pipeline."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentApprovalStatus(StrEnum):
    """Trạng thái duyệt nội dung trước khi publish thật."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


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
    trend_key: str = Field(
        default="",
        description="Khoá ổn định để nhận diện cùng một xu hướng qua nhiều lần chạy",
    )
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
    approval_status: ContentApprovalStatus = ContentApprovalStatus.DRAFT
    reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class PipelineRun(BaseModel):
    """Một lượt chạy pipeline, dùng cho API/CLI theo dõi trạng thái."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    dry_run: bool = False
    status: PipelineRunStatus = PipelineRunStatus.QUEUED
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary: dict[str, int | float | str | list[dict[str, str | float]]] = Field(
        default_factory=dict
    )
    error: str | None = None
    created_at: datetime = Field(default_factory=_now)


# ─── Vật trung chuyển giữa các agent (dây chuyền 9 agent) ──────────────────
# Mỗi model là output của một agent, làm input cho agent kế tiếp. Xem
# ARCHITECTURE.md §10.


class ResearchBrief(BaseModel):
    """② Research AI: hồ sơ đào sâu một xu hướng (facts, nguồn, góc nhìn)."""

    trend_id: str
    summary: str = ""
    facts: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    angles: list[str] = Field(default_factory=list, description="Các góc khai thác nội dung")
    created_at: datetime = Field(default_factory=_now)


class ContentPlanItem(BaseModel):
    """Một hạng mục nội dung trong kế hoạch: định dạng + kênh + góc + tone."""

    format: ContentFormat
    channel: str = Field(..., description="Nền tảng đích, vd. 'facebook', 'tiktok'")
    angle: str = ""
    tone: str = ""


class ContentPlan(BaseModel):
    """③ Content Strategist AI: chiến lược nội dung cho một xu hướng."""

    trend_id: str
    items: list[ContentPlanItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class MediaAsset(BaseModel):
    """⑤/⑥ Image & Video AI: một tài nguyên media gắn với một mẩu nội dung."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    content_id: str
    type: AssetType
    uri: str = Field(..., description="Đường dẫn/URL tới file media")
    meta: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)


class Publication(BaseModel):
    """⑦ Publisher AI: một lần đăng/lên lịch một mẩu nội dung lên một nền tảng."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    content_id: str
    platform: str
    status: PublishStatus = PublishStatus.SCHEDULED
    scheduled_at: datetime | None = None
    external_url: str | None = None
    created_at: datetime = Field(default_factory=_now)


class PerformanceReport(BaseModel):
    """⑧ Analyst AI: báo cáo hiệu suất sau khi đăng."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    publication_id: str
    metrics: dict[str, float] = Field(default_factory=dict, description="reach, likes, shares...")
    insights: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class LearningUpdate(BaseModel):
    """⑨ Learning AI: đề xuất tinh chỉnh để đóng vòng phản hồi."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    weight_adjustments: dict[str, float] = Field(
        default_factory=dict, description="Điều chỉnh trọng số scorer"
    )
    prompt_notes: list[str] = Field(
        default_factory=list, description="Gợi ý cải thiện prompt cho Copywriter/Strategist"
    )
    created_at: datetime = Field(default_factory=_now)
