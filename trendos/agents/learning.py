"""⑨ Learning AI — đóng vòng phản hồi.

Từ các `PerformanceReport`, rút ra điều gì làm nên nội dung lan truyền và đề
xuất tinh chỉnh: điều chỉnh trọng số scorer (① Trend Hunter) và ghi chú cải
thiện prompt (③ Strategist, ④ Copywriter) → `LearningUpdate`.

Cài đặt hiện tại là heuristic tổng hợp; bước sau có thể thay bằng tương quan
đặc trưng↔hiệu suất theo thời gian (ML) và cơ chế áp dụng update tự động.
"""

from __future__ import annotations

import logging
from collections import Counter

from trendos.agents.base import BaseAgent, PipelineContext
from trendos.models import LearningUpdate, PerformanceReport

log = logging.getLogger("trendos.agent.learning")

# Ngưỡng engagement coi là "tốt" (đồng bộ với analyst.derive_insights).
_GOOD_ENGAGEMENT = 0.05


def summarize(reports: list[PerformanceReport]) -> LearningUpdate:
    """Tổng hợp các báo cáo thành một đề xuất tinh chỉnh (hàm thuần, test được)."""
    if not reports:
        return LearningUpdate()

    engagements = [r.metrics.get("engagement_rate", 0.0) for r in reports]
    avg_eng = sum(engagements) / len(engagements)

    insight_counts = Counter(i for r in reports for i in r.insights)
    prompt_notes = [f"Hay gặp: {ins} ({n} lần)" for ins, n in insight_counts.most_common(3)]

    weight_adjustments: dict[str, float] = {}
    if avg_eng < _GOOD_ENGAGEMENT:
        # Hiệu suất thấp → nội dung chưa "bắt trend" đủ sớm; nhấn momentum sớm hơn.
        weight_adjustments["acceleration"] = +0.5
        weight_adjustments["novelty"] = +0.25
        prompt_notes.append("Engagement thấp: hook mạnh hơn, bám tín hiệu sớm hơn.")

    return LearningUpdate(weight_adjustments=weight_adjustments, prompt_notes=prompt_notes)


class LearningAgent(BaseAgent):
    name = "learning"

    async def run(self, ctx: PipelineContext) -> None:
        if not ctx.reports:
            log.info("Learning: chưa có báo cáo để học — bỏ qua")
            return
        update = summarize(ctx.reports)
        ctx.learning.append(update)
        log.info(
            "Learning: đề xuất %d điều chỉnh trọng số, %d ghi chú prompt",
            len(update.weight_adjustments),
            len(update.prompt_notes),
        )
