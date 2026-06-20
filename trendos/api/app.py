"""FastAPI app — mặt tiền HTTP của TrendOS.

Chạy: `uvicorn trendos.api.app:app --reload` rồi mở http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI

from trendos import __version__
from trendos.api.routes import content, trends

app = FastAPI(
    title="TrendOS",
    version=__version__,
    description="Hệ điều hành phát hiện xu hướng và sản xuất nội dung tự động.",
)

app.include_router(trends.router)
app.include_router(content.router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": __version__}
