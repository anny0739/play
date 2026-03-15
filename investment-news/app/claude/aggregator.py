"""패턴 1+4: Agentic Loop + 주제별 서브인보케이션 (ThreadPoolExecutor 병렬)."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from app.claude.client import get_client
from app.claude.prompts import AGGREGATOR_SYSTEM
from app.config import CLAUDE_MODEL
from app.db.crud import upsert_article
from app.db.database import get_session
from app.db.models import Topic

logger = logging.getLogger(__name__)

# web-search 베타 헤더 (tool type과 버전 일치)
_WEB_SEARCH_BETA = "web-search-2025-03-05"

_TOOLS = [
    {"type": "web_search_20250305", "name": "web_search"},
]


def _fetch_for_topic(topic: Topic) -> list[dict]:
    """단일 토픽에 대해 server-side web_search 호출 → 기사 리스트 반환.

    web_search_20250305 는 서버 사이드 툴이므로 API가 자동으로 검색을 실행하고
    end_turn 으로 최종 응답을 반환한다. 별도 agentic loop 불필요.
    """
    client = get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=AGGREGATOR_SYSTEM,
        tools=_TOOLS,
        messages=[
            {
                "role": "user",
                "content": (
                    f"다음 검색어로 오늘(또는 최근 2일 이내)의 재테크 뉴스를 수집해 주세요: "
                    f'"{topic.search_query}"\n'
                    "최대 5개 기사의 URL·제목·출처·발행일·내용을 JSON으로 반환하세요."
                ),
            }
        ],
        extra_headers={"anthropic-beta": _WEB_SEARCH_BETA},
    )

    for block in response.content:
        if block.type == "text":
            return _parse_articles_json(block.text)
    return []


def _parse_articles_json(text: str) -> list[dict]:
    """Claude 응답 텍스트에서 JSON 배열 파싱."""
    text = text.strip()
    # JSON 블록 추출 (```json ... ``` 제거)
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("["):
                text = part
                break

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        logger.warning("JSON 파싱 실패: %s", text[:200])
    return []


def fetch_and_save_all(topics: list[Topic]) -> dict[str, int]:
    """
    모든 활성 토픽에 대해 병렬로 뉴스 수집 후 DB 저장.
    반환: {category: 신규_저장_건수}
    """
    counts: dict[str, int] = {}
    today = date.today().isoformat()

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_topic = {executor.submit(_fetch_for_topic, t): t for t in topics}
        for future in as_completed(future_to_topic):
            topic = future_to_topic[future]
            try:
                articles = future.result()
                saved = 0
                with get_session() as session:
                    for art in articles:
                        url = art.get("url", "").strip()
                        title = art.get("title", "").strip()
                        if not url or not title:
                            continue
                        _, created = upsert_article(
                            session,
                            topic_id=topic.id,
                            url=url,
                            title=title,
                            source=art.get("source", ""),
                            published_at=None,
                            raw_content=art.get("content", ""),
                        )
                        if created:
                            saved += 1
                counts[topic.category] = counts.get(topic.category, 0) + saved
                logger.info("토픽 '%s': %d건 신규 저장", topic.name, saved)
            except Exception as exc:
                logger.error("토픽 '%s' 수집 실패: %s", topic.name, exc)

    return counts
