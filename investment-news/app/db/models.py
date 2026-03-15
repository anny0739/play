import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # stock_kr/stock_us/realestate/macro
    search_query: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    articles: Mapped[list["Article"]] = relationship("Article", back_populates="topic")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_job_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    topic: Mapped["Topic"] = relationship("Topic", back_populates="articles")
    notes: Mapped[list["Note"]] = relationship("Note", back_populates="article")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)  # bullish/bearish/neutral
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    article: Mapped["Article"] = relationship("Article", back_populates="notes")


class Digest(Base):
    __tablename__ = "digests"
    __table_args__ = (UniqueConstraint("digest_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    digest_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    summary_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    _article_ids: Mapped[str | None] = mapped_column("article_ids", Text, nullable=True)
    share_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    @property
    def article_ids(self) -> list[int]:
        if self._article_ids:
            return json.loads(self._article_ids)
        return []

    @article_ids.setter
    def article_ids(self, value: list[int]):
        self._article_ids = json.dumps(value)

    def generate_share_token(self):
        self.share_token = str(uuid.uuid4())


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    kospi: Mapped[float | None] = mapped_column(Float, nullable=True)
    kosdaq: Mapped[float | None] = mapped_column(Float, nullable=True)
    sp500: Mapped[float | None] = mapped_column(Float, nullable=True)
    nasdaq: Mapped[float | None] = mapped_column(Float, nullable=True)
    usd_krw: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class InvestorSnapshot(Base):
    __tablename__ = "investor_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_date", "market"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # 'KOSPI' or 'KOSDAQ'
    foreign_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    foreign_sell: Mapped[float | None] = mapped_column(Float, nullable=True)
    foreign_net: Mapped[float | None] = mapped_column(Float, nullable=True)
    inst_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    inst_sell: Mapped[float | None] = mapped_column(Float, nullable=True)
    inst_net: Mapped[float | None] = mapped_column(Float, nullable=True)
    indiv_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    indiv_sell: Mapped[float | None] = mapped_column(Float, nullable=True)
    indiv_net: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
