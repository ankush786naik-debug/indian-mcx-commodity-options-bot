import pandas as pd

from indicators import add_indicators
from support_resistance import find_support_resistance


def _latest_values(df):
    if len(df) < 200:
        raise ValueError(
            "At least 200 candles are required for EMA 200 analysis."
        )

    result = add_indicators(df)
    latest = result.iloc[-1]

    required = [
        "close",
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "macd",
        "macd_signal",
        "atr_14",
    ]

    for column in required:
        if pd.isna(latest[column]):
            raise ValueError(
                f"Insufficient data for indicator: {column}"
            )

    return result, latest


def analyze_market(daily_df, fifteen_min_df, five_min_df, minimum_score=70):
    """
    Analyze the underlying commodity market.

    Returns BUY_CALL, BUY_PUT or NO_TRADE as a directional
    candidate. This does not select an option contract or
    authorize a trade.
    """

    if not 0 <= minimum_score <= 100:
        raise ValueError("minimum_score must be between 0 and 100.")

    daily, d = _latest_values(daily_df)
    fifteen, m15 = _latest_values(fifteen_min_df)
    five, m5 = _latest_values(five_min_df)

    score_call = 0
    score_put = 0
    reasons = []

    # Daily trend: maximum 30 points.
    if d["close"] > d["ema_200"]:
        score_call += 15
        reasons.append("Daily price above EMA 200")
    elif d["close"] < d["ema_200"]:
        score_put += 15
        reasons.append("Daily price below EMA 200")

    if d["ema_20"] > d["ema_50"]:
        score_call += 15
        reasons.append("Daily EMA 20 above EMA 50")
    elif d["ema_20"] < d["ema_50"]:
        score_put += 15
        reasons.append("Daily EMA 20 below EMA 50")

    # 15-minute confirmation: maximum 30 points.
    if m15["close"] > m15["ema_20"] > m15["ema_50"]:
        score_call += 15
        reasons.append("15-minute bullish EMA alignment")
    elif m15["close"] < m15["ema_20"] < m15["ema_50"]:
        score_put += 15
        reasons.append("15-minute bearish EMA alignment")

    if m15["macd"] > m15["macd_signal"]:
        score_call += 10
        reasons.append("15-minute MACD bullish")
    elif m15["macd"] < m15["macd_signal"]:
        score_put += 10
        reasons.append("15-minute MACD bearish")

    if 50 <= m15["rsi_14"] <= 70:
        score_call += 5
    elif 30 <= m15["rsi_14"] <= 50:
        score_put += 5

    # 5-minute entry confirmation: maximum 40 points.
    if m5["close"] > m5["ema_20"]:
        score_call += 10
        reasons.append("5-minute price above EMA 20")
    elif m5["close"] < m5["ema_20"]:
        score_put += 10
        reasons.append("5-minute price below EMA 20")

    if m5["macd"] > m5["macd_signal"]:
        score_call += 10
        reasons.append("5-minute MACD bullish")
    elif m5["macd"] < m5["macd_signal"]:
        score_put += 10
        reasons.append("5-minute MACD bearish")

    if 50 <= m5["rsi_14"] <= 70:
        score_call += 10
    elif 30 <= m5["rsi_14"] <= 50:
        score_put += 10

    # Avoid chasing an already extended move.
    if m5["rsi_14"] > 75:
        score_call -= 10
        reasons.append("Bullish momentum may be overextended")

    if m5["rsi_14"] < 25:
        score_put -= 10
        reasons.append("Bearish momentum may be overextended")

    levels = find_support_resistance(fifteen)

    # Final directional decision.
    if score_call >= minimum_score and score_call > score_put:
        signal = "BUY_CALL"
        score = score_call
    elif score_put >= minimum_score and score_put > score_call:
        signal = "BUY_PUT"
        score = score_put
    else:
        signal = "NO_TRADE"
        score = max(score_call, score_put)

    return {
        "signal": signal,
        "score": max(0, min(100, score)),
        "call_score": max(0, min(100, score_call)),
        "put_score": max(0, min(100, score_put)),
        "underlying_price": float(m5["close"]),
        "daily_trend": (
            "BULLISH" if d["close"] > d["ema_200"]
            else "BEARISH"
        ),
        "support": levels["support"],
        "resistance": levels["resistance"],
        "atr": float(m5["atr_14"]),
        "reasons": reasons,
        "status": "DIRECTIONAL_CANDIDATE_ONLY",
    }
  
