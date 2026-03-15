# 재테크 뉴스 애그리게이터 - 구현 플랜

## Context

백엔드 개발자가 Claude API 학습을 겸해서, 국내외 주식·부동산·거시경제 뉴스를 자동으로 수집하고 개인 메모를 남기며 타인과 공유할 수 있는 로컬 앱을 만든다. Python + Streamlit 기반 경량 앱, Claude API의 4가지 핵심 패턴을 직접 써볼 수 있는 실습 프로젝트.

**관심 주제:** 국내 주식(KOSPI/KOSDAQ), 미국 주식(S&P500/나스닥), 부동산(서울/수도권), 거시경제/금리/환율
**UI 언어:** 한국어
**배포:** Phase 3에서 결정 (Streamlit Cloud or 로컬 export)

### 유사 서비스 분석 및 차별점

시장 조사 결과 주요 경쟁 서비스:
- **Byul (별)**: 한국 AI 뉴스 앱, 감성 지수(공포/탐욕 인덱스), 월정액 유료
- **DinoDigest**: 포트폴리오 기반 맞춤 뉴스 요약, 감성 분석, 미국 주식 특화
- **auto-news (GitHub)**: 뉴스+개인 노트+AI 오픈소스 프로젝트 (가장 유사한 레퍼런스)
- **StockInfo7**: 국내 주식 뉴스 필터링 특화, AI 분석 없음

**우리 앱의 차별점 (시장에 없는 기능):**
1. **뉴스+개인 메모 통합** — 기사 단위 메모, 투자 의견 기록 (어떤 서비스도 없음)
2. **국내 + 미국 + 부동산 + 거시경제 통합** — 하나의 앱에서 모두 커버하는 서비스 없음
3. **개인 다이제스트 공유** — 내 투자 관점을 정리해 타인에게 공유하는 기능 없음
4. **감성 분석 (bullish/bearish/neutral)** — Byul처럼 각 기사/포트폴리오 단위 감성 메모

**레퍼런스 UX 참고:**
- DinoDigest: 기사 카드 레이아웃, 주제별 섹션 구분
- Byul: 지수 현황 바, 실시간 감성 인디케이터

---

## 디렉토리 구조

```
/Users/areum.k/playground/play/investment-news/
├── Home.py                         # Streamlit 엔트리포인트, 스케줄러 부트스트랩
├── requirements.txt
├── .env.example
├── .gitignore
├── app/
│   ├── config.py                   # 환경변수 로드, KST 타임존, 모델 상수
│   ├── db/
│   │   ├── models.py               # SQLAlchemy ORM 모델 (Topic/Article/Note/Digest)
│   │   ├── database.py             # 엔진, get_session(), init_db()
│   │   └── crud.py                 # DB 읽기/쓰기 헬퍼
│   ├── claude/
│   │   ├── client.py               # Anthropic 클라이언트 싱글톤
│   │   ├── prompts.py              # 모든 프롬프트 템플릿 (튜닝 허브)
│   │   ├── aggregator.py           # [패턴1+4] Agentic loop + 주제별 서브인보케이션
│   │   ├── batch.py                # [패턴2] Batch API submit/poll/parse
│   │   └── analyst.py              # [패턴3] Streaming + Extended Thinking
│   ├── scheduler/
│   │   └── jobs.py                 # APScheduler, daily_digest_job() 07:00 KST
│   ├── market_data.py              # pykrx(국내 지수) + yfinance(미국 지수) 수집
│   ├── notifier.py                 # macOS 데스크탑 알림 (osascript)
│   └── pages/
│       ├── 1_오늘의_뉴스.py          # 오늘 수집된 뉴스 피드 + 메모 추가
│       ├── 2_내_메모.py             # 메모 목록/수정/삭제
│       ├── 3_AI_분석.py             # 스트리밍 + thinking 분석 on-demand
│       └── 4_공유하기.py            # Digest 발행 및 공유 링크 생성
```

---

## DB 스키마 (models.py)

| 테이블 | 핵심 컬럼 |
|--------|----------|
| `topics` | id, name, category(stock_kr/stock_us/realestate/macro), search_query, is_active |
| `articles` | id, topic_id(FK), url(unique), title, source, published_at, raw_content, summary, batch_job_id, fetched_at |
| `notes` | id, article_id(FK), content, sentiment(bullish/bearish/neutral), created_at, updated_at |
| `digests` | id, digest_date(unique), summary_html, article_ids(JSON), share_token(UUID, nullable), is_published |
| `market_snapshots` | id, snapshot_date(unique), kospi, kosdaq, sp500, nasdaq, usd_krw, fetched_at |

