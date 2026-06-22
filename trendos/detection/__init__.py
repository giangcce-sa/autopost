"""Tầng DETECT — gom cụm tín hiệu, chấm điểm momentum, xếp hạng."""

from trendos.detection.dedup import cluster_signals
from trendos.detection.ranker import rank_and_filter
from trendos.detection.scorer import TrendScorer

__all__ = ["cluster_signals", "TrendScorer", "rank_and_filter"]
