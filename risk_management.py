def calculate_trade_risk(
    entry_price,
    lot_size,
    capital,
    risk_percent=1.0,
    stop_loss_percent=20.0,
    target1_r=1.5,
    target2_r=2.5,
):
    """
    Calculate preliminary long-option paper-trading risk levels.

    Entry is assumed to be the actual executable ask price.
    These percentage-based levels must be validated through
    backtesting before being used for trading decisions.
    """

    if entry_price <= 0:
        raise ValueError("Entry price must be positive.")

    if lot_size <= 0:
        raise ValueError("Lot size must be positive.")

    if capital <= 0:
        raise ValueError("Capital must be positive.")

    if not 0 < risk_percent <= 100:
        raise ValueError("Risk percentage must be between 0 and 100.")

    if not 0 < stop_loss_percent < 100:
        raise ValueError("Stop loss percentage must be between 0 and 100.")

    if target1_r <= 0 or target2_r <= target1_r:
        raise ValueError("Targets must be positive and increasing.")

    entry = float(entry_price)
    lot_size = int(lot_size)

    risk_budget = capital * risk_percent / 100

    stop_distance = entry * stop_loss_percent / 100
    stop_loss = entry - stop_distance

    target1 = entry + (stop_distance * target1_r)
    target2 = entry + (stop_distance * target2_r)

    risk_per_lot = stop_distance * lot_size
    premium_per_lot = entry * lot_size

    affordable_lots = int(capital // premium_per_lot)
    risk_limited_lots = int(risk_budget // risk_per_lot)

    lots = min(affordable_lots, risk_limited_lots)

    return {
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "target1": round(target1, 2),
        "target2": round(target2, 2),
        "risk_budget": round(risk_budget, 2),
        "risk_per_lot": round(risk_per_lot, 2),
        "premium_per_lot": round(premium_per_lot, 2),
        "lots": lots,
        "quantity": lots * lot_size,
        "position_value": round(lots * premium_per_lot, 2),
        "maximum_planned_loss": round(lots * risk_per_lot, 2),
        "status": "PAPER_TRADE_RISK_CALCULATION",
    }
  
