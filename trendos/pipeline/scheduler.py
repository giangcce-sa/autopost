"""Scheduler đơn giản cho pipeline định kỳ.

Không phụ thuộc APScheduler/Celery để giữ deployment nhẹ. Production có thể
chạy `trendos schedule` bằng process manager, hoặc thay bằng cron/Kubernetes.
"""

from __future__ import annotations

import asyncio
import logging

from trendos.pipeline.orchestrator import Orchestrator

log = logging.getLogger("trendos.scheduler")


class PipelineScheduler:
    def __init__(
        self,
        orchestrator: Orchestrator | None = None,
        *,
        interval_seconds: int | None = None,
    ) -> None:
        self.orchestrator = orchestrator or Orchestrator()
        self.interval_seconds = (
            interval_seconds or self.orchestrator.settings.scheduler_interval_seconds
        )
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self, *, dry_run: bool = True) -> None:
        while not self._stop.is_set():
            try:
                await self.orchestrator.run(dry_run=dry_run)
            except Exception as exc:
                log.warning("Scheduled pipeline run failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                continue
