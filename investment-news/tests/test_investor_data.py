"""InvestorSnapshot CRUD + KRX fetcher 유닛 테스트."""

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
        foreign_buy=5000.0,
        foreign_sell=3000.0,
        foreign_net=2000.0,
        inst_buy=1000.0,
        inst_sell=1200.0,
        inst_net=-200.0,
        indiv_buy=4000.0,
        indiv_sell=4800.0,
        indiv_net=-800.0,
    )
    session.commit()
    assert snap.id is not None
    assert snap.market == "KOSPI"
    assert snap.foreign_net == 2000.0

    latest = get_latest_investor_snapshot(session, "KOSPI")
    assert latest is not None
    assert latest.foreign_buy == 5000.0


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


# ── Fetcher ───────────────────────────────────────────────────────────────────

def _make_krx_response(rows: list[dict]) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"output": rows}
    return mock_resp


KRX_SAMPLE_OUTPUT = [
    {
        "INVST_TP_NM": "개인",
        "BID_TRDVAL": "400000000000",
        "ASK_TRDVAL": "480000000000",
        "NETBID_TRDVAL": "-80000000000",
    },
    {
        "INVST_TP_NM": "외국인",
        "BID_TRDVAL": "500000000000",
        "ASK_TRDVAL": "300000000000",
        "NETBID_TRDVAL": "200000000000",
    },
    {
        "INVST_TP_NM": "기관합계",
        "BID_TRDVAL": "100000000000",
        "ASK_TRDVAL": "120000000000",
        "NETBID_TRDVAL": "-20000000000",
    },
]


def test_fetch_investor_data_success():
    from app.investor_data import fetch_investor_trading

    mock_sess = MagicMock()
    mock_sess.get.return_value = MagicMock(ok=True)
    mock_sess.post.return_value = _make_krx_response(KRX_SAMPLE_OUTPUT)

    with patch("app.investor_data.requests.Session", return_value=mock_sess):
        result = fetch_investor_trading("KOSPI", "2026-03-14")

    assert result is not None
    assert result["foreign_net"] == pytest.approx(2000.0, rel=0.01)
    assert result["inst_net"] == pytest.approx(-200.0, rel=0.01)
    assert result["indiv_net"] == pytest.approx(-800.0, rel=0.01)


def test_fetch_investor_data_empty_output():
    from app.investor_data import fetch_investor_trading

    mock_sess = MagicMock()
    mock_sess.get.return_value = MagicMock(ok=True)
    mock_sess.post.return_value = _make_krx_response([])

    with patch("app.investor_data.requests.Session", return_value=mock_sess):
        result = fetch_investor_trading("KOSPI", "2026-03-14")

    assert result is None


def test_fetch_investor_data_network_error():
    from app.investor_data import fetch_investor_trading

    mock_sess = MagicMock()
    mock_sess.get.side_effect = Exception("Connection refused")

    with patch("app.investor_data.requests.Session", return_value=mock_sess):
        result = fetch_investor_trading("KOSPI", "2026-03-14")

    assert result is None


def test_fetch_and_save_investor_data_calls_upsert():
    from app.investor_data import fetch_and_save_investor_data

    mock_data = {
        "foreign_buy": 5000.0, "foreign_sell": 3000.0, "foreign_net": 2000.0,
        "inst_buy": 1000.0, "inst_sell": 1200.0, "inst_net": -200.0,
        "indiv_buy": 4000.0, "indiv_sell": 4800.0, "indiv_net": -800.0,
    }
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch("app.investor_data.fetch_investor_trading", return_value=mock_data),
        patch("app.investor_data.get_session", return_value=mock_ctx),
        patch("app.investor_data.upsert_investor_snapshot") as mock_upsert,
    ):
        result = fetch_and_save_investor_data()

    assert mock_upsert.call_count == 2  # KOSPI + KOSDAQ
    assert "KOSPI" in result and "KOSDAQ" in result
