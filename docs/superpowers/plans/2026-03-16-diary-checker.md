# Diary Checker Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notion에서 오늘 일기를 자동으로 가져와 분량(900자/200단어)을 체크하고, Band에 쉽게 게시할 수 있는 Streamlit 앱을 만든다.

**Architecture:** `diary/counter.py`는 순수 카운팅 함수, `diary/notion.py`는 Notion API 클라이언트, `app.py`는 Streamlit UI를 담당한다. DB 없음.

**Tech Stack:** Python 3.11+, Streamlit, notion-client, pyperclip, python-dotenv, pytest

---

## Chunk 1: 프로젝트 셋업 + 카운터

### Task 1: 디렉토리 및 의존성 셋업

**Files:**
- Create: `diary-checker/requirements.txt`
- Create: `diary-checker/.env.example`
- Create: `diary-checker/diary/__init__.py`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p diary-checker/diary diary-checker/tests
```

- [ ] **Step 2: requirements.txt 작성**

```
streamlit>=1.32
notion-client>=2.0
pyperclip
python-dotenv
pytest
```

- [ ] **Step 3: .env.example 작성**

```
NOTION_TOKEN=ntn_여기에_토큰_입력
NOTION_DIARY_PARENT_ID=2dbad192-0f86-80b7-bb55-e9614da3413a
```

- [ ] **Step 4: .env 파일 생성 (실제 값)**

```bash
cp diary-checker/.env.example diary-checker/.env
# .env 파일에 실제 NOTION_TOKEN 입력
```

- [ ] **Step 5: 의존성 설치**

```bash
cd diary-checker
pip install -r requirements.txt
```

- [ ] **Step 6: `diary/__init__.py` 생성 (빈 파일)**

- [ ] **Step 7: `pytest.ini` 작성 — pythonpath 설정 (tests/__init__.py 불필요)**

```ini
# diary-checker/pytest.ini
[pytest]
pythonpath = .
```

- [ ] **Step 8: .gitignore 확인 — 프로젝트 루트 .gitignore에 .env 포함 여부 확인**

```bash
# 프로젝트 루트에서 실행
grep "^\.env$" .gitignore || echo ".env" >> .gitignore
```

- [ ] **Step 9: Commit**

```bash
git add diary-checker/requirements.txt diary-checker/.env.example diary-checker/diary/__init__.py diary-checker/pytest.ini
git commit -m "feat: scaffold diary-checker project"
```

---

### Task 2: 카운팅 모듈 (TDD)

**Files:**
- Create: `diary-checker/diary/counter.py`
- Create: `diary-checker/tests/test_counter.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
# diary-checker/tests/test_counter.py
import pytest
from diary.counter import count, CHAR_THRESHOLD, WORD_THRESHOLD


def test_empty_string():
    r = count("")
    assert r.char_count == 0
    assert r.word_count == 0
    assert r.goal_met is False


def test_whitespace_only():
    r = count("   \n\t  ")
    assert r.word_count == 0
    assert r.goal_met is False


def test_char_goal_exactly_met():
    text = "가" * CHAR_THRESHOLD  # 정확히 900자
    r = count(text)
    assert r.char_goal_met is True
    assert r.goal_met is True
    assert r.chars_remaining == 0


def test_char_goal_one_short():
    text = "가" * (CHAR_THRESHOLD - 1)  # 899자
    r = count(text)
    assert r.char_goal_met is False
    assert r.chars_remaining == 1


def test_word_goal_exactly_met():
    text = " ".join(["단어"] * WORD_THRESHOLD)  # 정확히 200단어
    r = count(text)
    assert r.word_goal_met is True
    assert r.goal_met is True
    assert r.words_remaining == 0


def test_word_goal_one_short():
    text = " ".join(["단어"] * (WORD_THRESHOLD - 1))  # 199단어
    r = count(text)
    assert r.word_goal_met is False
    assert r.words_remaining == 1


def test_or_condition_word_only():
    """글자 수 미달이지만 단어 수 달성 → goal_met True"""
    text = " ".join(["단어"] * WORD_THRESHOLD)  # 200단어, 900자 미만
    r = count(text)
    assert r.char_goal_met is False
    assert r.word_goal_met is True
    assert r.goal_met is True


