import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from instruments import InstrumentMaster
from market_data import MarketData


IST = ZoneInfo("Asia/Kolkata")

COMMODITIES = [
    "GOLD",
    "GOLDM",
    "SILVER",
    "SILVERM",
    "CRUDEOIL",
    "NATURALGAS",
    "COPPER",
]


def get_expiry(item):
    value = item.get("expiry")

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(
            value / 1000,
            tz=IST,
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

    nearest = min(get_expiry(item) for item in valid)

    return [
        item for item in valid
        if get_expiry(item) == nearest
    ], nearest


def run_diagnostics():
    logging.basicConfig(level=logging.INFO)

    master = InstrumentMaster()
    market = MarketData()

    report = {
        "checked_at": datetime.now(IST).isoformat(),
        "exchange": "MCX",
        "commodities": {},
    }

    try:
        master.download()

        futures_to_check = {}

        for commodity in COMMODITIES:
            futures = master.get_mcx_futures(commodity)
            options = master.get_option_contracts(commodity)

            selected_futures, future_expiry = nearest_contracts(
                futures
            )

            selected_options, option_expiry = nearest_contracts(
                options
            )

            if selected_futures:
                futures_to_check[commodity] = (
                    selected_futures[0]
                )

            report["commodities"][commodity] = {
                "futures_found": len(futures),
                "options_found": len(options),
                "nearest_future_expiry": (
                    future_expiry.isoformat()
                    if future_expiry else None
                ),
                "nearest_option_expiry": (
                    option_expiry.isoformat()
                    if option_expiry else None
                ),
                "future_quote_available": False,
                "call_quote_available": False,
                "put_quote_available": False,
            }

        if not futures_to_check:
            raise RuntimeError(
                "No valid MCX futures contracts found."
            )

        future_keys = [
            item["instrument_key"]
            for item in futures_to_check.values()
        ]

        future_quotes = market.get_market_quote(future_keys)

        option_keys = []
        option_map = {}

        for commodity, future in futures_to_check.items():
            quote = future_quotes.get(future["instrument_key"])

            if not isinstance(quote, dict):
                continue

            price = quote.get("last_price")

            if not isinstance(price, (int, float)) or price <= 0:
                continue

            report["commodities"][commodity][
                "future_quote_available"
            ] = True

            options = master.get_option_contracts(commodity)
            selected_options, _ = nearest_contracts(options)

            if not selected_options:
                continue

            for option_type in ("CE", "PE"):
                candidates = [
                    item for item in selected_options
                    if item.get("instrument_type") == option_type
                ]

                if not candidates:
                    continue

                candidate = min(
                    candidates,
                    key=lambda item: abs(
                        float(item.get("strike_price", 0)) - price
                    ),
                )

                key = candidate.get("instrument_key")

                if key:
                    option_keys.append(key)
                    option_map[key] = (commodity, option_type)

        if option_keys:
            option_quotes = market.get_market_quote(
                option_keys[:500]
            )

            for key, (commodity, option_type) in option_map.items():
                quote = option_quotes.get(key)

                available = (
                    isinstance(quote, dict)
                    and isinstance(
                        quote.get("last_price"),
                        (int, float),
                    )
                    and quote.get("last_price", 0) > 0
                )

                field = (
                    "call_quote_available"
                    if option_type == "CE"
                    else "put_quote_available"
                )

                report["commodities"][commodity][field] = available

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
              
