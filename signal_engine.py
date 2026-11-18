
from datetime import datetime
from risk_management import calculate_trade_risk


def generate_signal(
    commodity,
    market_analysis,
    news_analysis,
    option_analysis,
    selected_contract,
    capital,
    minimum_score=70,
):
    """
    Combine validated analysis into a paper-trading candidate.

    This function does not place orders.
    """

    def no_trade(reason):
        return {
            "commodity": commodity,
            "signal": "NO_TRADE",
            "status": "REJECTED",
            "reason": reason,
            "timestamp": datetime.now().astimezone().isoformat(),
        }

    if not isinstance(market_analysis, dict):
        return no_trade("Invalid market analysis.")

    if not isinstance(news_analysis, dict):
        return no_trade("Invalid news analysis.")

    if not isinstance(option_analysis, dict):
        return no_trade("Invalid option analysis.")

    if market_analysis.get("signal") not in ("BUY_CALL", "BUY_PUT"):
        return no_trade("No directional market signal.")

    if market_analysis.get("score", 0) < minimum_score:
        return no_trade("Technical score below minimum threshold.")

    if news_analysis.get("allow_trade") is not True:
        return no_trade("News filter blocked the trade.")

    if option_analysis.get("eligible") is not True:
        return no_trade("Option liquidity checks failed.")

    if not isinstance(selected_contract, dict):
        return no_trade("No valid option contract selected.")

    expected_type = (
        "CE" if market_analysis["signal"] == "BUY_CALL" else "PE"
    )

    if selected_contract.get("instrument_type") != expected_type:
        return no_trade("Option type does not match market direction.")

    if (
        not selected_contract.get("instrument_key")
        or selected_contract.get("expiry") is None
    ):
        return no_trade("Contract instrument key or expiry missing.")

    if (
        option_analysis.get("instrument_key")
        != selected_contract.get("instrument_key")
    ):
        return no_trade("Option quote does not match selected contract.")

    if option_analysis.get("lot_size") != selected_contract.get("lot_size"):
        return no_trade("Option lot size mismatch.")

    entry = option_analysis.get("ask")

    if entry is None:
        return no_trade("Executable ask price unavailable.")

    try:
        entry = float(entry)
        lot_size = int(selected_contract["lot_size"])
        score = float(market_analysis["score"])
    except (ValueError, TypeError, KeyError):
        return no_trade("Invalid contract or market values.")

    if entry <= 0 or lot_size <= 0:
        return no_trade("Invalid entry premium or lot size.")

    if not 0 <= score <= 100:
        return no_trade("Invalid technical score.")

    try:
        risk = calculate_trade_risk(
            entry_price=entry,
            lot_size=lot_size,
            capital=capital,
        )
    except (ValueError, TypeError) as exc:
        return no_trade(f"Risk validation failed: {exc}")

    if risk["lots"] < 1:
        return no_trade("Insufficient capital for one risk-compliant lot.")

    return {
        "commodity": commodity,
        "signal": market_analysis["signal"],
        "status": "PAPER_CANDIDATE",
        "technical_score": score,
        "option": {
            "instrument_key": selected_contract["instrument_key"],
            "option_type": expected_type,
            "expiry": selected_contract["expiry"],
            "strike": selected_contract["strike_price"],
            "lot_size": lot_size,
        },
        "entry": risk["entry"],
        "stop_loss": risk["stop_loss"],
        "target1": risk["target1"],
        "target2": risk["target2"],
        "lots": risk["lots"],
        "quantity": risk["quantity"],
        "position_value": risk["position_value"],
        "maximum_planned_loss": risk["maximum_planned_loss"],
        "underlying_price": market_analysis.get("underlying_price"),
        "support": market_analysis.get("support"),
        "resistance": market_analysis.get("resistance"),
        "news_status": news_analysis.get("status"),
        "reasons": market_analysis.get("reasons", []),
        "timestamp": datetime.now().astimezone().isoformat(),
        "execution_mode": "PAPER_ONLY",
  }
  
