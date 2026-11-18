from datetime import date
from urllib.parse import quote

from upstox_client import UpstoxClient


class HistoricalData:
    VALID_UNITS = {
        "minutes": range(1, 301),
        "hours": range(1, 6),
        "days": [1],
        "weeks": [1],
        "months": [1],
    }

    def __init__(self, client=None):
        self.client = client or UpstoxClient()

    def _validate(self, instrument_key, unit, interval, to_date, from_date=None):
        if not instrument_key or not isinstance(instrument_key, str):
            raise ValueError("A valid instrument key is required.")

        if unit not in self.VALID_UNITS:
            raise ValueError(f"Unsupported candle unit: {unit}")

        if interval not in self.VALID_UNITS[unit]:
            raise ValueError("Unsupported interval for the selected unit.")

        try:
            end = date.fromisoformat(to_date)
            start = date.fromisoformat(from_date) if from_date else None
        except (TypeError, ValueError) as exc:
            raise ValueError("Dates must use YYYY-MM-DD format.") from exc

        if start and start > end:
            raise ValueError("from_date cannot be after to_date.")

    def _extract_candles(self, response):
        if response.get("status") != "success":
            raise RuntimeError("Upstox historical candle request failed.")

        data = response.get("data", {})
        candles = data.get("candles")

        if not isinstance(candles, list):
            raise RuntimeError("Invalid candle response from Upstox.")

        return candles

    def get_historical_candles(
        self,
        instrument_key,
        unit,
        interval,
        to_date,
        from_date=None,
    ):
        self._validate(
            instrument_key, unit, interval, to_date, from_date
        )

        key = quote(instrument_key, safe="")
        endpoint = (
            f"/v3/historical-candle/{key}/{unit}/"
            f"{interval}/{to_date}"
        )

        if from_date:
            endpoint += f"/{from_date}"

        response = self.client.get(endpoint)
        return self._extract_candles(response)

    def get_intraday_candles(
        self,
        instrument_key,
        unit="minutes",
        interval=1,
    ):
        if not instrument_key or not isinstance(instrument_key, str):
            raise ValueError("A valid instrument key is required.")

        if unit not in ("minutes", "hours", "days"):
            raise ValueError("Unsupported intraday candle unit.")

        if interval not in self.VALID_UNITS[unit]:
            raise ValueError("Unsupported intraday interval.")

        key = quote(instrument_key, safe="")
        endpoint = (
            f"/v3/historical-candle/intraday/"
            f"{key}/{unit}/{interval}"
        )

        response = self.client.get(endpoint)
        return self._extract_candles(response)

    def close(self):
        self.client.close()
      
