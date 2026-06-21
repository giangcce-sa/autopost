"""API auth, pagination, and health smoke tests."""

from __future__ import annotations

import anyio
from fastapi.testclient import TestClient

from trendos.api.app import app
from trendos.api.deps import get_orchestrator
from trendos.models import ContentApprovalStatus, ContentFormat, ContentPiece


def test_pipeline_run_requires_api_key_when_configured():
    orch = get_orchestrator()
    old_key = orch.settings.api_key
    orch.settings.api_key = "secret"
    client = TestClient(app)
    try:
        assert client.post("/pipeline/run?dry_run=true").status_code == 401
        ok = client.post("/pipeline/run?dry_run=true", headers={"X-TrendOS-Key": "secret"})
        assert ok.status_code == 200
    finally:
        orch.settings.api_key = old_key


def test_list_endpoints_accept_pagination_and_health_details():
    client = TestClient(app)
    assert client.get("/trends?limit=5&offset=0").status_code == 200
    assert client.get("/runs?limit=5&offset=0").status_code == 200
    assert client.get("/content?limit=5&offset=0").status_code == 200
    res = client.get("/health/details")
    assert res.status_code == 200
    assert "database" in res.json()


def test_content_approval_api_endpoint_updates_status():
    orch = get_orchestrator()
    client = TestClient(app)

    piece = ContentPiece(
        trend_id="api-trend",
        format=ContentFormat.SOCIAL_POST,
        title="API approval test",
        body="body",
    )
    anyio.run(orch.repo.save_content, [piece])

    res = client.post(f"/content/{piece.id}/approve")

    assert res.status_code == 200
    assert res.json()["approval_status"] == ContentApprovalStatus.APPROVED
