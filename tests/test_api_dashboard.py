"""Smoke tests for FastAPI dashboard routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from trendos.api.app import app


def test_dashboard_routes_render_html():
    client = TestClient(app)
    for path in ["/dashboard", "/dashboard/runs", "/dashboard/trends", "/dashboard/content"]:
        res = client.get(path)
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "TrendOS Dashboard" in res.text
