"""⑨ Learning AI — đóng vòng phản hồi.

Từ các `PerformanceReport`, rút ra điều gì làm nên nội dung lan truyền và đề
xuất tinh chỉnh: điều chỉnh trọng số scorer (① Trend Hunter) và ghi chú cải
thiện prompt (③ Strategist, ④ Copywriter) → `LearningUpdate`.
"""

from __future__ import annotations

import logging

from trendos.agents.base import BaseAgent, PipelineContext

log = logging.getLogger("trendos.agent.learning")


class LearningAgent(BaseAgent):
    name = "learning"

    async def run(self, ctx: PipelineContext) -> None:
        # TODO(impl): tổng hợp report theo thời gian, tương quan đặc trưng xu hướng/
        #   nội dung với hiệu suất; xuất LearningUpdate(weight_adjustments,
        #   prompt_notes). Cơ chế áp dụng update (cập nhật config/prompt store)
        #   sẽ thiết kế cùng tầng lưu trữ bền.
        if not ctx.reports:
            log.info("Learning: chưa có báo cáo để học — bỏ qua")
            return
        log.info("Learning: học từ %d báo cáo (TODO)", len(ctx.reports))
