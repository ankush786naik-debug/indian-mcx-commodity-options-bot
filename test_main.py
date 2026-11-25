from datetime import datetime
from zoneinfo import ZoneInfo

from main import find_quote, format_scan_summary


def test_find_quote_matches_exact_instrument_token():
    instrument = {
        "segment": "MCX_FO",
        "trading_symbol": "CRUDEOIL FUT 18 DEC 26",
        "instrument_key": "MCX_FO|576264",
    }
    quote = {
        "instrument_token": "MCX_FO|576264",
        "last_price": 7822.0,
    }
    response = {"MCX_FO:CRUDEOIL26DECFUT": quote}

    assert find_quote(response, instrument) is quote


def test_find_quote_rejects_different_contract_token():
    instrument = {
        "segment": "MCX_FO",
        "trading_symbol": "CRUDEOIL FUT 18 DEC 26",
        "instrument_key": "MCX_FO|576264",
    }
    response = {
        "MCX_FO:CRUDEOIL26DECFUT": {
            "instrument_token": "MCX_FO|573422",
            "last_price": 7822.0,
        }
    }

    assert find_quote(response, instrument) is None


def test_scan_summary_reports_no_quote_and_paper_mode():
    started = datetime(2026, 11, 25, 9, 15, tzinfo=ZoneInfo("Asia/Kolkata"))
    summary = format_scan_summary(
        [{
            "commodity": "CRUDEOIL",
            "status": "NO_LIVE_QUOTE",
            "detail": "No matching quote",
        }],
        started,
    )

    assert "CRUDEOIL: NO_LIVE_QUOTE" in summary
    assert "PAPER ONLY" in summary
    assert "Live orders: DISABLED" in summary
