"""Gom cụm tín hiệu nói về cùng một chủ đề thành một `Trend`.

Cùng một sự vật có thể xuất hiện trên HN, Reddit, GitHub cùng lúc — gom lại
để (a) tránh trùng lặp và (b) tính được tín hiệu "đa nguồn" cho scorer.

Cài đặt hiện tại: **gom theo từ khoá** (offline, không cần model). Mỗi tín hiệu
được rút về một tập token (từ `keywords` nếu có, không thì tách từ tiêu đề, bỏ
stopword). Hai tín hiệu thuộc cùng cụm nếu độ tương đồng Jaccard ≥ ngưỡng.

Mở rộng sau: thay bước similarity bằng embedding semantic (cosine) để bắt các
diễn đạt khác nhau của cùng chủ đề — interface `cluster_signals` giữ nguyên.
"""

from __future__ import annotations

import re

from trendos.models import Signal, Trend

# Ngưỡng Jaccard để xếp hai tín hiệu vào cùng cụm.
_SIMILARITY_THRESHOLD = 0.3

# Stopword tối thiểu (EN + một ít VI) — đủ cho gom cụm từ khoá.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "this", "that", "it", "as", "at", "by",
    "from", "how", "why", "what", "new", "show", "hn",
    "và", "của", "các", "những", "một", "là", "có", "cho", "với", "khi",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(signal: Signal) -> set[str]:
    """Tập token đại diện một tín hiệu (ưu tiên keyword, fallback tách tiêu đề)."""
    if signal.keywords:
        raw = " ".join(signal.keywords)
    else:
        raw = signal.title
    toks = {t for t in _TOKEN_RE.findall(raw.lower()) if len(t) > 2 and t not in _STOPWORDS}
    return toks


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def cluster_signals(signals: list[Signal]) -> list[Trend]:
    """Gom danh sách tín hiệu thành các xu hướng ứng viên (greedy by Jaccard)."""
    clusters: list[dict] = []  # mỗi cụm: {signals, tokens}

    for sig in signals:
        toks = _tokens(sig)
        best_idx, best_sim = -1, 0.0
        for i, cl in enumerate(clusters):
            sim = _jaccard(toks, cl["tokens"])
            if sim > best_sim:
                best_idx, best_sim = i, sim
        if best_idx >= 0 and best_sim >= _SIMILARITY_THRESHOLD:
            cl = clusters[best_idx]
            cl["signals"].append(sig)
            cl["tokens"] |= toks
        else:
            clusters.append({"signals": [sig], "tokens": set(toks)})

    return [_to_trend(cl) for cl in clusters]


def _to_trend(cluster: dict) -> Trend:
    sigs: list[Signal] = cluster["signals"]
    # Nhãn: tiêu đề dài nhất (thường mô tả đầy đủ nhất).
    label = max((s.title for s in sigs), key=len, default="")
    # first_seen: thời điểm sớm nhất quan sát được trong cụm.
    first_seen = min(s.captured_at for s in sigs)
    return Trend(
        label=label,
        keywords=sorted(cluster["tokens"]),
        signals=sigs,
        first_seen=first_seen,
    )
