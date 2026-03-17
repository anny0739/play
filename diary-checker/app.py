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
            st.warning(
                "오늘 날짜의 페이지를 찾지 못했습니다. Notion에서 오늘 일기를 먼저 작성해주세요."
            )
        else:
            text = notion.extract_text(page_id)
            st.session_state["diary_text"] = text
            st.session_state["diary_input"] = text

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
