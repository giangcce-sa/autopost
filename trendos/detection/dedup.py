"""Gom cụm tín hiệu nói về cùng một chủ đề thành một `Trend`.

Cùng một sự vật có thể xuất hiện trên HN, Reddit, GitHub cùng lúc — gom lại
để (a) tránh trùng lặp và (b) tính được tín hiệu "đa nguồn" cho scorer.
"""

from __future__ import annotations

from trendos.models import Signal, Trend


def cluster_signals(signals: list[Signal]) -> list[Trend]:
    """Gom danh sách tín hiệu thành các xu hướng ứng viên.

    Khởi đầu (đơn giản): nhóm theo keyword chuẩn hoá / so khớp mờ tiêu đề.
    Mở rộng sau: embedding semantic + clustering (vd. cosine + HDBSCAN) để
    bắt được các diễn đạt khác nhau của cùng chủ đề.
    """
    # TODO(impl): thay placeholder "mỗi tín hiệu một trend" bằng clustering thật.
    trends: list[Trend] = []
    for sig in signals:
        trends.append(
            Trend(
                label=sig.title,
                keywords=sig.keywords,
                signals=[sig],
                first_seen=sig.captured_at,
            )
        )
    return trends


def _normalize(text: str) -> str:
    """Chuẩn hoá chuỗi để so khớp (placeholder cho bước dedup thật)."""
    return " ".join(text.lower().split())
