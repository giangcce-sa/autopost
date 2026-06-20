"""Cấu hình tập trung — đọc từ biến môi trường / file .env.

Mọi tham số có thể tinh chỉnh (trọng số chấm điểm, model Claude, ngưỡng lọc...)
sống ở đây để không rải rác hằng số khắp codebase.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScoringWeights(BaseSettings):
    """Trọng số tổ hợp điểm xu hướng. Xem detection/scorer.py và ARCHITECTURE.md §4.2.

    Nhấn mạnh `acceleration` và `novelty` chính là cách phát hiện "trước đám đông";
    `saturation` phạt những chủ đề đã bão hoà mà ai cũng thấy.
    """

    model_config = SettingsConfigDict(env_prefix="TRENDOS_WEIGHT_")

    velocity: float = 1.0
    acceleration: float = 2.0   # tín hiệu sớm — trọng số cao nhất
    novelty: float = 1.5
    cross_source: float = 1.0
    saturation: float = 1.0     # trừ điểm


class Settings(BaseSettings):
    """Cấu hình toàn cục của TrendOS."""

    model_config = SettingsConfigDict(
        env_prefix="TRENDOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Claude / sinh nội dung ──────────────────────────────────────────
    anthropic_api_key: str = Field("", validation_alias="ANTHROPIC_API_KEY")
    claude_model: str = "claude-opus-4-8"
    claude_max_tokens: int = 4096

    # ─── Detection ───────────────────────────────────────────────────────
    top_n_trends: int = 10        # số xu hướng đưa sang giai đoạn sinh nội dung
    min_trend_score: float = 0.3  # ngưỡng lọc điểm tối thiểu

    # ─── Storage ─────────────────────────────────────────────────────────
    database_url: str = "sqlite:///trendos.db"

    # ─── Khoá API nguồn dữ liệu (rỗng = collector đó chạy ở chế độ stub) ──
    reddit_client_id: str = Field("", validation_alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str = Field("", validation_alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field("trendos/0.1", validation_alias="REDDIT_USER_AGENT")
    twitter_bearer_token: str = Field("", validation_alias="TWITTER_BEARER_TOKEN")
    youtube_api_key: str = Field("", validation_alias="YOUTUBE_API_KEY")
    github_token: str = Field("", validation_alias="GITHUB_TOKEN")

    # ─── Khoá provider cho agent media & đăng bài (rỗng = agent đó bị bỏ qua) ─
    image_provider_key: str = Field("", validation_alias="IMAGE_PROVIDER_KEY")
    video_provider_key: str = Field("", validation_alias="VIDEO_PROVIDER_KEY")
    facebook_token: str = Field("", validation_alias="FACEBOOK_TOKEN")
    tiktok_token: str = Field("", validation_alias="TIKTOK_TOKEN")

    # ─── RSS feeds mặc định (collector RSS) ──────────────────────────────
    rss_feeds: list[str] = Field(
        default_factory=lambda: [
            "https://hnrss.org/frontpage",
            "https://www.theverge.com/rss/index.xml",
        ]
    )

    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)


@lru_cache
def get_settings() -> Settings:
    """Singleton cấu hình (cache để không đọc lại .env mỗi lần gọi)."""
    return Settings()
