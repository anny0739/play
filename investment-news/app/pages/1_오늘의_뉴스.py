"""오늘 수집된 뉴스 피드 + 지수 스냅샷."""

import streamlit as st

from app.db.crud import get_latest_market_snapshot, get_today_articles
from app.db.database import get_session

st.set_page_config(page_title="오늘의 뉴스", page_icon="📰", layout="wide")
st.title("📰 오늘의 뉴스")

CATEGORY_LABELS = {
    "stock_kr": "🇰🇷 국내주식",
    "stock_us": "🇺🇸 미국주식",
    "realestate": "🏠 부동산",
    "macro": "🌐 거시경제",
}
CATEGORY_ORDER = ["stock_kr", "stock_us", "realestate", "macro"]

# ── 상단 지수 스냅샷 바 ────────────────────────────────────────────────────────
with get_session() as session:
    snapshot = get_latest_market_snapshot(session)

if snapshot:
    cols = st.columns(5)
    data = [
        ("KOSPI", snapshot.kospi, "{:,.2f}"),
        ("KOSDAQ", snapshot.kosdaq, "{:,.2f}"),
        ("S&P500", snapshot.sp500, "{:,.2f}"),
        ("NASDAQ", snapshot.nasdaq, "{:,.2f}"),
        ("USD/KRW", snapshot.usd_krw, "{:,.1f}"),
    ]
    for col, (label, value, fmt) in zip(cols, data):
        with col:
            st.metric(label, fmt.format(value) if value else "—")
    st.caption(f"지수 기준: {snapshot.snapshot_date}")
    st.divider()

# ── 카테고리 필터 ─────────────────────────────────────────────────────────────
selected_cat = st.selectbox(
    "카테고리 필터",
    options=["전체"] + list(CATEGORY_LABELS.keys()),
    format_func=lambda x: "📋 전체" if x == "전체" else CATEGORY_LABELS[x],
)
cat_filter = None if selected_cat == "전체" else selected_cat

# ── 기사 목록 ─────────────────────────────────────────────────────────────────
with get_session() as session:
    articles = get_today_articles(session, category=cat_filter)
    # eager load relationships
    for art in articles:
        _ = art.topic
        _ = art.notes

if not articles:
    st.info("오늘 수집된 뉴스가 없습니다. 홈에서 '지금 뉴스 수집'을 눌러보세요.")
    st.stop()

st.write(f"총 **{len(articles)}**건")

# 카테고리별 그룹핑
grouped: dict[str, list] = {}
for art in articles:
    cat = art.topic.category if art.topic else "기타"
    grouped.setdefault(cat, []).append(art)

for cat in CATEGORY_ORDER:
    if cat not in grouped:
        continue
    arts = grouped[cat]
    st.subheader(f"{CATEGORY_LABELS.get(cat, cat)} ({len(arts)}건)")

    for art in arts:
        with st.container(border=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**[{art.title}]({art.url})**")
                if art.source:
                    st.caption(f"출처: {art.source}")
                if art.summary:
                    st.write(art.summary)
                elif art.raw_content:
                    st.write(art.raw_content[:200] + "..." if len(art.raw_content) > 200 else art.raw_content)
            with col2:
                note_count = len(art.notes)
                if note_count:
                    st.badge(f"메모 {note_count}", icon="📝")
                # 메모 추가는 Phase 2에서 st.dialog로 구현
                st.link_button("기사 보기", art.url, use_container_width=True)

    st.divider()