def test_or_condition_char_only():
    """단어 수 미달이지만 글자 수 달성 → goal_met True"""
    text = "가" * CHAR_THRESHOLD  # 900자, 1단어
    r = count(text)
    assert r.char_goal_met is True
    assert r.word_goal_met is False
    assert r.goal_met is True


def test_newline_as_word_separator():
    text = "안녕\n세상\n반가워"
    r = count(text)
    assert r.word_count == 3


def test_mixed_korean_english():
    text = "Hello 세상 world 안녕"
    r = count(text)
    assert r.word_count == 4
    assert r.char_count == len(text)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd diary-checker
pytest tests/test_counter.py -v
```

Expected: `ImportError` 또는 `ModuleNotFoundError`

- [ ] **Step 3: counter.py 구현**

```python
# diary-checker/diary/counter.py
from dataclasses import dataclass

CHAR_THRESHOLD = 900
WORD_THRESHOLD = 200


@dataclass(frozen=True)
class CountResult:
    char_count: int
    word_count: int
    char_goal_met: bool
    word_goal_met: bool
    goal_met: bool
    chars_remaining: int
    words_remaining: int


def count(text: str) -> CountResult:
    char_count = len(text)
    word_count = len(text.split()) if text.strip() else 0
    char_met = char_count >= CHAR_THRESHOLD
    word_met = word_count >= WORD_THRESHOLD
    return CountResult(
        char_count=char_count,
        word_count=word_count,
        char_goal_met=char_met,
        word_goal_met=word_met,
        goal_met=char_met or word_met,
        chars_remaining=max(0, CHAR_THRESHOLD - char_count),
        words_remaining=max(0, WORD_THRESHOLD - word_count),
    )
```

- [ ] **Step 4: 테스트 실행 — 전체 통과 확인**

```bash
cd diary-checker
pytest tests/test_counter.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: Commit**

```bash
git add diary-checker/diary/counter.py diary-checker/tests/test_counter.py
git commit -m "feat: add diary character/word counter with tests"
```

---

## Chunk 2: Notion 클라이언트

### Task 3: Notion API 클라이언트 (TDD)

**Files:**
- Create: `diary-checker/diary/notion.py`
- Create: `diary-checker/tests/test_notion.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
# diary-checker/tests/test_notion.py
from unittest.mock import MagicMock, patch
from datetime import date
from diary.notion import NotionDiaryClient


PARENT_ID = "2dbad192-0f86-80b7-bb55-e9614da3413a"


def make_child_page_block(title: str, block_id: str) -> dict:
    return {
        "object": "block",
        "id": block_id,
        "type": "child_page",
        "child_page": {"title": title},
        "has_children": True,
        "in_trash": False,
    }


def test_get_today_page_id_found():
    """오늘 날짜로 시작하는 페이지 ID를 반환한다"""
    today = date.today().strftime("%Y%m%d")
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [
            make_child_page_block(f"{today}_테스트", "page-id-123"),
        ],
        "has_more": False,
        "next_cursor": None,
    }

    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    result = diary.get_today_page_id()
    assert result == "page-id-123"


def test_get_today_page_id_not_found():
    """오늘 날짜 페이지가 없으면 None 반환"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [
            make_child_page_block("20260101_과거", "old-page"),
        ],
        "has_more": False,
        "next_cursor": None,
    }

    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    result = diary.get_today_page_id()
    assert result is None


def test_get_today_page_id_pagination():
    """has_more=True일 때 페이지네이션으로 계속 탐색한다"""
    today = date.today().strftime("%Y%m%d")
    mock_client = MagicMock()
    mock_client.blocks.children.list.side_effect = [
        {
            "results": [make_child_page_block("20260101", "old-1")],
            "has_more": True,
            "next_cursor": "cursor-abc",
        },
        {
            "results": [make_child_page_block(today, "today-page")],
            "has_more": False,
            "next_cursor": None,
        },
    ]

    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    result = diary.get_today_page_id()
    assert result == "today-page"
    assert mock_client.blocks.children.list.call_count == 2


def test_extract_text_paragraph():
    """paragraph 블록에서 텍스트를 추출한다"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "오늘은 맑은 날이었다."}]
                },
                "has_children": False,
            }
        ],
        "has_more": False,
    }

    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    text = diary.extract_text("some-page-id")
    assert "오늘은 맑은 날이었다." in text


def test_extract_text_multiple_block_types():
    """heading, paragraph, bulleted_list_item 등 여러 타입을 처리한다"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [{"plain_text": "제목"}]},
                "has_children": False,
            },
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "본문"}]},
                "has_children": False,
            },
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"plain_text": "목록"}]},
                "has_children": False,
            },
        ],
        "has_more": False,
    }

    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    text = diary.extract_text("some-page-id")
    assert "제목" in text
    assert "본문" in text
    assert "목록" in text


def test_extract_text_empty_page():
    """내용 없는 페이지는 빈 문자열을 반환한다"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [],
        "has_more": False,
    }

    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    text = diary.extract_text("empty-page-id")
    assert text == ""


def test_extract_text_pagination():
    """has_more=True일 때 페이지네이션으로 모든 블록을 추출한다"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.side_effect = [
        {
            "results": [
                {
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"plain_text": "첫 번째 페이지 내용"}]},
                    "has_children": False,
                }
            ],
            "has_more": True,
            "next_cursor": "cursor-xyz",
        },
        {
            "results": [
                {
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"plain_text": "두 번째 페이지 내용"}]},
                    "has_children": False,
                }
            ],
            "has_more": False,
        },
    ]

    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    text = diary.extract_text("long-page-id")
    assert "첫 번째 페이지 내용" in text
    assert "두 번째 페이지 내용" in text
    assert mock_client.blocks.children.list.call_count == 2
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd diary-checker
pytest tests/test_notion.py -v
```

