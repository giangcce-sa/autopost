# TrendOS Runbook

## Local Setup

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,sources]"
cp .env.example .env
```

## Run API

```bash
.venv/bin/uvicorn trendos.api.app:app --reload
```

Open:

- Dashboard: http://127.0.0.1:8000/dashboard
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health/details

## API Key

Set `API_KEY` in `.env` to protect dashboard and write endpoints.

```bash
API_KEY=change-me
```

Use either header:

```bash
X-TrendOS-Key: change-me
Authorization: Bearer change-me
```

## Dry Run

```bash
.venv/bin/python -m trendos.cli run --dry-run
.venv/bin/python -m trendos.cli runs list
.venv/bin/python -m trendos.cli trends list --limit 10
```

## Local Full Pipeline

Local providers create files and receipts without external side effects.

```env
IMAGE_PROVIDER_KEY=local
VIDEO_PROVIDER_KEY=local
PUBLISH_PROVIDER_KEY=local
ANALYTICS_PROVIDER_KEY=local
OUTPUT_DIR=trendos_output
ANTHROPIC_API_KEY=...
```

Then:

```bash
.venv/bin/python -m trendos.cli run --full
```

## Scheduler

```bash
.venv/bin/python -m trendos.cli schedule --dry-run --interval 3600
```

Use a process manager in production. The orchestrator has an in-process lock to
avoid overlapping runs within the same worker.

## Docker

```bash
docker compose up --build
```

## Quality Gate

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy trendos
```

## Provider Notes

Production posting/video/image adapters are intentionally isolated behind
provider interfaces. Use `local` adapters for safe development.

Provider keys also accept import paths:

```env
IMAGE_PROVIDER_KEY=my_project.providers:ImageProvider
VIDEO_PROVIDER_KEY=my_project.providers:video_provider
PUBLISH_PROVIDER_KEY=my_project.providers:MetaPublishProvider
ANALYTICS_PROVIDER_KEY=my_project.providers:AnalyticsProvider
```

Provider classes/factories may accept no arguments or one `Settings` argument.
Add real provider adapters only after API credentials, approval workflow, and
publishing policy are confirmed.
