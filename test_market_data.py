import pytest

from market_data import MarketData
from main import find_quote


class MockUpstoxClient:
    def __init__(self, response=None):
        self.response = response or {
            "status": "success",
            "data": {
                "MCX_FUT_TEST": {
                    "last_price": 100.0
                }
            }
        }
        self.last_endpoint = None
        self.last_params = None
        self.closed = False

    def get(self, endpoint, params=None):
        self.last_endpoint = endpoint
        self.last_params = params
        return self.response

    def close(self):
        self.closed = True


def test_market_quote():
    client = MockUpstoxClient()
    market = MarketData(client)

    result = market.get_market_quote(["MCX_FUT_TEST"])

    assert "MCX_FUT_TEST" in result
    assert client.last_endpoint == "/v2/market-quote/quotes"


def test_ltp():
    client = MockUpstoxClient()
    market = MarketData(client)

    result = market.get_ltp(["MCX_FUT_TEST"])

    assert "MCX_FUT_TEST" in result
    assert client.last_endpoint == "/v2/market-quote/ltp"


def test_empty_instrument_list():
    market = MarketData(MockUpstoxClient())

    with pytest.raises(ValueError):
        market.get_market_quote([])


def test_invalid_response():
    client = MockUpstoxClient({
        "status": "error",
        "data": {}
    })
    market = MarketData(client)

    with pytest.raises(RuntimeError):
        market.get_ltp(["MCX_FUT_TEST"])


def test_close_client():
    client = MockUpstoxClient()
    market = MarketData(client)

    market.close()

    assert client.closed is True
  


def test_find_quote_matches_canonical_mcx_future_symbol():
    contract = {
        "segment": "MCX_FO",
        "instrument_key": "MCX_FO|576264",
        "trading_symbol": "CRUDEOIL FUT 18 DEC 26",
        "underlying_symbol": "CRUDEOIL",
        "name": "CRUDEOIL",
        "instrument_type": "FUT",
        "expiry": "2026-12-18",
    }
    quote = {"last_price": 7822.0}
    response = {"MCX_FO:CRUDEOIL26DECFUT": quote}

    assert find_quote(response, contract) is quote


def test_find_quote_does_not_match_another_expiry():
    contract = {
        "segment": "MCX_FO",
        "instrument_key": "MCX_FO|576264",
        "trading_symbol": "CRUDEOIL FUT 18 DEC 26",
        "underlying_symbol": "CRUDEOIL",
        "name": "CRUDEOIL",
        "instrument_type": "FUT",
        "expiry": "2026-12-18",
    }
    response = {"MCX_FO:CRUDEOIL26NOVFUT": {"last_price": 7800.0}}

    assert find_quote(response, contract) is None
