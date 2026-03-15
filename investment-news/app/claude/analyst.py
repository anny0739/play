"""패턴 3: Streaming + Extended Thinking (Adaptive) — on-demand 분석."""

import logging
from collections.abc import Generator

from app.claude.client import get_client
from app.claude.prompts import ANALYSIS_PROMPT_TEMPLATE
from app.config import CLAUDE_MODEL
from app.db.models import Article

logger = logging.getLogger(__name__)

# Interleaved thinking 베타 헤더
_THINKING_BETA = "interleaved-thinking-2025-05-14"


def build_news_context(articles: list[Article]) -> str:
    """기사 목록을 분석 프롬프트용 텍스트로 변환."""
    lines = []
    for i, art in enumerate(articles, 1):
        lines.append(f"{i}. [{art.topic.category if art.topic else '기타'}] {art.title}")
        if art.summary:
            lines.append(f"   요약: {art.summary}")
        elif art.raw_content:
            lines.append(f"   내용: {art.raw_content[:150]}...")
    return "\n".join(lines)


def stream_analysis(
    articles: list[Article],
) -> Generator[tuple[str, str], None, None]:
    """
    스트리밍으로 thinking + text 델타를 순서대로 yield.
    Yields: (block_type, delta_text)  — block_type: "thinking" | "text"
    """
    client = get_client()
    news_context = build_news_context(articles)
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(news_context=news_context)

    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": _THINKING_BETA},
    ) as stream:
        current_block_type: str | None = None

        for event in stream:
            event_type = event.type

            if event_type == "content_block_start":
                block = event.content_block
                current_block_type = block.type  # "thinking" or "text"

            elif event_type == "content_block_delta":
                delta = event.delta
                if delta.type == "thinking_delta" and current_block_type == "thinking":
                    yield "thinking", delta.thinking
                elif delta.type == "text_delta" and current_block_type == "text":
                    yield "text", delta.text

            elif event_type == "content_block_stop":
                current_block_type = None
