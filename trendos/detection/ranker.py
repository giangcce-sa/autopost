"""Xếp hạng và lọc xu hướng đã chấm điểm.

Giới hạn top-N để kiểm soát chi phí giai đoạn sinh nội dung (mỗi xu hướng =
một vài lần gọi Claude API).
"""

from __future__ import annotations

from trendos.models import Trend


def rank_and_filter(trends: list[Trend], *, top_n: int, min_score: float) -> list[Trend]:
    """Lọc theo ngưỡng điểm tối thiểu rồi lấy `top_n` xu hướng điểm cao nhất."""
    qualified = [t for t in trends if t.score >= min_score]
    qualified.sort(key=lambda t: t.score, reverse=True)
    return qualified[:top_n]
