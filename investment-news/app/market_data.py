"""시장 지수 수집: pykrx(KOSPI/KOSDAQ) + yfinance(S&P500/NASDAQ/USD-KRW)."""

import logging
from datetime import date

from app.db.crud import upsert_market_snapshot
from app.db.database import get_session

logger = logging.getLogger(__name__)


def fetch_kr_indices() -> dict[str, float | None]:
    """yfinance로 KOSPI(^KS11), KOSDAQ(^KQ11) 종가 수집."""
    try:
        import yfinance as yf

        result: dict[str, float | None] = {}
        for key, symbol in [("kospi", "^KS11"), ("kosdaq", "^KQ11")]:
            try:
                hist = yf.Ticker(symbol).history(period="5d")
                result[key] = float(hist["Close"].iloc[-1]) if not hist.empty else None
            except Exception as e:
                logger.error("%s 수집 오류: %s", symbol, e)
                result[key] = None
        return result
    except ImportError:
        logger.warning("yfinance 미설치. 국내 지수 수집 불가.")
    except Exception as e:
        logger.error("국내 지수 수집 오류: %s", e)
    return {"kospi": None, "kosdaq": None}


def fetch_us_indices() -> dict[str, float | None]:
    """yfinance로 S&P500, NASDAQ, USD/KRW 수집."""
    try:
        import yfinance as yf

        tickers = {"sp500": "^GSPC", "nasdaq": "^IXIC", "usd_krw": "KRW=X"}
        result: dict[str, float | None] = {}
        for key, symbol in tickers.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if not hist.empty:
                    result[key] = float(hist["Close"].iloc[-1])
                else:
                    result[key] = None
            except Exception as e:
                logger.error("%s 수집 오류: %s", symbol, e)
                result[key] = None
        return result
    except ImportError:
        logger.warning("yfinance 미설치. 미국 지수 수집 불가.")
    except Exception as e:
        logger.error("미국 지수 수집 오류: %s", e)
    return {"sp500": None, "nasdaq": None, "usd_krw": None}


def fetch_and_save_market_data() -> dict:
    """모든 지수 수집 후 DB 저장. 수집된 데이터 dict 반환."""
    kr = fetch_kr_indices()
    us = fetch_us_indices()
    data = {**kr, **us}
    today = date.today().isoformat()

    with get_session() as session:
        upsert_market_snapshot(session, snapshot_date=today, **data)

    logger.info(
        "지수 저장 완료: KOSPI=%.2f KOSDAQ=%.2f S&P500=%.2f NASDAQ=%.2f USD/KRW=%.2f",
        data.get("kospi") or 0,
        data.get("kosdaq") or 0,
        data.get("sp500") or 0,
        data.get("nasdaq") or 0,
        data.get("usd_krw") or 0,
    )
    return data
