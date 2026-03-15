"""APScheduler 정기 작업 정의."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import KST

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def daily_news_job():
    """07:00 KST — RSS 뉴스 수집 + macOS 알림."""
    logger.info("[스케줄러] RSS 뉴스 수집 시작...")
    try:
        from app.notifier import notify_fetch_complete
        from app.rss_collector import fetch_rss_articles

        counts = fetch_rss_articles()
        notify_fetch_complete(counts)
        logger.info("[스케줄러] RSS 뉴스 수집 완료: %s", counts)
    except Exception as e:
        logger.error("[스케줄러] 뉴스 수집 실패: %s", e)


def kr_market_job():
    """16:10 KST — 국내 지수 수집."""
    logger.info("[스케줄러] 국내 지수 수집...")
    try:
        from app.market_data import fetch_and_save_market_data

        fetch_and_save_market_data()
    except Exception as e:
        logger.error("[스케줄러] 국내 지수 수집 실패: %s", e)


def investor_data_job():
    """16:15 KST — 투자자별 매매 현황 수집."""
    logger.info("[스케줄러] 투자자 매매 데이터 수집...")
    try:
        from app.investor_data import fetch_and_save_investor_data

        fetch_and_save_investor_data()
    except Exception as e:
        logger.error("[스케줄러] 투자자 데이터 수집 실패: %s", e)


def get_scheduler() -> BackgroundScheduler:
    """싱글톤 스케줄러 반환."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=KST)
        # 07:00 KST 뉴스 수집
        _scheduler.add_job(
            daily_news_job,
            CronTrigger(hour=7, minute=0, timezone=KST),
            id="daily_news",
            replace_existing=True,
        )
        # 16:10 KST 국내 지수
        _scheduler.add_job(
            kr_market_job,
            CronTrigger(hour=16, minute=10, timezone=KST),
            id="kr_market",
            replace_existing=True,
        )
        _scheduler.add_job(
            investor_data_job,
            IntervalTrigger(hours=1),
            id="investor_data",
            replace_existing=True,
        )
    return _scheduler


def start_scheduler():
    """스케줄러 시작 (이미 실행 중이면 스킵)."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("스케줄러 시작됨. 등록 작업: %s", [j.id for j in scheduler.get_jobs()])


def stop_scheduler():
    """스케줄러 정지."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("스케줄러 정지됨.")
