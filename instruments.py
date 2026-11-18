import csv
import gzip
import io
import logging
from datetime import date

import requests


logger = logging.getLogger(__name__)


class InstrumentMaster:
    INSTRUMENT_URL = (
        "https://assets.upstox.com/market-quote/instruments/"
        "exch_complete.json.gz"
    )

    def __init__(self, timeout=60):
        self.timeout = timeout
        self.instruments = []

    def download(self):
        response = requests.get(
            self.INSTRUMENT_URL,
            timeout=self.timeout,
        )
        response.raise_for_status()

        content = response.content

        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)

        try:
            import json
            records = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError(
                "Unable to parse Upstox instrument master."
            ) from exc

        if not isinstance(records, list):
            raise RuntimeError(
                "Unexpected instrument master format."
            )

        self.instruments = records
        logger.info("Downloaded %s instrument records.", len(records))
        return records

    def get_mcx_instruments(self):
        if not self.instruments:
            self.download()

        return [
            item for item in self.instruments
            if str(item.get("segment", "")).upper().startswith("MCX")
        ]

    def search_commodity(self, commodity):
        """
        Search MCX instruments by trading symbol or name.
        This returns candidates, not a guarantee that an option
        contract is currently tradable.
        """

        commodity = commodity.upper().strip()

        if not commodity:
            raise ValueError("Commodity name is required.")

        matches = []

        for item in self.get_mcx_instruments():
            symbol = str(item.get("trading_symbol", "")).upper()
            name = str(item.get("name", "")).upper()

            if commodity in symbol or commodity in name:
                matches.append(item)

        return matches

    def get_option_contracts(self, commodity):
        """
        Return option candidates for further validation.
        """

        matches = self.search_commodity(commodity)

        return [
            item for item in matches
            if "OPT" in str(item.get("instrument_type", "")).upper()
            or "OPTION" in str(item.get("instrument_type", "")).upper()
        ]
      
