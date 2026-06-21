"""Test SqliteRepository — round-trip + lịch sử chuỗi thời gian (DB file tạm)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trendos.config import Settings
from trendos.models import ContentFormat, ContentPiece, Signal, SourceName, Trend
from trendos.storage import InMemoryRepository, SqliteRepository, get_repository


def _signal(ext_id: str, score: float, captured_at: datetime | None = None) -> Signal:
    kw = {"captured_at": captured_at} if captured_at else {}
    return Signal(
        source=SourceName.HACKER_NEWS,
        external_id=ext_id,
        title="x",
        metrics={"score": score},
        **kw,
    )


@pytest.fixture
def repo(tmp_path) -> SqliteRepository:
    r = SqliteRepository(str(tmp_path / "test.db"))
    yield r
    r.close()


@pytest.mark.asyncio
async def test_save_and_retrieve_signal_history(repo: SqliteRepository):
    s1 = _signal("1", 10, datetime.now(UTC) - timedelta(hours=2))
    s2 = _signal("1", 30, datetime.now(UTC) - timedelta(hours=1))  # cùng dedup_key
    await repo.save_signals([s1])
    await repo.save_signals([s2])
    history = await repo.get_signal_history([s1.dedup_key])
    assert len(history[s1.dedup_key]) == 2  # giữ chuỗi thời gian cho scorer


@pytest.mark.asyncio
async def test_signal_history_sorted_old_to_new(repo: SqliteRepository):
    early = _signal("1", 10, datetime.now(UTC) - timedelta(hours=3))
    late = _signal("1", 50, datetime.now(UTC) - timedelta(hours=1))
    # Lưu lệch thứ tự để chứng minh sắp xếp theo captured_at, không theo thứ tự ghi.
    await repo.save_signals([late])
    await repo.save_signals([early])
    series = (await repo.get_signal_history([early.dedup_key]))[early.dedup_key]
    assert [s.metrics["score"] for s in series] == [10, 50]


@pytest.mark.asyncio
async def test_signal_history_persists_across_instances(tmp_path):
    """Lịch sử còn nguyên khi mở lại DB — điều InMemory không làm được."""
    path = str(tmp_path / "persist.db")
    r1 = SqliteRepository(path)
    await r1.save_signals([_signal("1", 10)])
    r1.close()

    r2 = SqliteRepository(path)
    history = await r2.get_signal_history(["hacker_news:1"])
    r2.close()
    assert len(history["hacker_news:1"]) == 1


@pytest.mark.asyncio
async def test_get_signal_history_empty_keys(repo: SqliteRepository):
    assert await repo.get_signal_history([]) == {}


@pytest.mark.asyncio
async def test_save_trends_roundtrip_ordered_by_score(repo: SqliteRepository):
    await repo.save_trends(
        [Trend(label="low", score=0.2), Trend(label="high", score=0.9)]
    )
    trends = await repo.list_trends()
    assert [t.label for t in trends] == ["high", "low"]


@pytest.mark.asyncio
async def test_get_trend_by_id(repo: SqliteRepository):
    t = Trend(label="x", score=0.5)
    await repo.save_trends([t])
    fetched = await repo.get_trend(t.id)
    assert fetched is not None and fetched.label == "x"
    assert await repo.get_trend("missing") is None


@pytest.mark.asyncio
async def test_save_content_roundtrip_with_filters(repo: SqliteRepository):
    post = ContentPiece(trend_id="t1", format=ContentFormat.SOCIAL_POST, title="p", body="b")
    blog = ContentPiece(trend_id="t2", format=ContentFormat.BLOG_ARTICLE, title="g", body="b")
    await repo.save_content([post, blog])

    assert len(await repo.list_content()) == 2
    assert len(await repo.list_content(trend_id="t1")) == 1
    by_fmt = await repo.list_content(fmt=ContentFormat.BLOG_ARTICLE)
    assert len(by_fmt) == 1 and by_fmt[0].trend_id == "t2"


def test_get_repository_selects_backend(tmp_path):
    sqlite_settings = Settings(database_url=f"sqlite:///{tmp_path / 'x.db'}")
    assert isinstance(get_repository(sqlite_settings), SqliteRepository)

    mem_settings = Settings(database_url="memory://")
    assert isinstance(get_repository(mem_settings), InMemoryRepository)
