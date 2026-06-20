"""Engine chấm điểm xu hướng — TRÁI TIM của sứ mệnh "trước đám đông".

Điểm là tổ hợp có trọng số (xem ARCHITECTURE.md §4.2):

    score = w_v·velocity + w_a·acceleration + w_n·novelty
          + w_x·cross_source − w_s·saturation

Trực giác: thứ ĐÃ viral có velocity cao nhưng acceleration thấp và saturation
cao → bị kéo xuống. Thứ ĐANG chớm nổi có acceleration + novelty cao → nổi lên
đầu bảng. Vì vậy trọng số acceleration là lớn nhất (config.ScoringWeights).

Velocity/acceleration cần CHUỖI THỜI GIAN: cùng một tín hiệu phải được quan sát
qua nhiều lần chạy. `history` truyền vào là các lần quan sát trước của cùng
`dedup_key`, do storage cung cấp.
"""

from __future__ import annotations

from datetime import UTC, datetime

from trendos.config import ScoringWeights
from trendos.models import Signal, Trend


class TrendScorer:
    def __init__(self, weights: ScoringWeights) -> None:
        self.w = weights

    def score(self, trend: Trend, history: dict[str, list[Signal]] | None = None) -> Trend:
        """Tính điểm cho một xu hướng và ghi vào trend (trả lại chính nó).

        `history[dedup_key]` = các lần quan sát trước (cũ → mới) của tín hiệu đó.
        """
        history = history or {}

        velocity = self._velocity(trend, history)
        acceleration = self._acceleration(trend, history)
        novelty = self._novelty(trend)
        cross = self._cross_source(trend)
        saturation = self._saturation(trend)

        trend.momentum = velocity
        trend.acceleration = acceleration
        trend.novelty = novelty
        trend.score = (
            self.w.velocity * velocity
            + self.w.acceleration * acceleration
            + self.w.novelty * novelty
            + self.w.cross_source * cross
            - self.w.saturation * saturation
        )
        trend.updated_at = datetime.now(UTC)
        return trend

    # ─── Các thành phần điểm ─────────────────────────────────────────────
    # Tất cả nên trả về giá trị đã chuẩn hoá ~[0,1] để trọng số có ý nghĩa.

    def _primary_metric(self, sig: Signal) -> float:
        """Chọn một con số đại diện 'độ lớn' của tín hiệu để tính đạo hàm."""
        # TODO(impl): chọn metric theo nguồn (score/views/search_index...).
        if not sig.metrics:
            return 0.0
        return max(sig.metrics.values())

    def _velocity(self, trend: Trend, history: dict[str, list[Signal]]) -> float:
        """Tốc độ tăng = Δmetric / Δt giữa hai lần quan sát gần nhất."""
        # TODO(impl): với mỗi signal, ghép lần quan sát hiện tại với gần nhất trong
        #   history, tính (m_now - m_prev) / (t_now - t_prev), chuẩn hoá & tổng hợp.
        return 0.0

    def _acceleration(self, trend: Trend, history: dict[str, list[Signal]]) -> float:
        """Gia tốc = thay đổi của velocity (đạo hàm bậc 2). Tín hiệu SỚM nhất."""
        # TODO(impl): cần >= 3 điểm thời gian; tính chênh lệch velocity liên tiếp.
        return 0.0

    def _novelty(self, trend: Trend) -> float:
        """Độ mới: xu hướng vừa xuất hiện gần đây = điểm cao, phân rã theo tuổi."""
        # TODO(impl): vd. exp(-age_hours / tau). Hiện trả 0 khi chưa cài.
        return 0.0

    def _cross_source(self, trend: Trend) -> float:
        """Xuất hiện trên nhiều nguồn độc lập = xác nhận mạnh hơn."""
        n = len(trend.sources)
        if n <= 1:
            return 0.0
        return min(1.0, (n - 1) / 3.0)  # bão hoà ở ~4 nguồn

    def _saturation(self, trend: Trend) -> float:
        """Phạt: volume đã rất cao = đám đông đã biết, hết 'sớm'."""
        # TODO(impl): chuẩn hoá volume tuyệt đối so với baseline lịch sử.
        return 0.0
