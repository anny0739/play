"""InvestorSnapshot CRUD + 네이버 API fetcher 유닛 테스트."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


# ── CRUD ──────────────────────────────────────────────────────────────────────


def test_upsert_investor_snapshot_creates(session):
    from app.db.crud import get_latest_investor_snapshot, upsert_investor_snapshot

    snap = upsert_investor_snapshot(
        session,
        snapshot_date="2026-03-14",
        market="KOSPI",
        foreign_net=2000.0,
        inst_net=-200.0,
        indiv_net=-800.0,
    )
    session.commit()
    assert snap.id is not None
    assert snap.market == "KOSPI"
    assert snap.foreign_net == 2000.0


def test_upsert_investor_snapshot_updates(session):
    from app.db.crud import get_latest_investor_snapshot, upsert_investor_snapshot

    upsert_investor_snapshot(
        session, snapshot_date="2026-03-14", market="KOSPI", foreign_net=2000.0
    )
    session.commit()
    upsert_investor_snapshot(
        session, snapshot_date="2026-03-14", market="KOSPI", foreign_net=2500.0
    )
    session.commit()

    latest = get_latest_investor_snapshot(session, "KOSPI")
    assert latest.foreign_net == 2500.0


def test_upsert_investor_snapshot_separate_markets(session):
    from app.db.crud import get_latest_investor_snapshot, upsert_investor_snapshot

    upsert_investor_snapshot(
        session, snapshot_date="2026-03-14", market="KOSPI", foreign_net=2000.0
    )
    upsert_investor_snapshot(
        session, snapshot_date="2026-03-14", market="KOSDAQ", foreign_net=500.0
    )
    session.commit()

    assert get_latest_investor_snapshot(session, "KOSPI").foreign_net == 2000.0
    assert get_latest_investor_snapshot(session, "KOSDAQ").foreign_net == 500.0


def test_get_latest_investor_snapshot_returns_none_when_empty(session):
    from app.db.crud import get_latest_investor_snapshot

    assert get_latest_investor_snapshot(session, "KOSPI") is None


# ── Fetcher (네이버 API) ────────────────────────────────────────────────────

NAVER_SAMPLE_RESPONSE = {
    "bizdate": "20260313",
    "personalValue": "+24,512",
    "foreignValue": "-14,502",
    "institutionalValue": "-10,434",
}


def test_fetch_investor_trend_success():
    from app.investor_data import fetch_investor_trend

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = NAVER_SAMPLE_RESPONSE

    with patch("app.investor_data.requests.get", return_value=mock_resp):
        result = fetch_investor_trend("KOSPI")

    assert result is not None
    assert result["snapshot_date"] == "2026-03-13"
    assert result["foreign_net"] == pytest.approx(-14502.0)
    assert result["inst_net"] == pytest.approx(-10434.0)
    assert result["indiv_net"] == pytest.approx(24512.0)


def test_fetch_investor_trend_api_error():
    from app.investor_data import fetch_investor_trend

    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 500

    with patch("app.investor_data.requests.get", return_value=mock_resp):
        result = fetch_investor_trend("KOSPI")

    assert result is None


def test_fetch_investor_trend_network_error():
    from app.investor_data import fetch_investor_trend

    with patch("app.investor_data.requests.get", side_effect=Exception("Connection refused")):
        result = fetch_investor_trend("KOSPI")

    assert result is None


def test_fetch_and_save_investor_data_calls_upsert():
    from app.investor_data import fetch_and_save_investor_data

    mock_data = {
        "snapshot_date": "2026-03-13",
        "foreign_net": -14502.0,
        "inst_net": -10434.0,
        "indiv_net": 24512.0,
    }
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch("app.investor_data.fetch_investor_trend", return_value=mock_data),
        patch("app.investor_data.get_session", return_value=mock_ctx),
        patch("app.investor_data.upsert_investor_snapshot") as mock_upsert,
    ):
        result = fetch_and_save_investor_data()

    assert mock_upsert.call_count == 2  # KOSPI + KOSDAQ
    assert "KOSPI" in result and "KOSDAQ" in result