**기본 토픽 시드 데이터 (init_db 시 자동 삽입):**
- `삼성전자 주가` (stock_kr), `코스피 시황` (stock_kr)
- `S&P500 나스닥` (stock_us), `애플 엔비디아 주가` (stock_us)
- `서울 아파트 시세` (realestate), `부동산 정책` (realestate)
- `한국은행 금리` (macro), `달러원 환율` (macro), `미 연준 FOMC` (macro)

---

## Claude API 패턴 4가지

### 패턴 1+4: Agentic Loop + 서브인보케이션 (`aggregator.py`)
- 주제 그룹(stock_kr / stock_us / realestate / macro)별로 **독립된 messages.create 호출** (ThreadPoolExecutor 병렬)
- 각 호출: `web_search_20260209` → `web_fetch_20260209` → 구조화된 JSON 반환 agentic loop
- 베타 헤더: `"anthropic-beta": "web-search-2025-03-05"`
- 모델: `claude-sonnet-4-6`

### 패턴 2: Batch API (`batch.py`)
- 수집 완료 후 미요약 articles 전체를 한 번에 배치 제출 (최대 50개)
- `custom_id: "article-{id}"` → 결과 매핑
- 5분 간격 폴링, 완료 시 DB summary 업데이트
- 비용: 개별 호출 대비 50% 절감

### 패턴 3: Streaming + Extended Thinking (`analyst.py`)
- 모델: `claude-sonnet-4-6`, 베타: `"interleaved-thinking-2025-05-14"`
- `budget_tokens` 슬라이더 (1,000~10,000) 제공
- thinking_delta → `st.expander("Claude의 사고 과정")` 실시간 스트리밍
- text_delta → `st.empty()` markdown 실시간 렌더링

### 시장 지수 데이터 (`market_data.py`)
- **국내 지수** (KOSPI, KOSDAQ): `pykrx` 라이브러리 — API 키 불필요, KRX 공식 데이터
- **미국 지수** (S&P500, NASDAQ): `yfinance` 라이브러리 — API 키 불필요
- **환율** (USD/KRW): yfinance `"KRW=X"` 티커
- 수집 시점: 국내 장 마감 후 16:00 KST (pykrx), 미국 장 마감 후 별도 스케줄 또는 07:00 KST 전일 종가
- `market_snapshots` 테이블에 저장, 홈 화면과 분석 페이지에 지수 요약 표시
- **추가 의존성**: `pykrx>=1.0.47`, `yfinance>=0.2.40`

### 프롬프트 관리
- **모든 프롬프트는 `prompts.py` 한 곳에**: `AGGREGATOR_SYSTEM`, `SUMMARIZE_PROMPT`, `ANALYSIS_PROMPT_TEMPLATE`

---

## 3단계 구현 순서

### Phase 1: MVP (자동 수집 + 알림 + 기본 UI)
순서대로 생성:
1. `requirements.txt`, `.env.example`, `.gitignore`
2. `app/config.py`
3. `app/db/models.py` → `app/db/database.py` → `app/db/crud.py`
4. `app/claude/client.py` → `app/claude/prompts.py` → `app/claude/aggregator.py`
5. `app/market_data.py` — pykrx(KOSPI/KOSDAQ) + yfinance(S&P500/NASDAQ/USD-KRW) 수집
6. `app/notifier.py` — `osascript`로 macOS 알림 발송, 카테고리별 건수 + 지수 요약 표시
7. `app/scheduler/jobs.py` — APScheduler jobs: 07:00 KST 뉴스수집, 16:10 KST 국내지수, 07:00 KST 미국전일종가
8. `Home.py` — 스케줄러 부트스트랩 + 수동 "지금 수집" 버튼 + 지수 현황 카드 + 마지막 수집 시각
9. `app/pages/1_오늘의_뉴스.py` — 오늘 수집된 뉴스 카드 목록 + 상단 지수 스냅샷 바

**알림 내용 (`notifier.py`):**
```
제목: 재테크 뉴스 수집 완료
본문: 오늘의 뉴스 {total}건 수집됨
      국내주식 {n} | 미주식 {n} | 부동산 {n} | 거시경제 {n}
```
`subprocess.run(["osascript", "-e", f'display notification "{body}" with title "{title}"'])`

**완료 기준:** 앱 시작 시 스케줄러 자동 시작, 07:00 KST에 자동 수집 + macOS 알림 팝업, UI에서 뉴스 목록 확인

