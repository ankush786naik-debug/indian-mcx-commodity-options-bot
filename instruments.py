
import gzip
import json
import logging
import re

import requests


logger = logging.getLogger(__name__)


class InstrumentMaster:
    INSTRUMENT_URL = (
        "https://assets.upstox.com/market-quote/"
        "instruments/exchange/MCX.json.gz"
    )

    COMMODITIES = {
        "GOLD": ["GOLD"],
        "GOLDM": ["GOLDM"],
        "SILVER": ["SILVER"],
        "SILVERM": ["SILVERM"],
        "CRUDEOIL": ["CRUDEOIL"],
        "NATURALGAS": ["NATURALGAS"],
        "COPPER": ["COPPER"],
    }

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
            records = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError(
                "Unable to parse MCX instrument master."
            ) from exc

        if not isinstance(records, list):
            raise RuntimeError("Unexpected instrument master format.")

        self.instruments = [
            item for item in records
            if isinstance(item, dict)
            and item.get("segment") == "MCX_FO"
        ]

        logger.info(
            "Loaded %s MCX instruments.",
            len(self.instruments),
        )

        return self.instruments

    def get_mcx_instruments(self):
        if not self.instruments:
            self.download()

        return self.instruments

    def search_commodity(self, commodity):
        commodity = commodity.upper().strip()

        if commodity not in self.COMMODITIES:
            raise ValueError(f"Unsupported commodity: {commodity}")

        patterns = [
            re.compile(r"\b" + re.escape(alias) + r"\b")
            for alias in self.COMMODITIES[commodity]
        ]

        results = []

        for item in self.get_mcx_instruments():
            searchable = " ".join([
                str(item.get("name", "")),
                str(item.get("underlying_symbol", "")),
                str(item.get("trading_symbol", "")),
                str(item.get("short_name", "")),
            ]).upper()

            if any(pattern.search(searchable) for pattern in patterns):
                results.append(item)

        return results

    def get_mcx_futures(self, commodity):
        return [
            item for item in self.search_commodity(commodity)
            if item.get("instrument_type") == "FUT"
        ]

    def get_option_contracts(self, commodity):
        return [
            item for item in self.search_commodity(commodity)
            if item.get("instrument_type") in ("CE", "PE")
        ]
        
