"""재테크 뉴스 애그리게이터 — 홈 화면."""

import html as _html
import logging

import streamlit as st
import streamlit.components.v1 as components

from app.config import ANTHROPIC_API_KEY
from app.db.crud import get_latest_investor_snapshot, get_latest_market_snapshot
from app.db.database import get_session, init_db
from app.scheduler.jobs import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── 초기화 (최초 1회) ────────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    init_db()
    start_scheduler()
    st.session_state.initialized = True

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="재테크 뉴스 애그리게이터",
    page_icon="📈",
    layout="wide",
)

st.title("📈 재테크 뉴스 애그리게이터")
st.caption("국내외 주식 · 부동산 · 거시경제 뉴스를 자동 수집하고 AI로 분석합니다.")

# ── API 키 경고 ───────────────────────────────────────────────────────────────
if not ANTHROPIC_API_KEY:
    st.error("⚠️ ANTHROPIC_API_KEY가 설정되지 않았습니다. `.env` 파일을 확인하세요.")

# ── 지수 현황 카드 ────────────────────────────────────────────────────────────
with get_session() as session:
    snapshot = get_latest_market_snapshot(session)

with get_session() as session:
    kospi_inv = get_latest_investor_snapshot(session, "KOSPI")
    kosdaq_inv = get_latest_investor_snapshot(session, "KOSDAQ")

st.subheader("📊 시장 지수 현황")
cols = st.columns(5)
labels = ["KOSPI", "KOSDAQ", "S&P 500", "NASDAQ", "USD/KRW"]
values = [
    snapshot.kospi if snapshot else None,
    snapshot.kosdaq if snapshot else None,
    snapshot.sp500 if snapshot else None,
    snapshot.nasdaq if snapshot else None,
    snapshot.usd_krw if snapshot else None,
]
formats = ["{:,.2f}", "{:,.2f}", "{:,.2f}", "{:,.2f}", "{:,.1f}"]

for col, label, value, fmt in zip(cols, labels, values, formats):
    with col:
        if value is not None:
            st.metric(label, fmt.format(value))
        else:
            st.metric(label, "—")

if snapshot:
    st.caption(f"마지막 업데이트: {snapshot.fetched_at.strftime('%Y-%m-%d %H:%M')} (UTC)")

st.divider()

# ── 투자자별 매매 현황 캐러셀 ──────────────────────────────────────────────────


def _fmt_eokwon(val: float | None) -> str:
    if val is None:
        return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:,.0f}억"


def _net_color(val: float | None) -> str:
    if val is None:
        return "#888888"
    return "#27ae60" if val >= 0 else "#e74c3c"


def _render_investor_panel(title: str, inv) -> str:
    if inv is None:
        return (
            f'<div style="padding:16px;text-align:center;color:#888;">'
            f"<strong>{title}</strong><br/>"
            f'<span style="font-size:13px;">데이터 없음</span></div>'
        )
    rows_html = ""
    for label, net in [
        ("외국인", inv.foreign_net),
        ("기관", inv.inst_net),
        ("개인", inv.indiv_net),
    ]:
        rows_html += (
            f"<tr>"
            f'<td style="padding:6px 12px;font-weight:bold;">{label}</td>'
            f'<td style="padding:6px 12px;text-align:right;color:{_net_color(net)};'
            f'font-weight:bold;">{_fmt_eokwon(net)}</td>'
            f"</tr>"
        )
    return (
        f'<div style="padding:8px 0;">'
        f'<div style="font-size:18px;font-weight:bold;margin-bottom:6px;">'
        f'{title} <span style="font-size:12px;color:#888;">({inv.snapshot_date})</span></div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:14px;">'
        f'<thead><tr style="border-bottom:1px solid #ddd;color:#666;font-size:12px;">'
        f'<th style="padding:4px 12px;text-align:left;">구분</th>'
        f'<th style="padding:4px 12px;text-align:right;">순매수</th>'
        f"</tr></thead><tbody>{rows_html}</tbody></table></div>"
    )


kospi_html = _render_investor_panel("KOSPI 투자자 매매", kospi_inv)
kosdaq_html = _render_investor_panel("KOSDAQ 투자자 매매", kosdaq_inv)

carousel_html = f"""
<div id="inv-carousel" style="font-family:sans-serif;min-height:160px;">
  <div id="panel-kospi">{kospi_html}</div>
  <div id="panel-kosdaq" style="display:none;">{kosdaq_html}</div>
</div>
<script>
(function() {{
  var panels = ['panel-kospi', 'panel-kosdaq'];
  var current = 0;
  setInterval(function() {{
    document.getElementById(panels[current]).style.display = 'none';
    current = (current + 1) % panels.length;
    document.getElementById(panels[current]).style.display = 'block';
  }}, 5000);
}})();
</script>
"""

st.subheader("👥 투자자별 매매 현황")
components.html(carousel_html, height=200)

st.divider()

# ── 오늘의 뉴스 ──────────────────────────────────────────────────────────────
from app.db.crud import get_today_articles  # noqa: E402

st.subheader("📰 오늘의 뉴스")

