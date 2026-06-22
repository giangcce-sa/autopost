"""Smoke tests for FastAPI dashboard routes."""

from __future__ import annotations

import anyio
from fastapi.testclient import TestClient

from trendos.api.app import app
from trendos.api.deps import get_orchestrator
from trendos.models import ContentApprovalStatus, ContentFormat, ContentPiece


def test_dashboard_routes_render_html():
    client = TestClient(app)
    for path in ["/dashboard", "/dashboard/runs", "/dashboard/trends", "/dashboard/content"]:
        res = client.get(path)
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "TrendOS Dashboard" in res.text


def test_dashboard_content_preview_and_approval_flow():
    orch = get_orchestrator()
    piece = ContentPiece(
        trend_id="dashboard-trend",
        format=ContentFormat.SOCIAL_POST,
        title="Dashboard approval test",
        body="Preview body",
    )
    client = TestClient(app)

    anyio.run(orch.repo.save_content, [piece])

    detail = client.get(f"/dashboard/content/{piece.id}")
    assert detail.status_code == 200
    assert "Preview body" in detail.text
    assert "draft" in detail.text

    approve = client.post(f"/dashboard/content/{piece.id}/approve", follow_redirects=False)
    assert approve.status_code == 303
    updated = anyio.run(orch.repo.get_content, piece.id)
    assert updated is not None
    assert updated.approval_status == ContentApprovalStatus.APPROVED
