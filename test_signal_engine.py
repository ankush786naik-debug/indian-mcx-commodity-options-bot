import pytest

from signal_engine import generate_signal


MARKET = {
    "signal": "BUY_CALL",
    "score": 85,
    "underlying_price": 70000,
    "support": 69500,
    "resistance": 71000,
    "reasons": ["Bullish trend", "MACD bullish"],
}

NEWS = {
    "status": "NO_KEYWORD_RISK_DETECTED",
    "allow_trade": True,
}

CONTRACT = {
    "instrument_key": "MCX_FO|GOLD_TEST_CE",
    "instrument_type": "CE",
    "expiry": "2026-12-31",
    "strike_price": 70000,
    "lot_size": 100,
}

OPTION = {
    "instrument_key": "MCX_FO|GOLD_TEST_CE",
    "eligible": True,
    "ask": 251.0,
    "bid": 249.0,
    "ltp": 250.0,
    "lot_size": 100,
    "volume": 5000,
    "open_interest": 12000,
    "spread_percent": 0.8,
}


def test_valid_call_candidate():
    result = generate_signal(
        commodity="GOLD",
        market_analysis=MARKET,
        news_analysis=NEWS,
        option_analysis=OPTION,
        selected_contract=CONTRACT,
        capital=1000000,
    )

    assert result["signal"] == "BUY_CALL"
    assert result["status"] == "PAPER_CANDIDATE"
    assert result["execution_mode"] == "PAPER_ONLY"
    assert result["entry"] == 251.0


def test_news_blocked():
    blocked_news = {
        "status": "RISK_DETECTED",
        "allow_trade": False,
    }

    result = generate_signal(
        "GOLD", MARKET, blocked_news, OPTION,
        CONTRACT, 1000000
    )

    assert result["signal"] == "NO_TRADE"


def test_insufficient_technical_score():
    weak_market = dict(MARKET, score=50)

    result = generate_signal(
        "GOLD", weak_market, NEWS, OPTION,
        CONTRACT, 1000000
    )

    assert result["signal"] == "NO_TRADE"


def test_option_liquidity_rejected():
    poor_option = dict(OPTION, eligible=False)

    result = generate_signal(
        "GOLD", MARKET, NEWS, poor_option,
        CONTRACT, 1000000
    )

    assert result["signal"] == "NO_TRADE"


def test_wrong_option_type_rejected():
    put_contract = dict(CONTRACT, instrument_type="PE")

    result = generate_signal(
        "GOLD", MARKET, NEWS, OPTION,
        put_contract, 1000000
    )

    assert result["signal"] == "NO_TRADE"


def test_quote_contract_mismatch_rejected():
    wrong_option = dict(
        OPTION,
        instrument_key="MCX_FO|OTHER_CONTRACT"
    )

    result = generate_signal(
        "GOLD", MARKET, NEWS, wrong_option,
        CONTRACT, 1000000
    )

    assert result["signal"] == "NO_TRADE"


def test_insufficient_capital_rejected():
    result = generate_signal(
        "GOLD", MARKET, NEWS, OPTION,
        CONTRACT, 1000
    )

    assert result["signal"] == "NO_TRADE"


def test_no_directional_signal():
    no_signal = dict(MARKET, signal="NO_TRADE")

    result = generate_signal(
        "GOLD", no_signal, NEWS, OPTION,
        CONTRACT, 1000000
    )

    assert result["signal"] == "NO_TRADE"
