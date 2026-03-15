# Diary Checker Design Spec

**Date:** 2026-03-16
**Status:** Approved

---

## 1. 문제

사용자는 매일 "100일 글쓰기" 챌린지를 Notion에서 진행 중이다. 두 가지 불편함이 있다:

1. Notion에서 오늘 일기를 복사해오는 것 (수동)
2. 분량 조건(900자 이상 OR 200단어 이상)을 매번 직접 세는 것 (수동)

Band에 게시하는 것은 수동으로 해도 괜찮지만, 복사+열기를 한 번에 해주면 편하다.

---

## 2. 목표

Streamlit 앱을 실행하면:
- 오늘 Notion 일기를 버튼 하나로 자동으로 가져온다
- 글자 수 / 단어 수를 실시간으로 보여준다
- 조건 충족 시 "복사 + Band 열기" 버튼을 활성화한다

---

## 3. Notion 구조 (확인됨)

- 부모 페이지: `100일 글쓰기` (ID: `2dbad192-0f86-80b7-bb55-e9614da3413a`)
- 하위 페이지 제목 형식: `YYYYMMDD` 또는 `YYYYMMDD_제목` (예: `20260316`, `20260102_십분`)
- 오늘 페이지 탐색: 제목이 오늘 날짜 `YYYYMMDD`로 시작하는 페이지

---

## 4. 분량 조건

- **글자 수:** `len(text)` — 공백 포함
- **단어 수:** `len(text.split())` — 공백/개행 기준 어절
- **충족 조건:** 900자 이상 **OR** 200단어 이상

---

## 5. 아키텍처

```
diary-checker/
├── .env                  # NOTION_TOKEN, NOTION_DIARY_PARENT_ID
├── app.py                # Streamlit 엔트리포인트
├── requirements.txt
└── diary/
    ├── __init__.py
    ├── counter.py        # 글자/단어 카운팅 순수 함수
    └── notion.py         # Notion API: 오늘 페이지 탐색 + 텍스트 추출
```

**의존성:**
```
streamlit>=1.32
notion-client>=2.0
pyperclip
python-dotenv
```

---

## 6. 컴포넌트 설계

### `counter.py`

```python
@dataclass(frozen=True)
class CountResult:
    char_count: int
    word_count: int
    char_goal_met: bool   # >= 900
    word_goal_met: bool   # >= 200
    goal_met: bool        # OR
    chars_remaining: int
    words_remaining: int

def count(text: str) -> CountResult: ...
```

### `notion.py`

```python
class NotionDiaryClient:
    def get_today_page_id(self) -> str | None
        # 부모 페이지 하위 목록 순회 (페이지네이션 포함)
        # 제목이 today.strftime("%Y%m%d")로 시작하는 페이지 반환

    def extract_text(self, page_id: str) -> str
        # 블록 순회: paragraph, heading_1/2/3, bulleted_list_item,
        #            numbered_list_item, quote, callout
        # plain_text 연결하여 반환
```

### `app.py` UI 흐름

```
[오늘 일기 가져오기] 버튼
  → notion.py로 오늘 페이지 탐색
  → 텍스트 추출 → textarea에 표시

textarea 변경 시 (on_change)
  → counter.py로 글자/단어 수 계산
  → 진행률 바 + 상태 배너 갱신

[복사 + Band 열기] (goal_met일 때만 활성화)
  → pyperclip.copy(text)
  → webbrowser.open("https://band.us")
```

---

## 7. 엣지 케이스

| 케이스 | 처리 |
|---|---|
| 오늘 Notion 페이지 없음 | "오늘 페이지를 찾지 못했습니다" 안내 메시지 |
| 페이지는 있으나 내용 없음 | 빈 textarea, 카운트 0 표시 |
| NOTION_TOKEN 미설정 | 앱 시작 시 에러 메시지 + .env 설정 안내 |
| 페이지네이션 (100개 이상) | `has_more` 반복 순회로 처리 |

---

## 8. .env 설정

```
NOTION_TOKEN=ntn_...
NOTION_DIARY_PARENT_ID=2dbad192-0f86-80b7-bb55-e9614da3413a
```
