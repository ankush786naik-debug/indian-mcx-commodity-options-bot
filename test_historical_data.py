import pytest

from historical_data import HistoricalData


class MockClient:
    def __init__(self):
        self.endpoint = None

    def get(self, endpoint, params=None):
        self.endpoint = endpoint
        return {
            "status": "success",
            "data": {
                "candles": [
                    [
                        "2026-11-18T10:00:00+05:30",
                        100.0,
                        105.0,
                        99.0,
                        103.0,
                        1500,
                        200
                    ]
                ]
            }
        }

    def close(self):
        pass


def test_historical_candles():
    client = MockClient()
    history = HistoricalData(client)

    candles = history.get_historical_candles(
        instrument_key="MCX_FO|GOLDM26NOVFUT",
        unit="minutes",
        interval=5,
        to_date="2026-11-18",
        from_date="2026-11-17",
    )

    assert len(candles) == 1
    assert client.endpoint.startswith("/v3/historical-candle/")


def test_intraday_candles():
    client = MockClient()
    history = HistoricalData(client)

    candles = history.get_intraday_candles(
        "MCX_FO|GOLDM26NOVFUT",
        unit="minutes",
        interval=1,
    )

    assert len(candles) == 1
    assert "/intraday/" in client.endpoint


def test_invalid_interval():
    history = HistoricalData(MockClient())

    with pytest.raises(ValueError):
        history.get_historical_candles(
            "MCX_FO|GOLDM26NOVFUT",
            "minutes",
            999,
            "2026-11-18",
        )


def test_invalid_date():
    history = HistoricalData(MockClient())

    with pytest.raises(ValueError):
        history.get_historical_candles(
            "MCX_FO|GOLDM26NOVFUT",
            "minutes",
            5,
            "invalid-date",
        )


def test_start_date_after_end_date():
    history = HistoricalData(MockClient())

    with pytest.raises(ValueError):
        history.get_historical_candles(
            "MCX_FO|GOLDM26NOVFUT",
            "minutes",
            5,
            "2026-11-17",
            "2026-11-18",
        )
      
