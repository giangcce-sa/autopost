"""Server-rendered dashboard for TrendOS."""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from trendos.api.deps import get_orchestrator, require_api_key
from trendos.models import ContentApprovalStatus, ContentPiece
from trendos.pipeline import Orchestrator

router = APIRouter(tags=["dashboard"], dependencies=[Depends(require_api_key)])


def _page(title: str, body: str) -> HTMLResponse:
    styles = "\n".join(
        [
            "body { margin: 0; font-family: Inter, system-ui, sans-serif;",
            "  background: #f8fafc; color: #0f172a; }",
            "header { background: #111827; color: white; padding: 18px 28px;",
            "  display: flex; justify-content: space-between; }",
            "nav a { color: #c7d2fe; margin-left: 18px; text-decoration: none;",
            "  font-weight: 700; }",
            "main { max-width: 1180px; margin: 28px auto; padding: 0 20px; }",
            ".grid { display: grid; grid-template-columns: repeat(auto-fit,",
            "  minmax(220px, 1fr)); gap: 16px; }",
            ".card { background: white; border: 1px solid #e2e8f0;",
            "  border-radius: 14px; padding: 18px;",
            "  box-shadow: 0 8px 24px rgba(15,23,42,.06); }",
            "table { width: 100%; border-collapse: collapse; background: white;",
            "  border-radius: 14px; overflow: hidden; }",
            "th, td { padding: 12px 14px; border-bottom: 1px solid #e2e8f0;",
            "  text-align: left; vertical-align: top; }",
            "th { background: #eef2ff; font-size: 12px; text-transform: uppercase;",
            "  letter-spacing: .06em; }",
            ".muted { color: #64748b; }",
            ".status { display: inline-block; border-radius: 999px;",
            "  padding: 4px 10px; background: #e0f2fe; font-weight: 800;",
            "  font-size: 12px; }",
            ".status.approved { background: #dcfce7; color: #166534; }",
            ".status.rejected { background: #fee2e2; color: #991b1b; }",
            ".status.draft { background: #fef3c7; color: #92400e; }",
            ".actions { display: flex; gap: 8px; flex-wrap: wrap; }",
            "button, .button { border: 0; border-radius: 10px; padding: 9px 12px;",
            "  font-weight: 800; background: #111827; color: white;",
            "  text-decoration: none; cursor: pointer; }",
            ".button.secondary, button.secondary { background: #e2e8f0; color: #0f172a; }",
            ".button.good, button.good { background: #16a34a; }",
            ".button.bad, button.bad { background: #dc2626; }",
            ".filters { display: flex; gap: 10px; flex-wrap: wrap; margin: 0 0 16px; }",
            ".preview { white-space: pre-wrap; line-height: 1.65; }",
            ".meta { display: grid; grid-template-columns: repeat(auto-fit,",
            "  minmax(180px, 1fr)); gap: 12px; margin-bottom: 18px; }",
        ]
    )
    html = f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)} · TrendOS</title>
  <style>{styles}</style>
</head>
<body>
  <header>
    <strong>TrendOS Dashboard</strong>
    <nav>
      <a href="/dashboard">Overview</a>
      <a href="/dashboard/runs">Runs</a>
      <a href="/dashboard/trends">Trends</a>
      <a href="/dashboard/content">Content</a>
      <a href="/docs">API</a>
    </nav>
  </header>
  <main>{body}</main>
