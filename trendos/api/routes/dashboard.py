"""Server-rendered dashboard for TrendOS."""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from trendos.api.deps import get_orchestrator, require_api_key
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
async def dashboard_content(orch: Orchestrator = Depends(get_orchestrator)):
    content = await orch.repo.list_content()
    rows = "".join(
        f"<tr><td>{escape(c.title)}</td><td>{escape(c.format.value)}</td>"
        f"<td>{escape(c.trend_id[:10])}</td><td>{escape(c.body[:180])}</td></tr>"
        for c in content
    )
    table = (
        "<table><tr><th>Title</th><th>Format</th><th>Trend</th>"
        f"<th>Preview</th></tr>{rows}</table>"
    )
    return _page("Content", f"<h1>Content</h1>{table}")


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
