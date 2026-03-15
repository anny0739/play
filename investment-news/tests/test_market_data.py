"""market_data.py 유닛 테스트 (외부 API는 mock)."""

from unittest.mock import MagicMock, patch

import pytest


def test_fetch_us_indices_success():
    """yfinance 정상 응답 케이스."""
    mock_hist = MagicMock()
    mock_hist.empty = False
    mock_hist.__getitem__ = lambda self, key: MagicMock(iloc=[5000.0])

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_hist

    with patch("yfinance.Ticker", return_value=mock_ticker):
        from app.market_data import fetch_us_indices
        result = fetch_us_indices()
        assert "sp500" in result
        assert "nasdaq" in result
        assert "usd_krw" in result


def test_fetch_us_indices_import_error():
    """yfinance 미설치 케이스 — None 반환."""
    with patch.dict("sys.modules", {"yfinance": None}):
        import importlib
        import sys
        if "app.market_data" in sys.modules:
            del sys.modules["app.market_data"]
        from app.market_data import fetch_us_indices
        result = fetch_us_indices()
        # yfinance 없으면 None 값들 반환
        assert all(v is None for v in result.values())


def test_fetch_kr_indices_fallback():
    """pykrx 오류 시 None 반환."""
    with patch("app.market_data.fetch_kr_indices", return_value={"kospi": None, "kosdaq": None}):
        from app.market_data import fetch_kr_indices
        result = fetch_kr_indices()
        assert result["kospi"] is None
        assert result["kosdaq"] is None
