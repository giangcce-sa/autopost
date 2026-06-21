"""Test tầng COLLECT — map dữ liệu thô → Signal (thuần, không gọi mạng)."""

from __future__ import annotations

from types import SimpleNamespace

from trendos.collectors.github import repo_to_signal
from trendos.collectors.hackernews import story_to_signal
from trendos.collectors.reddit import post_to_signal
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


# ─── GitHub mapper ─────────────────────────────────────────────────────────


def test_github_repo_to_signal_maps_fields():
    item = {
        "full_name": "openai/whisper",
        "html_url": "https://github.com/openai/whisper",
        "description": "Robust speech recognition model",
        "topics": ["speech", "ml"],
        "stargazers_count": 5000,
        "forks_count": 300,
        "watchers_count": 5000,
    }
    sig = repo_to_signal(item)
    assert sig is not None
    assert sig.source == SourceName.GITHUB
    assert sig.external_id == "openai/whisper"
    assert sig.metrics["stars"] == 5000 and sig.metrics["forks"] == 300
    assert "speech" in sig.keywords  # topic được đưa vào keyword


def test_github_repo_to_signal_skips_missing_name():
    assert repo_to_signal({"stargazers_count": 10}) is None


# ─── Reddit mapper ─────────────────────────────────────────────────────────


def test_reddit_post_to_signal_maps_fields():
    submission = SimpleNamespace(
        id="abc123",
        title="New open-source LLM beats GPT-4 on benchmarks",
        permalink="/r/MachineLearning/comments/abc123/x/",
        score=1500,
        num_comments=200,
        upvote_ratio=0.97,
    )
    sig = post_to_signal(submission)
    assert sig is not None
    assert sig.source == SourceName.REDDIT
    assert sig.external_id == "abc123"
    assert sig.url == "https://www.reddit.com/r/MachineLearning/comments/abc123/x/"
    assert sig.metrics["upvotes"] == 1500 and sig.metrics["upvote_ratio"] == 0.97
    assert "llm" in sig.keywords


def test_reddit_post_to_signal_skips_without_id():
    assert post_to_signal(SimpleNamespace(title="x", id=None)) is None
