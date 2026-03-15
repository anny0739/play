---
name: investment-news-context
description: >
  재테크 뉴스 애그리게이터 프로젝트 컨텍스트.
  investment-news/ 디렉토리 파일 작업 시 자동 활성화.
user-invocable: false
---

# 재테크 뉴스 애그리게이터 — 프로젝트 컨텍스트

## 디렉토리 구조
```
investment-news/
├── Home.py                         # Streamlit 엔트리포인트
├── app/
│   ├── config.py                   # 환경변수, KST 타임존, 모델 상수
│   ├── db/
│   │   ├── models.py               # SQLAlchemy ORM (Topic/Article/Note/Digest/MarketSnapshot)
│   │   ├── database.py             # 엔진, get_session(), init_db()
│   │   └── crud.py                 # DB 헬퍼
│   ├── claude/
│   │   ├── client.py               # Anthropic 클라이언트 싱글톤
│   │   ├── prompts.py              # 모든 프롬프트 템플릿
│   │   ├── aggregator.py           # [패턴1+4] Agentic loop 뉴스 수집
│   │   ├── batch.py                # [패턴2] Batch API 요약
│   │   └── analyst.py              # [패턴3] Streaming + Adaptive Thinking
│   ├── scheduler/jobs.py           # APScheduler (07:00 KST 수집, 16:10 KST 지수)
│   ├── market_data.py              # pykrx + yfinance 지수 수집
│   ├── notifier.py                 # macOS osascript 알림
│   └── pages/
│       ├── 1_오늘의_뉴스.py
│       ├── 2_내_메모.py             # Phase 2
│       ├── 3_AI_분석.py             # Phase 2 (streaming thinking)
│       └── 4_공유하기.py            # Phase 3
```

## Claude API 4가지 패턴

### 패턴 1+4: Agentic Loop (aggregator.py)
- 모델: `claude-sonnet-4-6`
- 베타 헤더: `"anthropic-beta": "web-search-2025-03-05"`
- 툴: `web_search_20260209`, `web_fetch_20260209`
- ThreadPoolExecutor로 카테고리별 병렬 실행

### 패턴 2: Batch API (batch.py)
- `client.messages.batches.create(requests=[...])`
- `custom_id: "article-{id}"` 매핑
- 5분 간격 폴링, 완료 시 summary DB 저장

### 패턴 3: Streaming + Adaptive Thinking (analyst.py)
- 모델: `claude-sonnet-4-6`
- `thinking={"type": "adaptive"}`
- 베타 헤더: `"interleaved-thinking-2025-05-14"`
- `content_block_delta` 이벤트로 thinking/text 스트리밍

## DB 스키마 핵심
- `topics`: category = stock_kr | stock_us | realestate | macro
- `articles`: url(unique), summary(batch 결과), raw_content
- `notes`: sentiment = bullish | bearish | neutral
- `digests`: share_token(UUID), is_published
- `market_snapshots`: kospi, kosdaq, sp500, nasdaq, usd_krw

## 프롬프트
모든 프롬프트는 `app/claude/prompts.py`에만 정의.
