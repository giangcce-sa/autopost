"""Lớp trừu tượng lưu trữ.

Pipeline chỉ phụ thuộc vào interface `Repository`, nên có thể đổi backend
(SQLite → Postgres → ClickHouse) mà không sửa logic nghiệp vụ.

Quan trọng: `get_signal_history()` cung cấp dữ liệu CHUỖI THỜI GIAN cho scorer
tính velocity/acceleration (xem ARCHITECTURE.md §4.2, §6).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from trendos.models import (
    ContentFormat,
    ContentPiece,
    ContentPlan,
    MediaAsset,
    PerformanceReport,
    Publication,
    ResearchBrief,
    Signal,
    Trend,
)


class Repository(ABC):
    @abstractmethod
    async def save_signals(self, signals: list[Signal]) -> None:
        """Lưu các tín hiệu mới (bồi đắp lịch sử metric theo dedup_key + captured_at)."""

    @abstractmethod
    async def get_signal_history(self, dedup_keys: list[str]) -> dict[str, list[Signal]]:
        """Trả về các lần quan sát trước (cũ → mới) cho mỗi dedup_key, phục vụ scorer."""

    @abstractmethod
    async def save_trends(self, trends: list[Trend]) -> None: ...

    @abstractmethod
    async def list_trends(self, *, limit: int = 50) -> list[Trend]: ...

    @abstractmethod
    async def get_trend(self, trend_id: str) -> Trend | None: ...

    @abstractmethod
    async def save_content(self, pieces: list[ContentPiece]) -> None: ...

    @abstractmethod
    async def list_content(
        self, *, trend_id: str | None = None, fmt: ContentFormat | None = None
    ) -> list[ContentPiece]: ...

    # ─── Artifact của dây chuyền 9 agent ─────────────────────────────────
    @abstractmethod
    async def save_briefs(self, briefs: list[ResearchBrief]) -> None: ...

    @abstractmethod
    async def save_plans(self, plans: list[ContentPlan]) -> None: ...

    @abstractmethod
    async def save_assets(self, assets: list[MediaAsset]) -> None: ...

    @abstractmethod
    async def save_publications(self, publications: list[Publication]) -> None: ...

    @abstractmethod
    async def save_reports(self, reports: list[PerformanceReport]) -> None: ...


class InMemoryRepository(Repository):
    """Backend lưu trong RAM — dùng cho dev/test và chế độ --dry-run.

    Triển khai bền (SQLite) sẽ là một lớp `SqliteRepository(Repository)` riêng.
    """

    def __init__(self) -> None:
        self._signals: dict[str, list[Signal]] = {}  # dedup_key → lịch sử
        self._trends: dict[str, Trend] = {}
        self._content: list[ContentPiece] = []
        self._briefs: list[ResearchBrief] = []
        self._plans: list[ContentPlan] = []
        self._assets: list[MediaAsset] = []
        self._publications: list[Publication] = []
        self._reports: list[PerformanceReport] = []

    async def save_signals(self, signals: list[Signal]) -> None:
        for sig in signals:
            self._signals.setdefault(sig.dedup_key, []).append(sig)

    async def get_signal_history(self, dedup_keys: list[str]) -> dict[str, list[Signal]]:
        return {k: list(self._signals.get(k, [])) for k in dedup_keys}

    async def save_trends(self, trends: list[Trend]) -> None:
        for t in trends:
            self._trends[t.id] = t

    async def list_trends(self, *, limit: int = 50) -> list[Trend]:
        ordered = sorted(self._trends.values(), key=lambda t: t.score, reverse=True)
        return ordered[:limit]

    async def get_trend(self, trend_id: str) -> Trend | None:
        return self._trends.get(trend_id)

    async def save_content(self, pieces: list[ContentPiece]) -> None:
        self._content.extend(pieces)

    async def list_content(
        self, *, trend_id: str | None = None, fmt: ContentFormat | None = None
    ) -> list[ContentPiece]:
        out = self._content
        if trend_id is not None:
            out = [c for c in out if c.trend_id == trend_id]
        if fmt is not None:
            out = [c for c in out if c.format == fmt]
        return list(out)

    async def save_briefs(self, briefs: list[ResearchBrief]) -> None:
        self._briefs.extend(briefs)

    async def save_plans(self, plans: list[ContentPlan]) -> None:
        self._plans.extend(plans)

    async def save_assets(self, assets: list[MediaAsset]) -> None:
        self._assets.extend(assets)

    async def save_publications(self, publications: list[Publication]) -> None:
        self._publications.extend(publications)

    async def save_reports(self, reports: list[PerformanceReport]) -> None:
        self._reports.extend(reports)
