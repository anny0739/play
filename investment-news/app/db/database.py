from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import DB_URL
from app.db.models import Base, Topic

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_topics()


def _seed_topics():
    with get_session() as session:
        if session.query(Topic).count() > 0:
            return
        seeds = [
            Topic(name="삼성전자 주가", category="stock_kr", search_query="삼성전자 주가 뉴스"),
            Topic(name="코스피 시황", category="stock_kr", search_query="코스피 시황 오늘"),
            Topic(name="S&P500 나스닥", category="stock_us", search_query="S&P500 나스닥 시황"),
            Topic(name="애플 엔비디아 주가", category="stock_us", search_query="애플 엔비디아 주가 뉴스"),
            Topic(name="서울 아파트 시세", category="realestate", search_query="서울 아파트 시세 뉴스"),
            Topic(name="부동산 정책", category="realestate", search_query="부동산 정책 뉴스"),
            Topic(name="한국은행 금리", category="macro", search_query="한국은행 기준금리 뉴스"),
            Topic(name="달러원 환율", category="macro", search_query="달러원 환율 오늘"),
            Topic(name="미 연준 FOMC", category="macro", search_query="미국 연준 FOMC 금리"),
        ]
        session.add_all(seeds)
        session.commit()


@contextmanager
def get_session():
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
