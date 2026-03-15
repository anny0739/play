"""RSS 피드 기반 뉴스 수집기 — Claude API 크레딧 불필요."""

import logging

import feedparser

from app.db.crud import upsert_article
from app.db.database import get_session

logger = logging.getLogger(__name__)

# 카테고리 → RSS 피드 목록 매핑
RSS_FEEDS: dict[str, list[dict[str, str]]] = {
    "stock_kr": [
        {"name": "한경 증권", "url": "https://www.hankyung.com/feed/finance"},
        {"name": "매경 증권", "url": "https://www.mk.co.kr/rss/30100041/"},
    ],
    "stock_us": [
        {"name": "한경 국제", "url": "https://www.hankyung.com/feed/international"},
        {"name": "한경 증권", "url": "https://www.hankyung.com/feed/finance"},
        {"name": "매경 증권", "url": "https://www.mk.co.kr/rss/30100041/"},
    ],
    "realestate": [
        {"name": "한경 부동산", "url": "https://www.hankyung.com/feed/realestate"},
    ],
    "macro": [
        {"name": "한경 경제", "url": "https://www.hankyung.com/feed/economy"},
        {"name": "연합 경제", "url": "https://www.yna.co.kr/rss/economy.xml"},
        {
            "name": "연합뉴스TV 경제",
            "url": "https://www.yonhapnewstv.co.kr/category/news/economy/feed",
        },
    ],
}

# 카테고리별 키워드 필터 (해당 키워드 중 하나라도 제목에 포함되면 수집)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "stock_kr": [
        "코스피",
        "코스닥",
        "주가",
        "증시",
        "주식",
        "상장",
        "IPO",
        "배당",
        "삼성",
        "SK",
        "LG",
    ],
    "stock_us": [
        "나스닥",
        "S&P",
        "다우",
        "월가",
        "미국 증시",
        "미증시",
        "미 증시",
        "애플",
        "엔비디아",
        "테슬라",
        "마이크로소프트",
        "AI 반도체",
        "뉴욕증시",
        "뉴욕 증시",
        "필라델피아",
        "연준",
        "Fed",
    ],
    "realestate": ["아파트", "부동산", "분양", "전세", "월세", "주택", "재건축", "재개발"],
    "macro": ["금리", "환율", "달러", "물가", "GDP", "연준", "한은", "기준금리", "인플레"],
}


def _matches_category(title: str, category: str) -> bool:
    """제목이 카테고리 키워드와 매치되는지 확인."""
    keywords = CATEGORY_KEYWORDS.get(category)
    if keywords is None:
        return True
    return any(kw in title for kw in keywords)


def fetch_rss_articles(
    category: str | None = None,
    max_per_feed: int = 10,
) -> dict[str, int]:
    """RSS 피드에서 뉴스를 수집하여 DB에 저장.

    Args:
        category: 특정 카테고리만 수집. None이면 전체.
        max_per_feed: 피드당 최대 수집 기사 수.

    Returns:
        {category: 신규_저장_건수}
    """
    counts: dict[str, int] = {}

    categories = (
        {category: RSS_FEEDS[category]} if category and category in RSS_FEEDS else RSS_FEEDS
    )

    for cat, feeds in categories.items():
        saved = 0
        for feed_info in feeds:
            feed_name = feed_info["name"]
            feed_url = feed_info["url"]
            try:
                parsed = feedparser.parse(feed_url)
                entries = parsed.entries[:max_per_feed]
                logger.info("RSS [%s] %d건 파싱", feed_name, len(entries))

                with get_session() as session:
                    # 카테고리에 해당하는 첫 번째 토픽 ID 찾기
                    from app.db.models import Topic

                    topic = session.query(Topic).filter(Topic.category == cat).first()
                    if topic is None:
                        logger.warning("토픽 없음: category=%s", cat)
                        continue
                    topic_id = topic.id

                    for entry in entries:
                        title = entry.get("title", "").strip()
                        link = entry.get("link", "").strip()
                        if not title or not link:
                            continue

                        if not _matches_category(title, cat):
                            continue

                        summary = entry.get("summary", "")
                        # HTML 태그 제거 (간단한 방법)
                        if "<" in summary:
                            from html.parser import HTMLParser
                            from io import StringIO

                            class _Strip(HTMLParser):
                                def __init__(self):
                                    super().__init__()
                                    self._buf = StringIO()

                                def handle_data(self, d):
                                    self._buf.write(d)

                                def get_text(self):
                                    return self._buf.getvalue()

                            s = _Strip()
                            s.feed(summary)
                            summary = s.get_text()

                        _, created = upsert_article(
                            session,
                            topic_id=topic_id,
                            url=link,
                            title=title,
                            source=feed_name,
                            published_at=None,
                            raw_content=summary[:2000] if summary else "",
                        )
                        if created:
                            saved += 1

            except Exception as e:
                logger.error("RSS 수집 오류 [%s]: %s", feed_name, e)

        counts[cat] = saved
        if saved:
            logger.info("카테고리 '%s': RSS %d건 신규 저장", cat, saved)

    return counts
