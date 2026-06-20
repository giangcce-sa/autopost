"""Tiện ích xử lý văn bản dùng chung (trích keyword, tách token).

Dùng bởi collectors (điền `Signal.keywords`) và detection/dedup (gom cụm). Là
cách trích keyword nhẹ, offline — không cần model/mạng. Có thể nâng cấp sau
(RAKE/KeyBERT) mà giữ nguyên chữ ký hàm.
"""

from __future__ import annotations

import re

# Stopword tối thiểu (EN + một ít VI) — đủ cho trích keyword & gom cụm.
STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "this", "that", "it", "as", "at", "by",
        "from", "how", "why", "what", "new", "show", "hn", "your", "you", "we",
        "và", "của", "các", "những", "một", "là", "có", "cho", "với", "khi",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Tách văn bản thành token đã lowercase, bỏ token ngắn và stopword."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2 and t not in STOPWORDS]


def extract_keywords(text: str, *, limit: int = 10) -> list[str]:
    """Trích tối đa `limit` keyword (giữ thứ tự xuất hiện, khử trùng)."""
    seen: dict[str, None] = {}
    for tok in tokenize(text):
        if tok not in seen:
            seen[tok] = None
        if len(seen) >= limit:
            break
    return list(seen)
