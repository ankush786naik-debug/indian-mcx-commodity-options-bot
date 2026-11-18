import pytest

from option_analysis import analyze_option_quote


CONTRACT = {
    "instrument_key": "MCX_FO|GOLD_TEST_CE",
    "lot_size": 100,
}

GOOD_QUOTE = {
    "last_price": 250.0,
    "volume": 5000,
    "oi": 12000,
    "depth": {
        "buy": [{"price": 249.0, "quantity": 100}],
        "sell": [{"price": 251.0, "quantity": 100}],
    },
}


def test_liquid_option_eligible():
    result = analyze_option_quote(CONTRACT, GOOD_QUOTE)

    assert result["eligible"] is True
    assert result["ltp"] == 250.0
    assert result["volume"] == 5000
    assert result["open_interest"] == 12000


def test_spread_calculation():
    result = analyze_option_quote(CONTRACT, GOOD_QUOTE)

    assert result["spread_percent"] == pytest.approx(0.8)


def test_low_volume_rejected():
    quote = GOOD_QUOTE.copy()
    quote["volume"] = 0

    result = analyze_option_quote(CONTRACT, quote)

    assert result["eligible"] is False
    assert "Insufficient trading volume" in result["reasons"]


def test_low_open_interest_rejected():
    quote = GOOD_QUOTE.copy()
    quote["oi"] = 0

    result = analyze_option_quote(CONTRACT, quote)

    assert result["eligible"] is False
    assert "Insufficient open interest" in result["reasons"]


def test_missing_bid_ask_rejected():
    quote = {
        "last_price": 250,
        "volume": 5000,
        "oi": 12000,
    }

    result = analyze_option_quote(CONTRACT, quote)

    assert result["eligible"] is False
    assert "Valid bid/ask prices unavailable" in result["reasons"]


def test_wide_spread_rejected():
    quote = {
        "last_price": 250,
        "volume": 5000,
        "oi": 12000,
        "depth": {
            "buy": [{"price": 240}],
            "sell": [{"price": 260}],
        },
    }

    result = analyze_option_quote(CONTRACT, quote)

    assert result["eligible"] is False
    assert "Bid/ask spread too wide" in result["reasons"]


def test_invalid_lot_size_rejected():
    contract = {
        "instrument_key": "MCX_TEST",
        "lot_size": 0,
    }

    result = analyze_option_quote(contract, GOOD_QUOTE)

    assert result["eligible"] is False
    assert "Invalid lot size" in result["reasons"]
