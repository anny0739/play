#!/usr/bin/env python3
"""수동 뉴스 수집 스크립트. /fetch-news 스킬에서 호출."""

import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 프로젝트 루트를 sys.path에 추가
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    category_filter = sys.argv[1] if len(sys.argv) > 1 else "all"

    from app.db.database import init_db, get_session
    from app.db.crud import get_active_topics, get_topics_by_category
    from app.claude.aggregator import fetch_and_save_all
    from app.market_data import fetch_and_save_market_data
    from app.notifier import notify_fetch_complete

    init_db()

    with get_session() as session:
        if category_filter == "all":
            topics = get_active_topics(session)
        else:
            topics = get_topics_by_category(session, category_filter)

    if not topics:
        print(f"토픽 없음: category={category_filter}")
        return

    print(f"수집 시작: {len(topics)}개 토픽 (filter={category_filter})")
    counts = fetch_and_save_all(topics)
    market = fetch_and_save_market_data()
    notify_fetch_complete(counts, market)

    total = sum(counts.values())
    print(f"\n✅ 완료: 총 {total}건 수집")
    for cat, n in counts.items():
        print(f"  {cat}: {n}건")


if __name__ == "__main__":
    main()