CATEGORY_LABELS = {
    "stock_kr": "🇰🇷 국내 주식",
    "stock_us": "🇺🇸 해외 주식",
    "realestate": "🏠 부동산",
    "macro": "📊 거시경제",
}

with get_session() as session:
    today_articles = get_today_articles(session)

if today_articles:
    by_cat: dict[str, list] = {}
    for art in today_articles:
        cat = art.topic.category
        by_cat.setdefault(cat, []).append(art)

    for cat in ["stock_kr", "stock_us", "realestate", "macro"]:
        articles = by_cat.get(cat, [])
        if not articles:
            continue
        label = CATEGORY_LABELS.get(cat, cat)
        st.markdown(
            f'<p style="font-size:15px;font-weight:700;margin:16px 0 0;">{label} '
            f'<span style="font-size:12px;font-weight:400;opacity:0.45;">{len(articles)}건</span></p>',
            unsafe_allow_html=True,
        )
        rows_html = ""
        for art in articles:
            raw = art.raw_content or ""
            snippet = _html.escape(raw[:15] + ("…" if len(raw) > 15 else ""))
            title_esc = _html.escape(art.title)
            source = _html.escape(art.source or "")
            time_str = art.fetched_at.strftime("%m/%d") if art.fetched_at else ""
            meta = " · ".join(p for p in [source, time_str] if p)
            snippet_div = (
                f'<div style="font-size:12px;opacity:0.55;margin-bottom:2px;">{snippet}</div>'
                if snippet
                else ""
            )
            rows_html += (
                f'<a href="{art.url}" target="_blank"'
                f' style="text-decoration:none;color:inherit;display:block;">'
                f'<div style="padding:10px 0;border-bottom:1px solid rgba(128,128,128,0.15);">'
                f'<div style="font-size:13px;font-weight:600;line-height:1.45;margin-bottom:3px;">'
                f"{title_esc}</div>"
                f"{snippet_div}"
                f'<div style="font-size:11px;opacity:0.4;">{meta}</div>'
                f"</div></a>"
            )
        st.markdown(rows_html, unsafe_allow_html=True)
else:
    st.info("오늘 수집된 뉴스가 없습니다. 위 버튼으로 수집해 보세요.")

st.divider()

# ── 스케줄러 상태 ─────────────────────────────────────────────────────────────
from app.scheduler.jobs import get_scheduler  # noqa: E402

scheduler = get_scheduler()
st.subheader("⏰ 스케줄러 상태")
status = "🟢 실행 중" if scheduler.running else "🔴 정지"
st.write(f"상태: **{status}**")

if scheduler.running:
    jobs = scheduler.get_jobs()
    for job in jobs:
        next_run = job.next_run_time
        next_str = next_run.strftime("%Y-%m-%d %H:%M %Z") if next_run else "—"
        st.write(f"- `{job.id}`: 다음 실행 → {next_str}")

st.info(
    "💡 매일 **07:00 KST**에 뉴스를 자동 수집합니다. "
    "**16:10 KST**에 국내 지수를 업데이트하며, 투자자 매매 현황은 **매 1시간**마다 갱신됩니다."
)

st.divider()

# ── 수동 수집 버튼 ─────────────────────────────────────────────────────────────
st.subheader("🔄 수동 수집")
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("지금 뉴스 수집", type="primary", use_container_width=True):
        with st.spinner("뉴스를 수집하는 중입니다..."):
            from app.investor_data import fetch_and_save_investor_data
            from app.market_data import fetch_and_save_market_data
            from app.notifier import notify_fetch_complete
            from app.rss_collector import fetch_rss_articles

            counts: dict[str, int] = {}
            market = None
            errors: list[str] = []

            # RSS 뉴스 수집
            try:
                counts = fetch_rss_articles()
            except Exception as e:
                errors.append(f"뉴스 수집: {e}")

            # 시장 지수 수집
            try:
                market = fetch_and_save_market_data()
            except Exception as e:
                errors.append(f"시장 지수: {e}")

            # 투자자 데이터 수집
            try:
                fetch_and_save_investor_data()
            except Exception as e:
                errors.append(f"투자자 데이터: {e}")

            notify_fetch_complete(counts, market)

            total_new = sum(counts.values())
            for err in errors:
                st.error(f"⚠️ {err}")

            if total_new:
                st.success(f"✅ 신규 {total_new}건 수집 완료!")
                st.json(counts)
            else:
                # 오늘 기존 수집된 기사 수 표시
                from app.db.crud import get_today_articles

                with get_session() as sess:
                    existing = len(get_today_articles(sess))
                if existing:
                    st.info(f"📰 신규 기사가 없습니다. (오늘 수집된 기사: {existing}건)")
                else:
                    st.warning("⚠️ 오늘 수집된 기사가 없습니다. RSS 피드를 확인해 주세요.")
            st.rerun()

with col2:
    if st.button("지수만 업데이트", use_container_width=True):
        with st.spinner("지수 데이터를 업데이트하는 중..."):
            try:
                from app.market_data import fetch_and_save_market_data

                market = fetch_and_save_market_data()
                from app.investor_data import fetch_and_save_investor_data

                fetch_and_save_investor_data()
                st.success("✅ 지수 및 투자자 데이터 업데이트 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"지수 업데이트 오류: {e}")
