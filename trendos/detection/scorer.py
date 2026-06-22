"""Engine chấm điểm xu hướng — TRÁI TIM của sứ mệnh "trước đám đông".

Điểm là tổ hợp có trọng số (xem ARCHITECTURE.md §4.2):

    score = w_v·velocity + w_a·acceleration + w_n·novelty
          + w_x·cross_source − w_s·saturation

Trực giác: thứ ĐÃ viral có velocity cao nhưng acceleration thấp và saturation
cao → bị kéo xuống. Thứ ĐANG chớm nổi có acceleration + novelty cao → nổi lên
đầu bảng. Vì vậy trọng số acceleration là lớn nhất (config.ScoringWeights).

Velocity/acceleration cần CHUỖI THỜI GIAN: cùng một tín hiệu (cùng `dedup_key`)
phải được quan sát qua nhiều lần chạy. `history[dedup_key]` là các lần quan sát
(không cần sắp xếp trước; scorer tự sắp theo `captured_at`), do storage cung cấp.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from trendos.config import ScoringWeights
from trendos.models import Signal, SourceName, Trend

# Metric đại diện "độ lớn" theo từng nguồn (để tính đạo hàm theo thời gian).
# Dùng alias để scorer không lệch nếu collector/API đặt tên metric khác nhau.
_PRIMARY_METRICS: dict[SourceName, tuple[str, ...]] = {
    SourceName.HACKER_NEWS: ("score",),
    SourceName.REDDIT: ("upvotes", "ups", "score", "comments"),
    SourceName.YOUTUBE: ("views", "view_count", "viewCount"),
    SourceName.GITHUB: ("stars", "stargazers_count"),
    SourceName.GOOGLE_TRENDS: ("search_index",),
    SourceName.TWITTER: ("likes", "like_count"),
    SourceName.TIKTOK: ("play_count", "views"),
}


class TrendScorer:
    def __init__(self, weights: ScoringWeights) -> None:
        self.w = weights

    def score(self, trend: Trend, history: dict[str, list[Signal]] | None = None) -> Trend:
        """Tính điểm cho một xu hướng và ghi vào trend (trả lại chính nó)."""
        history = history or {}

        velocity = self._velocity(trend, history)
        acceleration = self._acceleration(trend, history)
        novelty = self._novelty(trend)
        cross = self._cross_source(trend)
        saturation = self._saturation(trend, history)

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

    # ─── Tiện ích chuỗi thời gian ────────────────────────────────────────

    def _primary_metric(self, sig: Signal) -> float:
        for key in _PRIMARY_METRICS.get(sig.source, ()):
            if key in sig.metrics:
                return float(sig.metrics[key])
        return max(sig.metrics.values()) if sig.metrics else 0.0

    def _series(
        self, sig: Signal, history: dict[str, list[Signal]]
    ) -> list[tuple[datetime, float]]:
        """Chuỗi (thời điểm, độ lớn) của một tín hiệu, cũ → mới.

        Gộp lịch sử với quan sát hiện tại, khử trùng theo `captured_at`.
        """
        obs = list(history.get(sig.dedup_key, []))
        if not any(o.captured_at == sig.captured_at for o in obs):
            obs.append(sig)
        obs.sort(key=lambda s: s.captured_at)
        return [(s.captured_at, self._primary_metric(s)) for s in obs]

    @staticmethod
    def _dt_hours(t0: datetime, t1: datetime) -> float:
        return max((t1 - t0).total_seconds() / 3600.0, 1e-6)  # tránh chia 0

    def _signal_velocity(self, series: list[tuple[datetime, float]]) -> float | None:
        """Δmetric / Δt(giờ) giữa hai quan sát gần nhất. None nếu chưa đủ điểm."""
        if len(series) < 2:
            return None
        (t0, m0), (t1, m1) = series[-2], series[-1]
        return (m1 - m0) / self._dt_hours(t0, t1)

    def _signal_acceleration(self, series: list[tuple[datetime, float]]) -> float | None:
        """Thay đổi của velocity giữa hai khoảng liên tiếp. Cần >= 3 điểm."""
        if len(series) < 3:
            return None
        (t0, m0), (t1, m1), (t2, m2) = series[-3], series[-2], series[-1]
        v_prev = (m1 - m0) / self._dt_hours(t0, t1)
        v_curr = (m2 - m1) / self._dt_hours(t1, t2)
        return v_curr - v_prev

    # ─── Các thành phần điểm (chuẩn hoá ~[0,1]) ──────────────────────────

    @staticmethod
    def _squash_pos(x: float, scale: float) -> float:
        """tanh của phần dương → [0,1). Giá trị âm (chững/giảm) coi như 0."""
        return math.tanh(max(0.0, x) / scale) if scale > 0 else 0.0

    def _velocity(self, trend: Trend, history: dict[str, list[Signal]]) -> float:
        vals = [
            v
            for sig in trend.signals
            if (v := self._signal_velocity(self._series(sig, history))) is not None
        ]
        if not vals:
            return 0.0
        return self._squash_pos(sum(vals) / len(vals), self.w.velocity_scale)

    def _acceleration(self, trend: Trend, history: dict[str, list[Signal]]) -> float:
        vals = [
            a
            for sig in trend.signals
            if (a := self._signal_acceleration(self._series(sig, history))) is not None
        ]
        if not vals:
            return 0.0
        return self._squash_pos(sum(vals) / len(vals), self.w.acceleration_scale)

    def _novelty(self, trend: Trend) -> float:
        """Xu hướng vừa xuất hiện = điểm cao, phân rã mũ theo tuổi."""
        age_h = self._dt_hours(trend.first_seen, datetime.now(UTC))
        return math.exp(-age_h / self.w.novelty_tau_hours)

    def _cross_source(self, trend: Trend) -> float:
        """Xuất hiện trên nhiều nguồn độc lập = xác nhận mạnh hơn."""
        n = len(trend.sources)
        if n <= 1:
            return 0.0
        return min(1.0, (n - 1) / 3.0)  # bão hoà ở ~4 nguồn

    def _saturation(self, trend: Trend, history: dict[str, list[Signal]]) -> float:
        """Phạt: volume hiện tại đã rất cao = đám đông đã biết, hết 'sớm'."""
        volume = 0.0
        for sig in trend.signals:
            series = self._series(sig, history)
            if series:
                volume += series[-1][1]  # độ lớn mới nhất
        if self.w.saturation_cap <= 0:
            return 0.0
        return min(1.0, volume / self.w.saturation_cap)
