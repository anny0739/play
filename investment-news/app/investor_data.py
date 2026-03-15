"""투자자별 매매 현황 수집: 네이버 증권 API → 외국인/기관/개인 순매수."""

import logging

import requests

from app.db.crud import upsert_investor_snapshot
from app.db.database import get_session

logger = logging.getLogger(__name__)

# 네이버 모바일 증권 API (인증 불필요)
_NAVER_TREND_URL = "https://m.stock.naver.com/api/index/{market}/trend"

_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _parse_value(val_str: str) -> float:
    """'+24,512' 또는 '-829' 형태 → 억원(float)."""
    return float(val_str.replace(",", "").replace("+", ""))


def fetch_investor_trend(market: str) -> dict | None:
    """네이버 증권 API에서 투자자별 순매수 데이터 수집.

    Args:
        market: 'KOSPI' or 'KOSDAQ'

    Returns:
        dict(foreign_net, inst_net, indiv_net in 억원, bizdate) or None
    """
    try:
        url = _NAVER_TREND_URL.format(market=market)
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if not resp.ok:
            logger.warning("네이버 API 오류 %s: %s", market, resp.status_code)
            return None

        data = resp.json()
        bizdate = data.get("bizdate", "")
        if not bizdate:
            logger.warning("네이버 API 응답에 bizdate 없음: %s", market)
            return None

        # bizdate: '20260313' → '2026-03-13'
        snapshot_date = f"{bizdate[:4]}-{bizdate[4:6]}-{bizdate[6:8]}"

        return {
            "snapshot_date": snapshot_date,
            "foreign_net": _parse_value(data["foreignValue"]),
            "inst_net": _parse_value(data["institutionalValue"]),
            "indiv_net": _parse_value(data["personalValue"]),
        }

    except Exception as e:
        logger.error("네이버 투자자 수집 오류 %s: %s", market, e)
        return None


def fetch_and_save_investor_data() -> dict[str, dict | None]:
    """KOSPI/KOSDAQ 투자자 데이터 수집 후 DB 저장."""
    results: dict[str, dict | None] = {}
    for market in ("KOSPI", "KOSDAQ"):
        data = fetch_investor_trend(market)
        results[market] = data
        if data is not None:
            snapshot_date = data["snapshot_date"]
            upsert_kwargs = {k: v for k, v in data.items() if k != "snapshot_date"}
            with get_session() as session:
                upsert_investor_snapshot(
                    session, snapshot_date=snapshot_date, market=market, **upsert_kwargs
                )
            logger.info(
                "투자자 저장: %s %s 외국인순매수=%.0f억",
                market,
                snapshot_date,
                data.get("foreign_net") or 0,
            )
        else:
            logger.warning("투자자 데이터 없음: %s", market)
    return results
