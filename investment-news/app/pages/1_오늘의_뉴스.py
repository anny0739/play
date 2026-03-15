"""오늘 수집된 뉴스 피드 + 지수 스냅샷."""

import html as _html

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
    st.markdown(
        f'<p style="font-size:17px;font-weight:700;margin:20px 0 4px;">'
        f"{CATEGORY_LABELS.get(cat, cat)} "
        f'<span style="font-size:13px;font-weight:400;opacity:0.45;">{len(arts)}건</span></p>',
        unsafe_allow_html=True,
    )
    rows_html = ""
    for art in arts:
        raw = art.raw_content or art.summary or ""
        snippet = _html.escape(raw[:15] + ("…" if len(raw) > 15 else ""))
        title_esc = _html.escape(art.title)
        source = _html.escape(art.source or "")
        time_str = art.fetched_at.strftime("%m/%d") if art.fetched_at else ""
        meta = " · ".join(p for p in [source, time_str] if p)
        note_count = len(art.notes)
        note_badge = (
            f'<span style="display:inline-block;background:rgba(0,122,255,0.12);'
            f"color:#007aff;font-size:10px;font-weight:600;padding:1px 7px;"
            f'border-radius:10px;margin-left:6px;">메모 {note_count}</span>'
            if note_count
            else ""
        )
        snippet_div = (
            f'<div style="font-size:13px;opacity:0.55;margin-bottom:3px;">{snippet}</div>'
            if snippet
            else ""
        )
        rows_html += (
            f'<a href="{art.url}" target="_blank"'
            f' style="text-decoration:none;color:inherit;display:block;">'
            f'<div style="padding:12px 0;border-bottom:1px solid rgba(128,128,128,0.15);">'
            f'<div style="font-size:14px;font-weight:600;line-height:1.45;margin-bottom:4px;">'
            f"{title_esc}{note_badge}</div>"
            f"{snippet_div}"
            f'<div style="font-size:11px;opacity:0.4;">{meta}</div>'
            f"</div></a>"
        )
    st.markdown(rows_html, unsafe_allow_html=True)
    st.write("")