</body>
</html>"""
    return HTMLResponse(html)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(orch: Orchestrator = Depends(get_orchestrator)):
    runs, trends, content = await _overview_data(orch)
    body = f"""
    <h1>Overview</h1>
    <form action="/dashboard/pipeline/run" method="post" class="card">
      <strong>Run pipeline</strong>
      <label><input type="checkbox" name="dry_run" value="true" checked /> Dry run</label>
      <button type="submit">Start</button>
    </form>
    <div class="grid">
      <div class="card"><div class="muted">Runs</div><h2>{len(runs)}</h2></div>
      <div class="card"><div class="muted">Trends</div><h2>{len(trends)}</h2></div>
      <div class="card"><div class="muted">Content</div><h2>{len(content)}</h2></div>
    </div>
    <h2>Top trends</h2>
    {_trend_table(trends[:8])}
    """
    return _page("Overview", body)


@router.post("/dashboard/pipeline/run")
async def dashboard_run_pipeline(
    background: BackgroundTasks,
    dry_run: bool = True,
    orch: Orchestrator = Depends(get_orchestrator),
):
    run = await orch.create_run(dry_run=dry_run)
    background.add_task(orch.run, dry_run=dry_run, run_id=run.id)
    return RedirectResponse("/dashboard/runs", status_code=303)


@router.get("/dashboard/runs", response_class=HTMLResponse)
async def dashboard_runs(orch: Orchestrator = Depends(get_orchestrator)):
    runs = await orch.repo.list_runs(limit=50)
    rows = "".join(
        f"<tr><td>{escape(r.id[:10])}</td>"
        f"<td><span class='status'>{escape(r.status.value)}</span></td>"
        f"<td>{escape(str(r.dry_run))}</td><td>{escape(str(r.started_at or ''))}</td>"
        f"<td>{escape(str(r.error or ''))}</td></tr>"
        for r in runs
    )
    table = (
        "<table><tr><th>ID</th><th>Status</th><th>Dry</th>"
        f"<th>Started</th><th>Error</th></tr>{rows}</table>"
    )
    return _page("Runs", f"<h1>Runs</h1>{table}")


@router.get("/dashboard/trends", response_class=HTMLResponse)
async def dashboard_trends(orch: Orchestrator = Depends(get_orchestrator)):
    trends = await orch.repo.list_trends(limit=100)
    return _page("Trends", f"<h1>Trends</h1>{_trend_table(trends)}")


@router.get("/dashboard/trends/{trend_id}", response_class=HTMLResponse)
async def dashboard_trend_detail(
    trend_id: str,
    orch: Orchestrator = Depends(get_orchestrator),
):
    trend = await orch.repo.get_trend(trend_id)
    if trend is None:
        raise HTTPException(status_code=404, detail="Trend not found")
    signals = "".join(
        f"<tr><td>{escape(s.source.value)}</td><td>{escape(s.title)}</td>"
        f"<td>{escape(str(s.metrics))}</td></tr>"
        for s in trend.signals
    )
    body = (
        f"<h1>{escape(trend.label)}</h1>"
        f"<div class='card'><strong>Score:</strong> {trend.score:.3f}<br/>"
        f"<strong>Keywords:</strong> {escape(', '.join(trend.keywords))}</div>"
        "<h2>Signals</h2>"
        f"<table><tr><th>Source</th><th>Title</th><th>Metrics</th></tr>{signals}</table>"
    )
    return _page("Trend Detail", body)


@router.get("/dashboard/content", response_class=HTMLResponse)
async def dashboard_content(
    status: ContentApprovalStatus | None = None,
    orch: Orchestrator = Depends(get_orchestrator),
):
    content = await orch.repo.list_content(approval_status=status)
    filters = _content_filters(status)
    rows = "".join(_content_row(c) for c in content)
    table = (
        "<table><tr><th>Title</th><th>Format</th><th>Status</th><th>Trend</th>"
        f"<th>Preview</th><th>Actions</th></tr>{rows}</table>"
    )
    return _page("Content", f"<h1>Content</h1>{filters}{table}")


@router.get("/dashboard/content/{content_id}", response_class=HTMLResponse)
async def dashboard_content_detail(
    content_id: str,
    orch: Orchestrator = Depends(get_orchestrator),
):
    piece = await orch.repo.get_content(content_id)
    if piece is None:
        raise HTTPException(status_code=404, detail="Content not found")
    trend = await orch.repo.get_trend(piece.trend_id)
    assets = await orch.repo.list_assets(content_id=piece.id)
    publications = await orch.repo.list_publications(content_id=piece.id)

    asset_rows = "".join(
        f"<tr><td>{escape(a.type.value)}</td><td>{escape(a.uri)}</td></tr>"
        for a in assets
    )
    publication_rows = "".join(
        f"<tr><td>{escape(p.platform)}</td><td>{escape(p.status.value)}</td>"
        f"<td>{escape(str(p.external_url or ''))}</td></tr>"
        for p in publications
    )
    format_value = escape(piece.format.value)
    trend_label = escape(trend.label if trend else piece.trend_id)
    channel = escape(piece.meta.get("channel", "-"))
    body = f"""
    <div class="actions">
      <a class="button secondary" href="/dashboard/content">Back</a>
      {_approval_forms(piece)}
    </div>
    <h1>{escape(piece.title)}</h1>
    <div class="meta">
      <div class="card"><div class="muted">Status</div>{_status_badge(piece.approval_status)}</div>
      <div class="card"><div class="muted">Format</div><strong>{format_value}</strong></div>
      <div class="card"><div class="muted">Trend</div><strong>{trend_label}</strong></div>
      <div class="card"><div class="muted">Channel</div><strong>{channel}</strong></div>
    </div>
    <h2>Preview</h2>
    <div class="card preview">{escape(piece.body)}</div>
    <h2>Metadata</h2>
    <div class="card"><pre>{escape(str(piece.meta))}</pre></div>
    <h2>Assets</h2>
    <table><tr><th>Type</th><th>URI</th></tr>{asset_rows}</table>
    <h2>Publications</h2>
    <table><tr><th>Platform</th><th>Status</th><th>URL</th></tr>{publication_rows}</table>
    """
    return _page("Content Preview", body)


@router.post("/dashboard/content/{content_id}/approve")
async def dashboard_approve_content(
    content_id: str,
    orch: Orchestrator = Depends(get_orchestrator),
):
    piece = await orch.repo.update_content_approval(content_id, ContentApprovalStatus.APPROVED)
    if piece is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return RedirectResponse(f"/dashboard/content/{content_id}", status_code=303)


@router.post("/dashboard/content/{content_id}/reject")
async def dashboard_reject_content(
    content_id: str,
    orch: Orchestrator = Depends(get_orchestrator),
):
    piece = await orch.repo.update_content_approval(content_id, ContentApprovalStatus.REJECTED)
    if piece is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return RedirectResponse(f"/dashboard/content/{content_id}", status_code=303)


async def _overview_data(orch: Orchestrator):
    return (
        await orch.repo.list_runs(limit=20),
        await orch.repo.list_trends(limit=20),
        await orch.repo.list_content(),
    )


def _trend_table(trends) -> str:
    rows = "".join(
        f"<tr><td>{escape(t.label)}</td><td>{t.score:.3f}</td>"
        f"<td><a href='/dashboard/trends/{escape(t.id)}'>Open</a></td>"
        f"<td>{escape(', '.join(s.value for s in t.sources))}</td></tr>"
        for t in trends
    )
    return (
        "<table><tr><th>Trend</th><th>Score</th><th>Detail</th><th>Sources</th></tr>"
        f"{rows}</table>"
    )


def _content_filters(active: ContentApprovalStatus | None) -> str:
    all_cls = "button" if active is None else "button secondary"
    links = [f'<a class="{all_cls}" href="/dashboard/content">All</a>']
    for status in ContentApprovalStatus:
        cls = "button" if active == status else "button secondary"
        links.append(
            f'<a class="{cls}" href="/dashboard/content?status={escape(status.value)}">'
            f"{escape(status.value.title())}</a>"
        )
    return f"<div class='filters'>{''.join(links)}</div>"


def _content_row(piece: ContentPiece) -> str:
    preview = piece.body[:180] + ("..." if len(piece.body) > 180 else "")
    return (
        f"<tr><td>{escape(piece.title)}</td><td>{escape(piece.format.value)}</td>"
        f"<td>{_status_badge(piece.approval_status)}</td>"
        f"<td>{escape(piece.trend_id[:10])}</td><td>{escape(preview)}</td>"
        "<td><div class='actions'>"
        f"<a class='button secondary' href='/dashboard/content/{escape(piece.id)}'>Preview</a>"
        f"{_approval_forms(piece)}"
        "</div></td></tr>"
    )


def _status_badge(status: ContentApprovalStatus) -> str:
    value = escape(status.value)
    return f"<span class='status {value}'>{value}</span>"


def _approval_forms(piece: ContentPiece) -> str:
    approve = (
        f"<form action='/dashboard/content/{escape(piece.id)}/approve' method='post'>"
        "<button class='good' type='submit'>Approve</button></form>"
    )
    reject = (
        f"<form action='/dashboard/content/{escape(piece.id)}/reject' method='post'>"
        "<button class='bad' type='submit'>Reject</button></form>"
    )
    return approve + reject
