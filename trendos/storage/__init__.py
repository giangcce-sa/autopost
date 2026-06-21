"""Tầng STORE — lưu trữ tín hiệu, xu hướng, nội dung.

`get_repository(settings)` chọn backend theo `settings.database_url`:
- `sqlite:///...`  → `SqliteRepository` (bền, lưu lịch sử metric qua các lần chạy)
- `memory://`/khác → `InMemoryRepository` (dev/test, dry-run)
"""

from __future__ import annotations

from trendos.config import Settings
from trendos.storage.repository import InMemoryRepository, Repository
from trendos.storage.sqlite_repository import SqliteRepository

__all__ = ["Repository", "InMemoryRepository", "SqliteRepository", "get_repository"]


def get_repository(settings: Settings) -> Repository:
    """Khởi tạo backend lưu trữ phù hợp với cấu hình."""
    url = settings.database_url
    if url.startswith("sqlite://"):
        # sqlite:///relative.db hoặc sqlite:////abs/path.db
        path = url.removeprefix("sqlite://").lstrip("/") or "trendos.db"
        if url.startswith("sqlite:////"):
            path = "/" + path  # đường dẫn tuyệt đối (4 dấu /)
        return SqliteRepository(path)
    return InMemoryRepository()
