def analyze_option_quote(
    contract,
    quote,
    minimum_volume=1,
    minimum_open_interest=1,
    maximum_spread_percent=3.0,
):
    """
    Evaluate an option contract using its live market quote.

    Returns an eligibility result, not a trade instruction.
    """

    reasons = []

    if not isinstance(contract, dict) or not isinstance(quote, dict):
        raise ValueError("Contract and quote must be dictionaries.")

    instrument_key = contract.get("instrument_key")
    lot_size = contract.get("lot_size")

    if not instrument_key:
        reasons.append("Missing instrument key")

    try:
        lot_size = int(lot_size)
        if lot_size <= 0:
            raise ValueError
    except (ValueError, TypeError):
        reasons.append("Invalid lot size")
        lot_size = None

    try:
        ltp = float(quote["last_price"])
        if ltp <= 0:
            raise ValueError
    except (ValueError, TypeError, KeyError):
        ltp = None
        reasons.append("Invalid option premium")

    try:
        volume = int(quote.get("volume", 0))
        oi = int(quote.get("oi", 0))

        if volume < 0 or oi < 0:
            raise ValueError
    except (ValueError, TypeError):
        volume = 0
        oi = 0
        reasons.append("Invalid volume or open interest")

    depth = quote.get("depth", {})
    buy = depth.get("buy", []) if isinstance(depth, dict) else []
    sell = depth.get("sell", []) if isinstance(depth, dict) else []

    bid = None
    ask = None

    if buy and isinstance(buy[0], dict):
        bid = buy[0].get("price")

    if sell and isinstance(sell[0], dict):
        ask = sell[0].get("price")

    try:
        bid = float(bid)
        ask = float(ask)

        if bid <= 0 or ask <= 0 or ask < bid:
            raise ValueError

    except (ValueError, TypeError):
        bid = None
        ask = None
        reasons.append("Valid bid/ask prices unavailable")

    spread_percent = None

    if bid is not None and ask is not None:
        midpoint = (bid + ask) / 2

        if midpoint > 0:
            spread_percent = ((ask - bid) / midpoint) * 100

    if volume < minimum_volume:
        reasons.append("Insufficient trading volume")

    if oi < minimum_open_interest:
        reasons.append("Insufficient open interest")

    if spread_percent is not None:
        if spread_percent > maximum_spread_percent:
            reasons.append("Bid/ask spread too wide")

    eligible = len(reasons) == 0

    return {
        "instrument_key": instrument_key,
        "eligible": eligible,
        "ltp": ltp,
        "bid": bid,
        "ask": ask,
        "spread_percent": spread_percent,
        "volume": volume,
        "open_interest": oi,
        "lot_size": lot_size,
        "reasons": reasons,
    }
  
