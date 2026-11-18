
import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from instruments import InstrumentMaster
from market_data import MarketData


IST = ZoneInfo("Asia/Kolkata")

COMMODITIES = [
    "GOLD", "GOLDM", "SILVER", "SILVERM",
    "CRUDEOIL", "NATURALGAS", "COPPER",
]


def get_expiry(item):
    value = item.get("expiry")

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(
            value / 1000, tz=IST
        ).date()

    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    return None


def nearest_contracts(contracts):
    today = datetime.now(IST).date()

    valid = [
        item for item in contracts
        if get_expiry(item) is not None
        and get_expiry(item) >= today
    ]

    if not valid:
        return [], None

    expiry = min(get_expiry(item) for item in valid)

    return [
        item for item in valid
        if get_expiry(item) == expiry
    ], expiry


def find_quote(quote_data, instrument):
    """
    Match Upstox response using instrument_token or
    exchange:trading_symbol response key.
    """

    instrument_key = instrument.get("instrument_key")
    segment = instrument.get("segment")
    symbol = instrument.get("trading_symbol")

    expected_keys = []

    if segment and symbol:
        expected_keys.append(f"{segment}:{symbol}")

    if instrument_key:
        expected_keys.append(instrument_key.replace("|", ":"))

    for key in expected_keys:
        if key in quote_data:
            return quote_data[key]

    for quote in quote_data.values():
        if (
            isinstance(quote, dict)
            and quote.get("instrument_token") == instrument_key
        ):
            return quote

    return None


def valid_quote(quote):
    return (
        isinstance(quote, dict)
        and isinstance(quote.get("last_price"), (int, float))
        and quote.get("last_price", 0) > 0
    )


def run_diagnostics():
    logging.basicConfig(level=logging.INFO)

    master = InstrumentMaster()
    market = MarketData()

    report = {
        "checked_at": datetime.now(IST).isoformat(),
        "exchange": "MCX",
        "commodities": {},
        "quote_response_keys": [],
    }

    try:
        master.download()

        futures_to_check = {}
        options_to_check = {}

        for commodity in COMMODITIES:
            futures = master.get_mcx_futures(commodity)
            options = master.get_option_contracts(commodity)

            selected_futures, future_expiry = nearest_contracts(futures)
            selected_options, option_expiry = nearest_contracts(options)

            report["commodities"][commodity] = {
                "futures_found": len(futures),
                "options_found": len(options),
                "nearest_future_expiry": (
                    future_expiry.isoformat() if future_expiry else None
                ),
                "nearest_option_expiry": (
                    option_expiry.isoformat() if option_expiry else None
                ),
                "future_quote_available": False,
                "call_quote_available": False,
                "put_quote_available": False,
                "future_price": None,
            }

            if selected_futures:
                futures_to_check[commodity] = selected_futures[0]

            if selected_options:
                options_to_check[commodity] = selected_options

        future_keys = [
            item["instrument_key"]
            for item in futures_to_check.values()
            if item.get("instrument_key")
        ]

        future_data = {}

        if future_keys:
            future_data = market.get_market_quote(future_keys)

        report["quote_response_keys"] = list(future_data.keys())[:20]

        for commodity, instrument in futures_to_check.items():
            quote = find_quote(future_data, instrument)

            if valid_quote(quote):
                report["commodities"][commodity][
                    "future_quote_available"
                ] = True

                report["commodities"][commodity][
                    "future_price"
                ] = quote["last_price"]

        option_instruments = []

        for commodity, contracts in options_to_check.items():
            underlying_price = report["commodities"][commodity][
                "future_price"
            ]

            if not underlying_price:
                continue

            for option_type in ("CE", "PE"):
                candidates = [
                    item for item in contracts
                    if item.get("instrument_type") == option_type
                ]

                if not candidates:
                    continue

                selected = min(
                    candidates,
                    key=lambda item: abs(
                        float(item.get("strike_price", 0))
                        - underlying_price
                    ),
                )

                option_instruments.append(
                    (commodity, option_type, selected)
                )

        option_keys = [
            item[2]["instrument_key"]
            for item in option_instruments
            if item[2].get("instrument_key")
        ]

        option_data = {}

        if option_keys:
            for start in range(0, len(option_keys), 500):
                batch = option_keys[start:start + 500]
                batch_data = market.get_market_quote(batch)
                option_data.update(batch_data)

        for commodity, option_type, instrument in option_instruments:
            quote = find_quote(option_data, instrument)

            field = (
                "call_quote_available"
                if option_type == "CE"
                else "put_quote_available"
            )

            report["commodities"][commodity][field] = valid_quote(quote)

        return report

    finally:
        market.close()


if __name__ == "__main__":
    try:
        result = run_diagnostics()
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({
            "status": "DIAGNOSTIC_FAILED",
            "error": str(exc),
        }, indent=2))
        raise
    
