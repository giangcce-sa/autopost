"""FastAPI app — mặt tiền HTTP của TrendOS.

Chạy: `uvicorn trendos.api.app:app --reload` rồi mở http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI

from trendos import __version__
from trendos.api.deps import get_orchestrator
from trendos.api.routes import content, dashboard, trends

app = FastAPI(
    title="TrendOS",
    version=__version__,
    description="Hệ điều hành phát hiện xu hướng và sản xuất nội dung tự động.",
)

app.include_router(trends.router)
app.include_router(content.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/health/details", tags=["system"])
async def health_details() -> dict:
    orch = get_orchestrator()
    db_ok = True
    error = None
    try:
        schema_version = await orch.repo.schema_version()
        await orch.repo.list_runs(limit=1)
    except Exception as exc:
        db_ok = False
        schema_version = 0
        error = str(exc)
    return {
        "status": "ok" if db_ok else "degraded",
        "version": __version__,
        "database": {"ok": db_ok, "schema_version": schema_version, "error": error},
        "providers": {
            "image": bool(orch.settings.image_provider_key),
            "video": bool(orch.settings.video_provider_key),
            "publish": bool(orch.settings.publish_provider_key),
            "analytics": bool(orch.settings.analytics_provider_key),
        },
    }
