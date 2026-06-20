"""⑧ Analyst AI — đo lường hiệu suất sau khi đăng.

Thu thập metric của các `Publication` (reach, like, share, comment, watch
time...) và dùng Claude diễn giải → `PerformanceReport` (kèm insight).
"""

from __future__ import annotations

import logging

from trendos.agents.base import BaseAgent, PipelineContext

log = logging.getLogger("trendos.agent.analyst")


class AnalystAgent(BaseAgent):
    name = "analyst"

    async def run(self, ctx: PipelineContext) -> None:
        # TODO(impl): với mỗi publication đã đăng, gọi API analytics nền tảng lấy
        #   metric; cho Claude tóm tắt điều gì hiệu quả/không → PerformanceReport.
        #   Thường chạy ở lần sau (độ trễ), không cùng lượt với đăng bài.
        if not ctx.publications:
            log.info("Analyst: chưa có bài đăng để phân tích — bỏ qua")
            return
        log.info("Analyst: phân tích %d bài đăng (TODO)", len(ctx.publications))