Expected: `ImportError`

- [ ] **Step 3: notion.py 구현**

```python
# diary-checker/diary/notion.py
from datetime import date
from notion_client import Client

TEXT_BLOCK_TYPES = {
    "paragraph",
    "heading_1",
    "heading_2",
    "heading_3",
    "bulleted_list_item",
    "numbered_list_item",
    "quote",
    "callout",
}


class NotionDiaryClient:
    def __init__(self, client: Client, parent_id: str):
        self._client = client
        self._parent_id = parent_id

    def get_today_page_id(self) -> str | None:
        """오늘 날짜(YYYYMMDD)로 시작하는 하위 페이지 ID를 반환한다."""
        today_prefix = date.today().strftime("%Y%m%d")
        cursor = None

        while True:
            kwargs = {"block_id": self._parent_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            response = self._client.blocks.children.list(**kwargs)

            for block in response["results"]:
                if block.get("type") == "child_page" and not block.get("in_trash"):
                    title = block["child_page"]["title"]
                    if title.startswith(today_prefix):
                        return block["id"]

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return None

    def extract_text(self, page_id: str) -> str:
        """페이지의 모든 텍스트 블록을 추출하여 하나의 문자열로 반환한다."""
        lines: list[str] = []
        cursor = None

        while True:
            kwargs = {"block_id": page_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            response = self._client.blocks.children.list(**kwargs)

            for block in response["results"]:
                block_type = block.get("type")
                if block_type in TEXT_BLOCK_TYPES:
                    rich_text = block[block_type].get("rich_text", [])
                    text = "".join(rt.get("plain_text", "") for rt in rich_text)
                    if text:
                        lines.append(text)

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return "\n".join(lines)


def make_client(token: str, parent_id: str) -> NotionDiaryClient:
    """환경변수로 초기화된 NotionDiaryClient를 반환한다."""
    return NotionDiaryClient(client=Client(auth=token), parent_id=parent_id)
```

- [ ] **Step 4: 테스트 실행 — 전체 통과 확인**

```bash
cd diary-checker
pytest tests/test_notion.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: Commit**

```bash
git add diary-checker/diary/notion.py diary-checker/tests/test_notion.py
git commit -m "feat: add Notion diary client with pagination and text extraction"
```

---

## Chunk 3: Streamlit UI

### Task 4: app.py — Streamlit UI 구현

**Files:**
- Create: `diary-checker/app.py`

- [ ] **Step 1: app.py 작성**

```python
# diary-checker/app.py
import os
import webbrowser

import pyperclip
import streamlit as st
from dotenv import load_dotenv
from notion_client import Client

