"""Test tầng COLLECT — map dữ liệu thô → Signal (thuần, không gọi mạng)."""

from __future__ import annotations

from trendos.collectors.hackernews import story_to_signal
from trendos.collectors.rss import entry_to_signal
from trendos.models import SourceName
from trendos.text import extract_keywords, tokenize

# ─── Keyword util ──────────────────────────────────────────────────────────


def test_tokenize_drops_stopwords_and_short_tokens():
    toks = tokenize("The new AI agent framework is here")
    assert "the" not in toks and "is" not in toks and "new" not in toks
    assert "agent" in toks and "framework" in toks


def test_extract_keywords_dedups_and_limits():
    kws = extract_keywords("rust rust compiler compiler speed", limit=2)
    assert kws == ["rust", "compiler"]


# ─── Hacker News mapper ──────────────────────────────────────────────────


def test_story_to_signal_maps_fields():
    item = {
        "id": 42,
        "type": "story",
        "title": "Postgres beats MySQL in new benchmark",
        "url": "https://example.com/x",
        "score": 250,
        "descendants": 88,
    }
    sig = story_to_signal(item)
    assert sig is not None
    assert sig.source == SourceName.HACKER_NEWS
    assert sig.external_id == "42"
    assert sig.metrics["score"] == 250 and sig.metrics["comments"] == 88
    assert "postgres" in sig.keywords


def test_story_to_signal_skips_non_story():
    assert story_to_signal({"id": 1, "type": "job", "title": "We are hiring"}) is None
    assert story_to_signal({}) is None


# ─── RSS mapper ────────────────────────────────────────────────────────────


def test_entry_to_signal_from_dict_like():
    entry = {
        "id": "guid-1",
        "title": "Apple announces new chip",
        "link": "https://news.example/apple",
        "summary": "A faster processor",
    }
    sig = entry_to_signal(entry, feed_url="https://news.example/rss")
    assert sig is not None
    assert sig.source == SourceName.RSS
    assert sig.external_id == "guid-1"
    assert sig.url == "https://news.example/apple"
    assert "apple" in sig.keywords


def test_entry_without_title_is_skipped():
    assert entry_to_signal({"link": "x"}, feed_url="f") is None
