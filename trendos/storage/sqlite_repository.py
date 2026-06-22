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
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from trendos.models import (
    ContentApprovalStatus,
    ContentFormat,
    ContentPiece,
    ContentPlan,
    MediaAsset,
    PerformanceReport,
    PipelineRun,
    Publication,
    ResearchBrief,
    Signal,
    Trend,
)
from trendos.storage.repository import Repository

_T = TypeVar("_T")
_ModelT = TypeVar("_ModelT", bound=BaseModel)
_SCHEMA_VERSION = 3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    dedup_key   TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    data        TEXT NOT NULL,
    PRIMARY KEY (dedup_key, captured_at)
);
CREATE INDEX IF NOT EXISTS idx_signals_key ON signals(dedup_key);

CREATE TABLE IF NOT EXISTS trends (
    id        TEXT PRIMARY KEY,
    trend_key TEXT,
    score     REAL NOT NULL DEFAULT 0,
    data      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trends_key ON trends(trend_key);

CREATE TABLE IF NOT EXISTS content (
    id       TEXT PRIMARY KEY,
    trend_id TEXT,
    format   TEXT,
    approval_status TEXT NOT NULL DEFAULT 'draft',
    data     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id         TEXT PRIMARY KEY,
    status     TEXT NOT NULL,
    created_at TEXT NOT NULL,
    data       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);

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
            self._migrate()
            self._conn.commit()

    def _migrate(self) -> None:
        trend_cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(trends)").fetchall()
        }
        if "trend_key" not in trend_cols:
            self._conn.execute("ALTER TABLE trends ADD COLUMN trend_key TEXT")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_trends_key ON trends(trend_key)")
        content_cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(content)").fetchall()
        }
        if "approval_status" not in content_cols:
            self._conn.execute(
                "ALTER TABLE content ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'draft'"
            )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_approval ON content(approval_status)"
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', ?)",
            (str(_SCHEMA_VERSION),),
        )

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
                "INSERT OR REPLACE INTO trends (id, trend_key, score, data) VALUES (?, ?, ?, ?)",
                ((t.id, t.trend_key, t.score, t.model_dump_json()) for t in trends),
            )

        await self._run(_op)

    async def list_trends(self, *, limit: int = 50, offset: int = 0) -> list[Trend]:
        def _op() -> list[Trend]:
            rows = self._conn.execute(
                "SELECT data FROM trends ORDER BY score DESC LIMIT ? OFFSET ?",
                (limit, offset),
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

    async def get_trend_by_key(self, trend_key: str) -> Trend | None:
        def _op() -> Trend | None:
            row = self._conn.execute(
                "SELECT data FROM trends WHERE trend_key = ? ORDER BY score DESC LIMIT 1",
                (trend_key,),
            ).fetchone()
            return Trend.model_validate_json(row["data"]) if row else None

        return await self._run(_op)

    # ─── Content ──────────────────────────────────────────────────────────
    async def save_content(self, pieces: list[ContentPiece]) -> None:
        def _op() -> None:
            self._write(
                "INSERT OR REPLACE INTO content "
                "(id, trend_id, format, approval_status, data) VALUES (?, ?, ?, ?, ?)",
                (
                    (
                        c.id,
                        c.trend_id,
                        c.format.value,
                        c.approval_status.value,
                        c.model_dump_json(),
                    )
                    for c in pieces
                ),
            )

        await self._run(_op)

    async def get_content(self, content_id: str) -> ContentPiece | None:
        def _op() -> ContentPiece | None:
            row = self._conn.execute(
                "SELECT data FROM content WHERE id = ?", (content_id,)
            ).fetchone()
            return ContentPiece.model_validate_json(row["data"]) if row else None

        return await self._run(_op)

    async def list_content(
        self,
        *,
        trend_id: str | None = None,
        fmt: ContentFormat | None = None,
        approval_status: ContentApprovalStatus | None = None,
        limit: int = 50,
        offset: int = 0,
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
            if approval_status is not None:
                clauses.append("approval_status = ?")
                params.append(approval_status.value)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " LIMIT ? OFFSET ?"
            params.extend([str(limit), str(offset)])
            rows = self._conn.execute(query, params).fetchall()
            return [ContentPiece.model_validate_json(r["data"]) for r in rows]

        return await self._run(_op)

    async def update_content_approval(
        self, content_id: str, status: ContentApprovalStatus
    ) -> ContentPiece | None:
        def _op() -> ContentPiece | None:
            row = self._conn.execute(
                "SELECT data FROM content WHERE id = ?", (content_id,)
            ).fetchone()
            if row is None:
                return None
            piece = ContentPiece.model_validate_json(row["data"]).model_copy(
                update={"approval_status": status, "reviewed_at": datetime.now(UTC)}
            )
            self._conn.execute(
                "UPDATE content SET approval_status = ?, data = ? WHERE id = ?",
                (status.value, piece.model_dump_json(), content_id),
            )
            self._conn.commit()
            return piece

        return await self._run(_op)

    async def save_run(self, run: PipelineRun) -> None:
        def _op() -> None:
            self._write(
                "INSERT OR REPLACE INTO runs (id, status, created_at, data) VALUES (?, ?, ?, ?)",
                [(run.id, run.status.value, run.created_at.isoformat(), run.model_dump_json())],
            )

        await self._run(_op)

    async def get_run(self, run_id: str) -> PipelineRun | None:
        def _op() -> PipelineRun | None:
            row = self._conn.execute("SELECT data FROM runs WHERE id = ?", (run_id,)).fetchone()
            return PipelineRun.model_validate_json(row["data"]) if row else None

        return await self._run(_op)

    async def list_runs(self, *, limit: int = 50, offset: int = 0) -> list[PipelineRun]:
        def _op() -> list[PipelineRun]:
            rows = self._conn.execute(
                "SELECT data FROM runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [PipelineRun.model_validate_json(r["data"]) for r in rows]

        return await self._run(_op)

    async def schema_version(self) -> int:
        def _op() -> int:
            row = self._conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'version'"
            ).fetchone()
            return int(row["value"]) if row else 0

        return await self._run(_op)

    # ─── Artifact của dây chuyền 9 agent ──────────────────────────────────
    async def _save_artifacts(
        self, artifact_type: str, items: Sequence[BaseModel], key: Callable[[Any], str]
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

    async def list_briefs(self) -> list[ResearchBrief]:
        return await self._list_artifacts("brief", ResearchBrief)

    async def save_plans(self, plans: list[ContentPlan]) -> None:
        await self._save_artifacts("plan", plans, lambda p: p.trend_id)

    async def list_plans(self) -> list[ContentPlan]:
        return await self._list_artifacts("plan", ContentPlan)

    async def save_assets(self, assets: list[MediaAsset]) -> None:
        await self._save_artifacts("asset", assets, lambda a: a.id)

    async def list_assets(self, *, content_id: str | None = None) -> list[MediaAsset]:
        assets = await self._list_artifacts("asset", MediaAsset)
        if content_id is not None:
            assets = [a for a in assets if a.content_id == content_id]
        return assets

    async def save_publications(self, publications: list[Publication]) -> None:
        await self._save_artifacts("publication", publications, lambda p: p.id)

    async def list_publications(self, *, content_id: str | None = None) -> list[Publication]:
        publications = await self._list_artifacts("publication", Publication)
        if content_id is not None:
            publications = [p for p in publications if p.content_id == content_id]
        return publications

    async def save_reports(self, reports: list[PerformanceReport]) -> None:
        await self._save_artifacts("report", reports, lambda r: r.id)

    async def list_reports(self, *, publication_id: str | None = None) -> list[PerformanceReport]:
        reports = await self._list_artifacts("report", PerformanceReport)
        if publication_id is not None:
            reports = [r for r in reports if r.publication_id == publication_id]
        return reports

    async def _list_artifacts(self, artifact_type: str, model: type[_ModelT]) -> list[_ModelT]:
        def _op() -> list[_ModelT]:
            rows = self._conn.execute(
                "SELECT data FROM agent_artifacts WHERE artifact_type = ?",
                (artifact_type,),
            ).fetchall()
            return [model.model_validate_json(r["data"]) for r in rows]

        return await self._run(_op)