from diary.counter import count
from diary.notion import NotionDiaryClient

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DIARY_PARENT_ID = os.getenv("NOTION_DIARY_PARENT_ID", "")

st.set_page_config(page_title="일기 체커", page_icon="✏️", layout="centered")
st.title("✏️ 일기 체커")

# 환경변수 검증
if not NOTION_TOKEN or not NOTION_DIARY_PARENT_ID:
    st.error(
        "NOTION_TOKEN 또는 NOTION_DIARY_PARENT_ID가 설정되지 않았습니다.\n\n"
        ".env 파일을 확인해주세요."
    )
    st.stop()

# Notion 클라이언트 초기화
notion = NotionDiaryClient(
    client=Client(auth=NOTION_TOKEN),
    parent_id=NOTION_DIARY_PARENT_ID,
)

# 오늘 일기 가져오기
if st.button("오늘 일기 가져오기", type="primary"):
    with st.spinner("Notion에서 오늘 일기를 가져오는 중..."):
        page_id = notion.get_today_page_id()
        if page_id is None:
            st.warning("오늘 날짜의 페이지를 찾지 못했습니다. Notion에서 오늘 일기를 먼저 작성해주세요.")
        else:
            text = notion.extract_text(page_id)
            st.session_state["diary_text"] = text

# 텍스트 입력 영역
# NOTE: session_state["diary_text"]는 Notion fetch 결과를 저장하는 용도.
#       textarea의 실제 값은 Streamlit이 key="diary_input"으로 관리한다.
#       fetch 후 첫 렌더링에서만 value=session_state["diary_text"]가 textarea에 주입되고,
#       이후 사용자가 편집하면 diary_text 변수에는 편집된 최신 값이 담긴다.
diary_text = st.text_area(
    "일기 내용",
    value=st.session_state.get("diary_text", ""),
    height=300,
    placeholder="Notion에서 가져오거나 직접 붙여넣기 하세요.",
    key="diary_input",
)

# 실시간 카운팅
result = count(diary_text)

col1, col2 = st.columns(2)

with col1:
    st.metric("글자 수 (공백 포함)", f"{result.char_count:,} / 900")
    st.progress(min(result.char_count / 900, 1.0))
    if result.char_goal_met:
        st.success("900자 달성!")
    else:
        st.caption(f"{result.chars_remaining:,}자 남음")

with col2:
    st.metric("단어 수", f"{result.word_count:,} / 200")
    st.progress(min(result.word_count / 200, 1.0))
    if result.word_goal_met:
        st.success("200단어 달성!")
    else:
        st.caption(f"{result.words_remaining:,}단어 남음")

st.divider()

# 달성 상태 배너
if result.goal_met:
    st.success("오늘 목표 달성! Band에 게시할 준비가 됐습니다.")

    if st.button("📋 복사 + Band 열기", type="primary", disabled=not result.goal_met):
        pyperclip.copy(diary_text)
        webbrowser.open("https://band.us")
        st.info("클립보드에 복사됐습니다. Band에서 붙여넣기 하세요.")
else:
    conditions = []
    if not result.char_goal_met:
        conditions.append(f"900자까지 **{result.chars_remaining:,}자** 남음")
    if not result.word_goal_met:
        conditions.append(f"200단어까지 **{result.words_remaining:,}단어** 남음")
    st.warning("  |  ".join(conditions))
```

- [ ] **Step 2: 앱 실행 확인**

```bash
cd diary-checker
streamlit run app.py
```

브라우저에서 확인:
- "오늘 일기 가져오기" 버튼 클릭 → Notion에서 텍스트 로드
- 글자 수 / 단어 수 실시간 업데이트 확인
- 조건 미달 시 경고 배너, 달성 시 성공 배너 + "복사 + Band 열기" 버튼 활성화

- [ ] **Step 3: Commit**

```bash
git add diary-checker/app.py
git commit -m "feat: add Streamlit UI with Notion fetch and Band copy helper"
```

---

## Chunk 4: 마무리

### Task 5: 전체 테스트 통과 확인

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd diary-checker
pytest -v
```

Expected: 모든 테스트 PASS (test_counter.py + test_notion.py)

- [ ] **Step 2: 최종 Commit**

```bash
git commit -m "feat: diary-checker complete — Notion fetch, length check, Band copy"
```
