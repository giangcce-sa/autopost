"""SqliteRepository — backend lưu trữ bền bằng `sqlite3` (thư viện chuẩn).

Là drop-in cho `InMemoryRepository`. Giá trị cốt lõi: lưu **lịch sử signal**
theo `(dedup_key, captured_at)` để scorer tính velocity/acceleration qua nhiều
lần chạy (xem ARCHITECTURE.md §4.2, §6) — điều mà InMemoryRepository đánh mất
khi process tắt.

`sqlite3` là đồng bộ → mọi thao tác chạy trong thread (`asyncio.to_thread`) và
được một khoá tuần tự hoá (một connection dùng chung, `check_same_thread=False`).
Không thêm dependency mới (không SQLAlchemy/aiosqlite).

Mỗi model được lưu/đọc bằng JSON của Pydantic (`model_dump_json` /
`model_validate_json`) trong cột `data` → round-trip chính xác mọi trường
(datetime, enum, dict mở) mà không phải ánh xạ từng cột.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

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
from trendos.storage.repository import Repository

_T = TypeVar("_T")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    dedup_key   TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    data        TEXT NOT NULL,
    PRIMARY KEY (dedup_key, captured_at)
);
CREATE INDEX IF NOT EXISTS idx_signals_key ON signals(dedup_key);

CREATE TABLE IF NOT EXISTS trends (
    id    TEXT PRIMARY KEY,
    score REAL NOT NULL DEFAULT 0,
    data  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content (
    id       TEXT PRIMARY KEY,
    trend_id TEXT,
    format   TEXT,
    data     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_artifacts (
    artifact_type TEXT NOT NULL,
    artifact_id   TEXT NOT NULL,
    data          TEXT NOT NULL,
    PRIMARY KEY (artifact_type, artifact_id)
);
"""


class SqliteRepository(Repository):
    """Lưu trữ bền trên một file SQLite (hoặc `:memory:` cho test)."""

    def __init__(self, path: str = "trendos.db") -> None:
        self._path = path
        if path != ":memory:":
            parent = Path(path).expanduser().resolve().parent
            parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ─── Chạy thao tác đồng bộ trong thread, tuần tự hoá bằng lock ─────────
    async def _run(self, fn: Callable[[], _T]) -> _T:
        return await asyncio.to_thread(self._locked, fn)

    def _locked(self, fn: Callable[[], _T]) -> _T:
        with self._lock:
            return fn()

    def _write(self, sql: str, rows: Iterable[tuple]) -> None:
        self._conn.executemany(sql, list(rows))
        self._conn.commit()

    # ─── Signals (chuỗi thời gian — trái tim của scorer) ──────────────────
    async def save_signals(self, signals: list[Signal]) -> None:
        def _op() -> None:
            self._write(
                "INSERT OR REPLACE INTO signals (dedup_key, captured_at, data) VALUES (?, ?, ?)",
                (
                    (s.dedup_key, s.captured_at.isoformat(), s.model_dump_json())
                    for s in signals
                ),
            )

        await self._run(_op)

    async def get_signal_history(self, dedup_keys: list[str]) -> dict[str, list[Signal]]:
        if not dedup_keys:
            return {}

        def _op() -> dict[str, list[Signal]]:
            placeholders = ",".join("?" * len(dedup_keys))
            rows = self._conn.execute(
                f"SELECT dedup_key, data FROM signals WHERE dedup_key IN ({placeholders}) "
                "ORDER BY captured_at ASC",
                dedup_keys,
            ).fetchall()
            out: dict[str, list[Signal]] = {k: [] for k in dedup_keys}
            for row in rows:
                out[row["dedup_key"]].append(Signal.model_validate_json(row["data"]))
            return out

        return await self._run(_op)

    # ─── Trends ───────────────────────────────────────────────────────────
    async def save_trends(self, trends: list[Trend]) -> None:
        def _op() -> None:
            self._write(
                "INSERT OR REPLACE INTO trends (id, score, data) VALUES (?, ?, ?)",
                ((t.id, t.score, t.model_dump_json()) for t in trends),
            )

        await self._run(_op)

    async def list_trends(self, *, limit: int = 50) -> list[Trend]:
        def _op() -> list[Trend]:
            rows = self._conn.execute(
                "SELECT data FROM trends ORDER BY score DESC LIMIT ?", (limit,)
            ).fetchall()
            return [Trend.model_validate_json(r["data"]) for r in rows]

        return await self._run(_op)

    async def get_trend(self, trend_id: str) -> Trend | None:
        def _op() -> Trend | None:
            row = self._conn.execute(
                "SELECT data FROM trends WHERE id = ?", (trend_id,)
            ).fetchone()
            return Trend.model_validate_json(row["data"]) if row else None

        return await self._run(_op)

    # ─── Content ──────────────────────────────────────────────────────────
    async def save_content(self, pieces: list[ContentPiece]) -> None:
        def _op() -> None:
            self._write(
                "INSERT OR REPLACE INTO content (id, trend_id, format, data) VALUES (?, ?, ?, ?)",
                (
                    (c.id, c.trend_id, c.format.value, c.model_dump_json())
                    for c in pieces
                ),
            )

        await self._run(_op)

    async def list_content(
        self, *, trend_id: str | None = None, fmt: ContentFormat | None = None
    ) -> list[ContentPiece]:
        def _op() -> list[ContentPiece]:
            query = "SELECT data FROM content"
            clauses: list[str] = []
            params: list[str] = []
            if trend_id is not None:
                clauses.append("trend_id = ?")
                params.append(trend_id)
            if fmt is not None:
                clauses.append("format = ?")
                params.append(fmt.value)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            rows = self._conn.execute(query, params).fetchall()
            return [ContentPiece.model_validate_json(r["data"]) for r in rows]

        return await self._run(_op)

    # ─── Artifact của dây chuyền 9 agent ──────────────────────────────────
    async def _save_artifacts(
        self, artifact_type: str, items: list[BaseModel], key: Callable[[BaseModel], str]
    ) -> None:
        def _op() -> None:
            self._write(
                "INSERT OR REPLACE INTO agent_artifacts "
                "(artifact_type, artifact_id, data) VALUES (?, ?, ?)",
                ((artifact_type, str(key(it)), it.model_dump_json()) for it in items),
            )

        await self._run(_op)

    async def save_briefs(self, briefs: list[ResearchBrief]) -> None:
        await self._save_artifacts("brief", briefs, lambda b: b.trend_id)

    async def save_plans(self, plans: list[ContentPlan]) -> None:
        await self._save_artifacts("plan", plans, lambda p: p.trend_id)

    async def save_assets(self, assets: list[MediaAsset]) -> None:
        await self._save_artifacts("asset", assets, lambda a: a.id)

    async def save_publications(self, publications: list[Publication]) -> None:
        await self._save_artifacts("publication", publications, lambda p: p.id)

    async def save_reports(self, reports: list[PerformanceReport]) -> None:
        await self._save_artifacts("report", reports, lambda r: r.id)
