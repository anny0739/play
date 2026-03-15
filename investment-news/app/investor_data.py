"""KRX 투자자별 매매 현황 수집: 외국인/기관/개인 매수·매도·순매수."""

import logging
from datetime import date, timedelta

import requests

from app.db.crud import upsert_investor_snapshot
from app.db.database import get_session

logger = logging.getLogger(__name__)

KRX_SESSION_URL = "https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd"
KRX_DATA_URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

MARKET_IDS = {"KOSPI": "STK", "KOSDAQ": "KSQ"}

# KRX INVST_TP_NM 값 → 내부 키 접두어 매핑
INVST_KEY_MAP = {"외국인": "foreign", "기관합계": "inst", "개인": "indiv"}

# KRX BID_TRDVAL 등은 원(KRW) 단위 → 억원으로 변환
_WON_TO_EOKWON = 1e8


def _parse_eokwon(value_str: str) -> float:
    """문자열 원 단위 → 억원(float)."""
    return round(int(value_str.replace(",", "")) / _WON_TO_EOKWON, 2)


def fetch_investor_trading(market: str, target_date: str) -> dict | None:
    """
    KRX에서 특정 날짜의 투자자별 매매 데이터 수집.

    Args:
        market: 'KOSPI' or 'KOSDAQ'
        target_date: 'YYYY-MM-DD'

    Returns:
        dict(foreign/inst/indiv × buy/sell/net in 억원) or None
    """
    mkt_id = MARKET_IDS.get(market)
    if mkt_id is None:
        logger.error("알 수 없는 시장: %s", market)
        return None

    date_str = target_date.replace("-", "")
    try:
        sess = requests.Session()
        sess.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://data.krx.co.kr/",
            }
        )
        sess.get(KRX_SESSION_URL, timeout=10)  # 세션 쿠키 취득

        resp = sess.post(
            KRX_DATA_URL,
            data={
                "bld": "dbms/MDC/STAT/standard/MDCSTAT02201",
                "mktId": mkt_id,
                "strtDd": date_str,
                "endDd": date_str,
                "etf": "",
                "etn": "",
                "els": "",
                "share": "1",
                "money": "1",
                "csvxls_isNo": "false",
            },
            timeout=15,
        )
        if not resp.ok:
            logger.warning("KRX API 오류 %s: %s %s", resp.status_code, market, target_date)
            return None

        rows = resp.json().get("output", [])
        if not rows:
            logger.info("KRX 데이터 없음 (휴일?): %s %s", market, target_date)
            return None

        result: dict[str, float | None] = {}
        for row in rows:
            prefix = INVST_KEY_MAP.get(row.get("INVST_TP_NM", ""))
            if prefix is None:
                continue
            try:
                result[f"{prefix}_buy"] = _parse_eokwon(row["BID_TRDVAL"])
                result[f"{prefix}_sell"] = _parse_eokwon(row["ASK_TRDVAL"])
                result[f"{prefix}_net"] = _parse_eokwon(row["NETBID_TRDVAL"])
            except (KeyError, ValueError) as e:
                logger.warning("파싱 오류 %s %s: %s", market, prefix, e)
                result[f"{prefix}_buy"] = None
                result[f"{prefix}_sell"] = None
                result[f"{prefix}_net"] = None

        if "foreign_net" not in result:
            return None
        return result

    except Exception as e:
        logger.error("KRX 투자자 수집 오류 %s %s: %s", market, target_date, e)
        return None


def fetch_investor_trading_latest(market: str) -> tuple[str | None, dict | None]:
    """최근 5일 소급하여 가장 최신 영업일 데이터 수집."""
    for days_back in range(5):
        target = (date.today() - timedelta(days=days_back)).isoformat()
        data = fetch_investor_trading(market, target)
        if data is not None:
            return target, data
    logger.warning("최근 5일 내 KRX 데이터 없음: %s", market)
    return None, None


def fetch_and_save_investor_data() -> dict[str, dict | None]:
    """KOSPI/KOSDAQ 투자자 데이터 수집 후 DB 저장."""
    results: dict[str, dict | None] = {}
    for market in ("KOSPI", "KOSDAQ"):
        trading_date, data = fetch_investor_trading_latest(market)
        results[market] = data
        if data is not None and trading_date is not None:
            with get_session() as session:
                upsert_investor_snapshot(
                    session, snapshot_date=trading_date, market=market, **data
                )
            logger.info(
                "투자자 저장: %s %s 외국인순매수=%.1f억",
                market,
                trading_date,
                data.get("foreign_net") or 0,
            )
        else:
            logger.warning("투자자 데이터 없음: %s", market)
    return results
