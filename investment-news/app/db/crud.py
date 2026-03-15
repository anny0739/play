from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.db.models import Article, Digest, InvestorSnapshot, MarketSnapshot, Note, Topic

# ── Topics ──────────────────────────────────────────────────────────────────


def get_active_topics(session: Session) -> list[Topic]:
    return session.query(Topic).filter(Topic.is_active == True).all()


def get_topics_by_category(session: Session, category: str) -> list[Topic]:
    return session.query(Topic).filter(Topic.category == category, Topic.is_active == True).all()


# ── Articles ─────────────────────────────────────────────────────────────────


def upsert_article(session: Session, **kwargs) -> tuple[Article, bool]:
    """Return (article, created). If URL already exists, skip insert."""
    url = kwargs["url"]
    existing = session.query(Article).filter(Article.url == url).first()
    if existing:
        return existing, False
    article = Article(**kwargs)
    session.add(article)
    session.flush()
    return article, True


def get_today_articles(session: Session, category: str | None = None) -> list[Article]:
    query = (
        session.query(Article)
        .join(Topic)
        .options(joinedload(Article.topic))
        .filter(Article.fetched_at >= datetime.combine(date.today(), datetime.min.time()))
    )
    if category:
        query = query.filter(Topic.category == category)
    return query.order_by(desc(Article.fetched_at)).all()


def get_articles_without_summary(session: Session, limit: int = 50) -> list[Article]:
    return (
        session.query(Article)
        .filter(Article.summary == None)
        .order_by(desc(Article.fetched_at))
        .limit(limit)
        .all()
    )


def update_article_summary(session: Session, article_id: int, summary: str):
    session.query(Article).filter(Article.id == article_id).update({"summary": summary})


# ── Notes ─────────────────────────────────────────────────────────────────────


def create_note(
    session: Session, article_id: int, content: str, sentiment: str | None = None
) -> Note:
    note = Note(article_id=article_id, content=content, sentiment=sentiment)
    session.add(note)
    session.flush()
    return note


def get_notes_for_article(session: Session, article_id: int) -> list[Note]:
    return session.query(Note).filter(Note.article_id == article_id).all()


def update_note(session: Session, note_id: int, content: str, sentiment: str | None = None):
    session.query(Note).filter(Note.id == note_id).update(
        {"content": content, "sentiment": sentiment, "updated_at": datetime.now(UTC)}
    )


def delete_note(session: Session, note_id: int):
    session.query(Note).filter(Note.id == note_id).delete()


def get_all_notes(session: Session) -> list[Note]:
    return session.query(Note).join(Article).order_by(desc(Note.created_at)).all()


# ── Market Snapshots ──────────────────────────────────────────────────────────


def upsert_market_snapshot(session: Session, snapshot_date: str, **kwargs) -> MarketSnapshot:
    existing = (
        session.query(MarketSnapshot).filter(MarketSnapshot.snapshot_date == snapshot_date).first()
    )
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        existing.fetched_at = datetime.now(UTC)
        return existing
    snapshot = MarketSnapshot(snapshot_date=snapshot_date, **kwargs)
    session.add(snapshot)
    session.flush()
    return snapshot


def get_latest_market_snapshot(session: Session) -> MarketSnapshot | None:
    return session.query(MarketSnapshot).order_by(desc(MarketSnapshot.snapshot_date)).first()


# ── Investor Snapshots ────────────────────────────────────────────────────────


def upsert_investor_snapshot(
    session: Session, snapshot_date: str, market: str, **kwargs
) -> InvestorSnapshot:
    existing = (
        session.query(InvestorSnapshot)
        .filter(
            InvestorSnapshot.snapshot_date == snapshot_date,
            InvestorSnapshot.market == market,
        )
        .first()
    )
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        existing.fetched_at = datetime.now(UTC)
        return existing
    snap = InvestorSnapshot(snapshot_date=snapshot_date, market=market, **kwargs)
    session.add(snap)
    session.flush()
    return snap


def get_latest_investor_snapshot(session: Session, market: str) -> InvestorSnapshot | None:
    return (
        session.query(InvestorSnapshot)
        .filter(InvestorSnapshot.market == market)
        .order_by(desc(InvestorSnapshot.snapshot_date))
        .first()
    )


# ── Digests ───────────────────────────────────────────────────────────────────


def get_or_create_digest(session: Session, digest_date: str) -> tuple[Digest, bool]:
    existing = session.query(Digest).filter(Digest.digest_date == digest_date).first()
    if existing:
        return existing, False
    digest = Digest(digest_date=digest_date)
    session.add(digest)
    session.flush()
    return digest, True
