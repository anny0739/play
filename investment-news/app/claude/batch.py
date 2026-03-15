"""패턴 2: Batch API — 미요약 기사 일괄 요약."""

import logging
import time

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from app.claude.client import get_client
from app.claude.prompts import SUMMARIZE_PROMPT
from app.config import CLAUDE_BATCH_MODEL, MAX_BATCH_SIZE
from app.db.crud import get_articles_without_summary, update_article_summary
from app.db.database import get_session

logger = logging.getLogger(__name__)

POLL_INTERVAL = 300  # 5분


def submit_summary_batch() -> str | None:
    """미요약 기사를 Batch API에 제출. batch_id 반환."""
    client = get_client()

    with get_session() as session:
        articles = get_articles_without_summary(session, limit=MAX_BATCH_SIZE)
        if not articles:
            logger.info("요약할 기사 없음.")
            return None

        requests = [
            Request(
                custom_id=f"article-{art.id}",
                params=MessageCreateParamsNonStreaming(
                    model=CLAUDE_BATCH_MODEL,
                    max_tokens=512,
                    messages=[
                        {
                            "role": "user",
                            "content": SUMMARIZE_PROMPT.format(
                                title=art.title,
                                content=art.raw_content or art.title,
                            ),
                        }
                    ],
                ),
            )
            for art in articles
        ]

    batch = client.messages.batches.create(requests=requests)
    logger.info("Batch 제출 완료: %s (%d건)", batch.id, len(requests))
    return batch.id


def poll_and_save(batch_id: str):
    """Batch 완료 대기 후 요약 DB 저장."""
    client = get_client()

    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            break
        logger.info(
            "Batch %s 처리 중... (남은: %d)", batch_id, batch.request_counts.processing
        )
        time.sleep(POLL_INTERVAL)

    saved = 0
    for result in client.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            continue
        custom_id = result.custom_id  # "article-{id}"
        article_id = int(custom_id.split("-")[1])
        text_blocks = [b for b in result.result.message.content if b.type == "text"]
        if not text_blocks:
            continue
        summary = text_blocks[0].text.strip()
        with get_session() as session:
            update_article_summary(session, article_id, summary)
        saved += 1

    logger.info("Batch %s 완료: %d건 요약 저장", batch_id, saved)
