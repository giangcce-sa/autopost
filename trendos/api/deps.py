"""Dependency injection cho API — orchestrator & repository dùng chung.

Giữ một orchestrator singleton để API và các lần chạy pipeline chia sẻ cùng
một repository (cùng dữ liệu). Khi chuyển sang storage bền (SQLite), singleton
này không còn giữ state trong RAM nữa nhưng cấu trúc vẫn nguyên.
"""

from __future__ import annotations

from functools import lru_cache
from secrets import compare_digest

from fastapi import Header, HTTPException, status

from trendos.pipeline import Orchestrator


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()


async def require_api_key(
    x_trendos_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Optional API-key auth.

    If TRENDOS_API_KEY/API_KEY is empty, auth is disabled for local development.
    Otherwise callers must send X-TrendOS-Key or Authorization: Bearer <key>.
    """
    key = get_orchestrator().settings.api_key
    if not key:
        return
    candidate = x_trendos_key
    if candidate is None and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization.split(" ", 1)[1]
    if candidate is None or not compare_digest(candidate, key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing TrendOS API key",
        )