### Phase 2: 전체 기능 (메모 + Batch 요약 + 스트리밍 분석)
순서대로 생성/확장:
1. `app/claude/batch.py`
2. `app/db/crud.py` 확장 (노트 CRUD, digest 생성)
3. `1_오늘의_뉴스.py` 확장 (batch summary 표시, `st.dialog` 메모 추가)
4. `app/pages/2_내_메모.py`
5. `app/claude/analyst.py` → `app/pages/3_AI_분석.py`

**완료 기준:** Batch API로 뉴스 요약 자동 생성, 메모 저장/수정/삭제, streaming thinking 분석 작동

### Phase 3: 공유 기능 (Phase 2 완료 후 결정)
- 옵션 A: Streamlit Cloud + Supabase Postgres (외부 링크 공유)
- 옵션 B: 로컬 HTML export (파일 공유)
- `4_공유하기.py`, `share_token` 생성, `?token=` 쿼리 파라미터 라우팅

---

## 코드 품질 관리

- **포매터**: `black` (PEP8 준수 자동 포매팅)
- **린터**: `ruff` (flake8/isort 대체, 빠름)
- **테스트**: `pytest` — DB/CRUD 레이어 유닛 테스트 (Claude API 호출은 mock 처리)
- **설정**: `pyproject.toml`에 black/ruff/pytest 설정 통합
- **테스트 파일 위치**: `tests/` 디렉토리, `test_crud.py`, `test_market_data.py` 우선

## requirements.txt 주요 의존성

```
# UI
streamlit>=1.35.0

# Claude API
anthropic>=0.49.0

# DB
sqlalchemy>=2.0.0

# Scheduler
apscheduler>=3.10.0

# Market data (API 키 불필요)
pykrx>=1.0.47        # 국내 KRX 지수 (KOSPI/KOSDAQ)
yfinance>=0.2.40     # 미국 지수 + 환율

# Utilities
python-dotenv>=1.0.0
pytz>=2024.1

# Dev/Quality
black>=24.0.0
ruff>=0.4.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

---

## 검증 방법

1. **Phase 1**: `streamlit run Home.py` 실행 → 스케줄러 시작 로그 확인 → "지금 수집" 클릭 → macOS 알림 팝업(카테고리별 건수 + 지수) → 홈에 지수 카드 표시 → 1_오늘의_뉴스 뉴스 목록 확인
2. **Phase 2**: Batch 요약 텍스트 뉴스 카드에 표시 확인, 메모 저장/수정/삭제, 3_AI_분석 페이지에서 thinking 스트리밍 확인
3. **Phase 3**: `?token=<uuid>` URL로 비로그인 접근 → digest 내용 표시 확인

---

## 활용할 Claude Code 기능 (학습 포인트)

### 기존 내장 스킬
| 스킬 | 언제 사용 |
|------|-----------|
| `/plan` | 각 Phase 시작 전 구현 계획 수립 |
| `/claude-api` | `aggregator.py`, `batch.py`, `analyst.py` 작성 시 자동 트리거 |
| `/simplify` | 각 Phase 완료 후 코드 품질 리뷰 |

### 프로젝트 전용 커스텀 스킬 (Phase 1에 함께 생성)

**1. `investment-news-context` (자동 호출용)**
- 경로: `.claude/skills/investment-news-context/SKILL.md`
- 역할: Claude가 이 프로젝트 작업 시 아키텍처 컨텍스트를 자동 로드
- `user-invocable: false` — Claude가 investment-news 코드 파일 작업 시 자동 활성화
- SKILL.md 내용: 4가지 Claude API 패턴, DB 스키마, 파일 구조 요약

```yaml
---
name: investment-news-context
description: >
  재테크 뉴스 애그리게이터 프로젝트 컨텍스트.
  investment-news/ 디렉토리 파일 작업 시 자동 활성화.
user-invocable: false
---
# 프로젝트 컨텍스트
[plan 내용 요약 + 핵심 파일 경로]
```

**2. `/fetch-news` (수동 호출용)**
- 경로: `.claude/skills/fetch-news/SKILL.md`
- 역할: `/fetch-news` 명령으로 뉴스 수집을 즉시 트리거
- `allowed-tools: Bash` — Python 스크립트 직접 실행

```yaml
---
name: fetch-news
description: 재테크 뉴스를 즉시 수집합니다
argument-hint: "[topic: all | stock_kr | stock_us | realestate | macro]"
allowed-tools: Bash
---
`python investment-news/scripts/fetch_news.py $ARGUMENTS` 실행
```

### 기타 Claude Code 패턴
- **Subagent (Plan/Explore)**: 각 Phase 구현 전 아키텍처 검토
- **Parallel tool calls**: Phase 별로 독립적인 파일 생성 병렬 처리
- **Memory**: 프로젝트 진행 상황 자동 기록
