import logging

from upstox_client import UpstoxClient


logger = logging.getLogger(__name__)


class MarketData:
    def __init__(self, client=None):
        self.client = client or UpstoxClient()

    def get_market_quote(self, instrument_keys):
        """
        Retrieve quotes for one or more instruments.

        instrument_keys must contain valid Upstox instrument keys.
        Example: ["NSE_INDEX|Nifty 50"]
        """

        if isinstance(instrument_keys, str):
            instrument_keys = [instrument_keys]

        if not instrument_keys:
            raise ValueError("At least one instrument key is required.")

        if not all(
            isinstance(key, str) and key.strip()
            for key in instrument_keys
        ):
            raise ValueError("Invalid instrument key.")

        result = self.client.get(
            "/v2/market-quote/quotes",
            params={"instrument_key": ",".join(instrument_keys)},
        )

        if result.get("status") != "success":
            raise RuntimeError(
                "Upstox did not return a successful market quote response."
            )

        data = result.get("data")

        if not isinstance(data, dict):
            raise RuntimeError("Unexpected market quote response.")

        return data

    def get_ltp(self, instrument_keys):
        """
        Retrieve last traded prices for instruments.
        """

        if isinstance(instrument_keys, str):
            instrument_keys = [instrument_keys]

        if not instrument_keys:
            raise ValueError("At least one instrument key is required.")

        result = self.client.get(
            "/v2/market-quote/ltp",
            params={"instrument_key": ",".join(instrument_keys)},
        )

        if result.get("status") != "success":
            raise RuntimeError(
                "Upstox did not return a successful LTP response."
            )

        data = result.get("data")

        if not isinstance(data, dict):
            raise RuntimeError("Unexpected LTP response.")

        return data

    def close(self):
        self.client.close()
      
