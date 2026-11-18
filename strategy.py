
import pandas as pd

from indicators import add_indicators
from support_resistance import find_support_resistance


def _latest_values(df, minimum_candles=200, daily_fallback=False):
    if daily_fallback:
        if len(df) < 50:
            raise ValueError(
                "At least 50 daily candles are required for trend analysis."
            )
    elif len(df) < minimum_candles:
        raise ValueError(
            f"At least {minimum_candles} candles are required "
            "for EMA 200 analysis."
        )

    result = add_indicators(df)
    latest = result.iloc[-1]

    required = [
        "close",
        "ema_20",
        "ema_50",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
        "atr_14",
    ]

    for column in required:
        if pd.isna(latest[column]):
            raise ValueError(
                f"Insufficient data for indicator: {column}"
            )

    if not daily_fallback or len(df) >= 200:
        if pd.isna(latest["ema_200"]):
            raise ValueError("Insufficient data for EMA 200 analysis.")

    return result, latest


def _valid_value(value):
    return pd.notna(value) and value is not None


def analyze_market(daily_df, fifteen_min_df, five_min_df, minimum_score=70):
    """
    Conservative multi-timeframe commodity options signal candidate.

    Uses daily trend, 15-minute confirmation and 5-minute entry.
    Returns BUY_CALL, BUY_PUT or NO_TRADE.

    This function does not select contracts, calculate position
    size or place orders.
    """

    if not 0 <= minimum_score <= 100:
        raise ValueError("minimum_score must be between 0 and 100.")

    daily, d = _latest_values(
        daily_df,
        daily_fallback=True
    )

    fifteen, m15 = _latest_values(fifteen_min_df)
    five, m5 = _latest_values(five_min_df)

    # Validate indicators required for the new confirmation rules.
    for column in ["adx_14", "plus_di_14", "minus_di_14"]:
        if not _valid_value(m15[column]):
            raise ValueError(
                f"Insufficient 15-minute data for {column}."
            )

    for column in ["vwap", "relative_volume"]:
        if not _valid_value(m5[column]):
            raise ValueError(
                f"Insufficient 5-minute data for {column}."
            )

    daily_ema_basis = (
        "EMA 200" if len(daily_df) >= 200 else "EMA 50 fallback"
    )

    daily_trend_ema = (
        d["ema_200"] if len(daily_df) >= 200 else d["ema_50"]
    )

    # Establish the higher-timeframe direction.
    if d["close"] > daily_trend_ema and d["ema_20"] > d["ema_50"]:
        daily_trend = "BULLISH"
    elif d["close"] < daily_trend_ema and d["ema_20"] < d["ema_50"]:
        daily_trend = "BEARISH"
    else:
        daily_trend = "NEUTRAL"

    score_call = 0
    score_put = 0
    reasons = []

    # 1. Daily trend: maximum 20 points.
    if daily_trend == "BULLISH":
        score_call += 20
        reasons.append(f"Daily trend bullish using {daily_ema_basis}")
    elif daily_trend == "BEARISH":
        score_put += 20
        reasons.append(f"Daily trend bearish using {daily_ema_basis}")

    # 2. Fifteen-minute trend alignment: maximum 15 points.
    bullish_15m = (
        m15["close"] > m15["ema_20"] > m15["ema_50"]
    )

    bearish_15m = (
        m15["close"] < m15["ema_20"] < m15["ema_50"]
    )

    if bullish_15m:
        score_call += 15
        reasons.append("15-minute bullish EMA alignment")
    elif bearish_15m:
        score_put += 15
        reasons.append("15-minute bearish EMA alignment")

    # 3. Trend strength and direction: maximum 15 points.
    strong_trend = m15["adx_14"] >= 18

    if strong_trend and m15["plus_di_14"] > m15["minus_di_14"]:
        score_call += 15
        reasons.append("15-minute ADX confirms bullish directional strength")
    elif strong_trend and m15["minus_di_14"] > m15["plus_di_14"]:
        score_put += 15
        reasons.append("15-minute ADX confirms bearish directional strength")

    # 4. Five-minute price and VWAP confirmation: maximum 20 points.
    bullish_entry = (
        m5["close"] > m5["ema_20"]
        and m5["close"] > m5["vwap"]
    )

    bearish_entry = (
        m5["close"] < m5["ema_20"]
        and m5["close"] < m5["vwap"]
    )

    if bullish_entry:
        score_call += 20
        reasons.append("5-minute price above EMA 20 and VWAP")
    elif bearish_entry:
        score_put += 20
        reasons.append("5-minute price below EMA 20 and VWAP")

    # 5. MACD momentum: maximum 10 points.
    if m5["macd_histogram"] > 0:
        score_call += 10
        reasons.append("5-minute MACD histogram positive")
    elif m5["macd_histogram"] < 0:
        score_put += 10
        reasons.append("5-minute MACD histogram negative")

    # 6. RSI momentum confirmation: maximum 10 points.
    if 52 <= m5["rsi_14"] <= 70:
        score_call += 10
        reasons.append("5-minute RSI supports bullish momentum")
    elif 30 <= m5["rsi_14"] <= 48:
        score_put += 10
        reasons.append("5-minute RSI supports bearish momentum")

    # 7. Relative volume: maximum 10 points.
    if m5["relative_volume"] >= 1.2:
        if bullish_entry:
            score_call += 10
            reasons.append("Bullish entry supported by relative volume")
        elif bearish_entry:
            score_put += 10
            reasons.append("Bearish entry supported by relative volume")

    # Support and resistance from 15-minute candles.
    levels = find_support_resistance(fifteen)

    support = levels.get("support")
    resistance = levels.get("resistance")
    atr = float(m5["atr_14"])
    price = float(m5["close"])

    # Avoid entering directly into nearby opposing levels.
    call_blocked = (
        _valid_value(resistance)
        and float(resistance) > price
        and (float(resistance) - price) <= 0.5 * atr
    )

    put_blocked = (
        _valid_value(support)
        and float(support) < price
        and (price - float(support)) <= 0.5 * atr
    )

    if call_blocked:
        reasons.append("BUY_CALL blocked: resistance is too close")

    if put_blocked:
        reasons.append("BUY_PUT blocked: support is too close")

    # Strict multi-timeframe agreement.
    call_confirmed = (
        daily_trend == "BULLISH"
        and bullish_15m
        and strong_trend
        and m15["plus_di_14"] > m15["minus_di_14"]
        and bullish_entry
        and m5["macd_histogram"] > 0
        and 52 <= m5["rsi_14"] <= 70
        and m5["relative_volume"] >= 1.2
        and not call_blocked
    )

    put_confirmed = (
        daily_trend == "BEARISH"
        and bearish_15m
        and strong_trend
        and m15["minus_di_14"] > m15["plus_di_14"]
        and bearish_entry
        and m5["macd_histogram"] < 0
        and 30 <= m5["rsi_14"] <= 48
        and m5["relative_volume"] >= 1.2
        and not put_blocked
    )

    if (
        call_confirmed
        and score_call >= minimum_score
        and score_call > score_put
    ):
        signal = "BUY_CALL"
        score = score_call

    elif (
        put_confirmed
        and score_put >= minimum_score
        and score_put > score_call
    ):
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
        "underlying_price": price,
        "daily_trend": daily_trend,
        "daily_trend_basis": daily_ema_basis,
        "support": support,
        "resistance": resistance,
        "atr": atr,
        "adx": float(m15["adx_14"]),
        "plus_di": float(m15["plus_di_14"]),
        "minus_di": float(m15["minus_di_14"]),
        "rsi": float(m5["rsi_14"]),
        "relative_volume": float(m5["relative_volume"]),
        "vwap": float(m5["vwap"]),
        "reasons": reasons,
        "status": "DIRECTIONAL_CANDIDATE_ONLY",
        }
    
