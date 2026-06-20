"""Dependency injection cho API — orchestrator & repository dùng chung.

Giữ một orchestrator singleton để API và các lần chạy pipeline chia sẻ cùng
một repository (cùng dữ liệu). Khi chuyển sang storage bền (SQLite), singleton
này không còn giữ state trong RAM nữa nhưng cấu trúc vẫn nguyên.
"""

from __future__ import annotations

from functools import lru_cache

from trendos.pipeline import Orchestrator


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()
