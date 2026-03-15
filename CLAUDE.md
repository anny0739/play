# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`investment-news/` — Korean investment news aggregator built with Python/Streamlit/Claude API/SQLite.

## Commands

All commands run from the `investment-news/` directory.

```bash
# Run the app
streamlit run Home.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_crud.py

# Lint and format
ruff check .
black .

# One-off news fetch (without starting the full UI)
python scripts/fetch_news.py
```

## Setup

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. The SQLite DB (`investment_news.db`) is created automatically on first run by `init_db()`.

## Architecture

**Entry point:** `Home.py` — initializes the DB, starts the APScheduler, and renders the home page. Streamlit multi-page routing picks up additional pages from `app/pages/`.

**DB layer (`app/db/`):**
- `models.py` — SQLAlchemy ORM: `Topic`, `Article`, `Note`, `Digest`, `MarketSnapshot`
- `database.py` — `get_session()` context manager, `init_db()`
- `crud.py` — all DB read/write operations

**Claude API layer (`app/claude/`):**
- `aggregator.py` — **Pattern 1: Agentic Loop.** For each active `Topic`, runs a multi-turn loop with `web_search` + `web_fetch` tools (beta header required) to collect up to 5 articles. Topics are processed in parallel via `ThreadPoolExecutor(max_workers=4)`.
- `batch.py` — **Pattern 2: Batch API.** Submits unsummarized articles in bulk (up to `MAX_BATCH_SIZE=50`) and polls every 5 minutes until the batch completes.
- `analyst.py` — Per-article analysis (sentiment, notes).
- `client.py` — Singleton Anthropic client factory.
- `prompts.py` — System prompt strings.

**Scheduler (`app/scheduler/jobs.py`):** APScheduler `BackgroundScheduler` singleton (KST timezone). Registered jobs: news collection at 07:00 KST (`daily_news`), domestic market index update at 16:10 KST (`kr_market`).

**Market data (`app/market_data.py`):** Fetches KOSPI/KOSDAQ via `pykrx` and S&P 500/NASDAQ/USD-KRW via `yfinance`. Saves one `MarketSnapshot` per calendar date (upsert on `snapshot_date`).

**Config (`app/config.py`):** Central constants — `KST`, `CLAUDE_MODEL`, `DB_URL`, `MAX_BATCH_SIZE`. Model is currently `claude-sonnet-4-6`.

## Code style

- Line length: 100 (black + ruff)
- Target: Python 3.11+
- Ruff rules: E, F, I (imports), UP (pyupgrade)
