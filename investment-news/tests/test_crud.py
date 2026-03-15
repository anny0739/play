"""DB/CRUD 레이어 유닛 테스트."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Topic, Article, Note
from app.db.crud import (
    upsert_article,
    get_today_articles,
    create_note,
    get_notes_for_article,
    update_note,
    delete_note,
    upsert_market_snapshot,
    get_latest_market_snapshot,
)


@pytest.fixture
def session():
    """인메모리 SQLite 세션."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


@pytest.fixture
def topic(session):
    t = Topic(name="테스트 토픽", category="stock_kr", search_query="테스트")
    session.add(t)
    session.commit()
    return t


def test_upsert_article_creates_new(session, topic):
    art, created = upsert_article(
        session,
        topic_id=topic.id,
        url="https://example.com/news/1",
        title="테스트 기사",
        source="테스트 출처",
    )
    session.commit()
    assert created is True
    assert art.id is not None
    assert art.title == "테스트 기사"


def test_upsert_article_duplicate_skips(session, topic):
    url = "https://example.com/news/2"
    art1, created1 = upsert_article(session, topic_id=topic.id, url=url, title="기사1")
    session.commit()
    art2, created2 = upsert_article(session, topic_id=topic.id, url=url, title="기사1 중복")
    assert created1 is True
    assert created2 is False
    assert art1.id == art2.id


def test_note_lifecycle(session, topic):
    art, _ = upsert_article(
        session, topic_id=topic.id, url="https://example.com/news/3", title="기사3"
    )
    session.commit()

    note = create_note(session, article_id=art.id, content="내 메모", sentiment="bullish")
    session.commit()
    assert note.id is not None

    notes = get_notes_for_article(session, art.id)
    assert len(notes) == 1
    assert notes[0].sentiment == "bullish"

    update_note(session, note.id, content="수정된 메모", sentiment="bearish")
    session.commit()

    notes = get_notes_for_article(session, art.id)
    assert notes[0].content == "수정된 메모"
    assert notes[0].sentiment == "bearish"

    delete_note(session, note.id)
    session.commit()
    notes = get_notes_for_article(session, art.id)
    assert len(notes) == 0


def test_market_snapshot_upsert(session):
    snap = upsert_market_snapshot(
        session,
        snapshot_date="2026-03-15",
        kospi=2500.0,
        kosdaq=800.0,
        sp500=5000.0,
        nasdaq=17000.0,
        usd_krw=1320.0,
    )
    session.commit()
    assert snap.kospi == 2500.0

    # 같은 날짜 업서트 → 덮어쓰기
    snap2 = upsert_market_snapshot(
        session, snapshot_date="2026-03-15", kospi=2510.0
    )
    session.commit()
    latest = get_latest_market_snapshot(session)
    assert latest.kospi == 2510.0
