# Playwright E2E 테스트 + Claude Code 워크플로우 설계

**날짜:** 2026-03-16
**프로젝트:** investment-news (Streamlit / Python)
**목표:** 기능 개발/수정 시 E2E 테스트 케이스를 추가하고, 구현 완료 전 자동 검증하는 워크플로우 구축

---

## 배경 및 목적

현재 `tests/` 에는 DB/market data 단위 테스트만 존재하며, UI/기능 레벨의 QA 테스트가 전혀 없다. 신규 기능 추가나 수정 시 브라우저에서 실제로 동작하는지 검증하는 E2E 테스트 체계가 필요하다.

**선택 도구: Playwright (pytest-playwright)**
- Python 네이티브 — 기존 pytest 인프라와 통합
- Node.js 불필요, `pip install` 만으로 설치
- 브라우저 E2E 테스트 (Chromium headless)
- 스크린샷 자동 저장 (실패 시)

---

## 디렉토리 구조

```
investment-news/
├── tests/
│   ├── test_crud.py              # 기존 DB 단위 테스트
│   ├── test_market_data.py       # 기존 market 단위 테스트
│   ├── test_investor_data.py     # 기존 investor 단위 테스트
│   └── e2e/
│       ├── conftest.py           # 앱 자동 시작 fixture
│       ├── test_home.py          # Home 페이지 E2E
│       └── test_news.py          # 오늘의 뉴스 페이지 E2E
└── pyproject.toml                # playwright 설정 추가
```

---

## 컴포넌트 설계

### conftest.py — 앱 자동 시작 fixture

```python
import subprocess
import time
from pathlib import Path

import requests
import pytest

BASE_URL = "http://localhost:8501"
APP_DIR = Path(__file__).parents[2]  # investment-news/  (parents[0]=e2e/, [1]=tests/, [2]=investment-news/)


def _wait_for_app(timeout: int = 15) -> bool:
    """앱이 응답할 때까지 최대 timeout초 대기. 성공 시 True."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(BASE_URL, timeout=1).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="session")
def app_url():
    proc = None
    try:
        requests.get(BASE_URL, timeout=2)
    except Exception:
        proc = subprocess.Popen(
            ["streamlit", "run", "Home.py", "--server.headless=true"],
            cwd=APP_DIR,
        )
        if not _wait_for_app(timeout=15):
            proc.terminate()
            pytest.fail("Streamlit app did not start within 15 seconds")

    yield BASE_URL

    if proc is not None:
        proc.terminate()
```

- 앱이 이미 실행 중(`localhost:8501`)이면 그대로 사용
- 아니면 자동 시작 → 15초 readiness 폴링 → 실패 시 명확한 오류
- `cwd=APP_DIR` 로 pytest 실행 위치와 무관하게 안정적
- `requests` 는 기존 app 의존성에 포함되어 있음

### 초기 테스트 케이스

**test_home.py**

검증 항목:
- Home 페이지 정상 로드 (타이틀 확인)
- 시장 지수 카드 렌더링 — 정확한 레이블: `"KOSPI"`, `"KOSDAQ"`, `"S&P 500"`, `"NASDAQ"`, `"USD/KRW"`
- `"지금 뉴스 수집"` 버튼 존재 확인 (실제 버튼 레이블, `Home.py` 참고)
- `"지수만 업데이트"` 버튼 존재 확인

**test_news.py**

URL: `http://localhost:8501/오늘의_뉴스`
- Streamlit은 `1_오늘의_뉴스.py` → `/오늘의_뉴스` 로 라우팅 (숫자 prefix 제거, `.py` 제거)
- 브라우저 접근 시 한글이 퍼센트 인코딩될 수 있으므로 Playwright `page.goto()` 에는 원문 URL 사용 (Playwright가 자동 인코딩)

검증 항목:
- 페이지 정상 로드 (`"오늘의 뉴스"` 타이틀 확인)
- `"카테고리 필터"` selectbox 존재 확인 (label 기준)
  > 참고: 뉴스 페이지 상단에도 지수 카드가 있으며 레이블은 `"S&P500"` (공백 없음, Home.py의 `"S&P 500"` 과 다름). 초기 테스트 범위에서 메트릭 카드는 제외.
- selectbox 옵션 목록 확인: `"📋 전체"`, `"🇰🇷 국내주식"`, `"🇺🇸 미국주식"`, `"🏠 부동산"`, `"🌐 거시경제"`

> **주의:** 필터 선택 후 기사 목록 변화 검증은 DB에 데이터가 있어야 하므로 초기 테스트 범위에서 제외. 향후 DB 시딩 fixture 추가 후 확장.

### pyproject.toml 추가 설정

기존 `testpaths = ["tests"]` 를 유지하면서, 기본 `pytest` 실행에서 e2e를 제외한다.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--ignore=tests/e2e"   # 기본 pytest는 단위 테스트만
markers = ["e2e: end-to-end browser tests (require running app)"]
```

실행 방법:
```bash
pytest              # 단위 테스트만 (빠름, e2e 제외)
pytest tests/e2e/   # E2E만 (앱 실행 필요)
```

---

## Claude Code 워크플로우 통합

### 워크플로우

1. 기능 구현 또는 수정
2. `tests/e2e/` 에 해당 기능의 테스트 케이스 추가
3. `superpowers:verification-before-completion` skill이 완료 선언 전 `pytest tests/e2e/ -v` 자동 실행
4. 테스트 통과 시 완료 처리 / 실패 시 수정 후 재실행

### 커스텀 슬래시 커맨드: `/e2e`

`.claude/commands/e2e.md` 추가:
- 수동으로 즉시 E2E 테스트 전체 실행
- 결과 요약 출력

---

## 의존성 추가

```
# requirements.txt 에 추가
pytest-playwright
```

(`playwright` 패키지는 `pytest-playwright`의 의존성으로 자동 설치)

설치 후 브라우저 바이너리 1회 설치 필요:
```bash
playwright install chromium
```

---

## 성공 기준

- `pytest tests/e2e/` 가 로컬에서 정상 실행됨
- 앱이 꺼져 있어도 자동 시작 후 테스트 실행됨
- 기존 `pytest` (단위 테스트)는 영향 없이 그대로 동작
- 기능 추가 시 E2E 테스트 케이스가 함께 커밋됨
- Claude가 구현 완료 선언 전 E2E 테스트 통과를 확인함
