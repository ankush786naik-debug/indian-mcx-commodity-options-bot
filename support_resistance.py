import pandas as pd


def validate_price_data(df):
    required = ["high", "low", "close"]

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if len(df) < 10:
        raise ValueError("At least 10 candles are required.")

    if df[required].isnull().any().any():
        raise ValueError("Price data contains missing values.")

    return df.copy()


def find_support_resistance(df, window=5):
    """
    Find recent confirmed swing levels.

    The latest candle is excluded from swing detection to avoid
    treating an unfinished candle as a confirmed level.
    """

    if window < 2:
        raise ValueError("Window must be at least 2.")

    data = validate_price_data(df)

    highs = data["high"].astype(float)
    lows = data["low"].astype(float)
    current_price = float(data["close"].iloc[-1])

    # Exclude latest candle from confirmed swing calculations.
    confirmed_highs = highs.iloc[:-1]
    confirmed_lows = lows.iloc[:-1]

    swing_high = (
        confirmed_highs
        == confirmed_highs.rolling(
            window * 2 + 1,
            center=True,
            min_periods=window * 2 + 1,
        ).max()
    )

    swing_low = (
        confirmed_lows
        == confirmed_lows.rolling(
            window * 2 + 1,
            center=True,
            min_periods=window * 2 + 1,
        ).min()
    )

    resistance_levels = sorted(
        set(
            float(value)
            for value in confirmed_highs[swing_high].dropna()
            if value > current_price
        )
    )

    support_levels = sorted(
        set(
            float(value)
            for value in confirmed_lows[swing_low].dropna()
            if value < current_price
        ),
        reverse=True,
    )

    nearest_support = (
        support_levels[0] if support_levels else None
    )

    nearest_resistance = (
        resistance_levels[0] if resistance_levels else None
    )

    support_distance = (
        (current_price - nearest_support) / current_price * 100
        if nearest_support is not None and current_price > 0
        else None
    )

    resistance_distance = (
        (nearest_resistance - current_price) / current_price * 100
        if nearest_resistance is not None and current_price > 0
        else None
    )

    return {
        "current_price": current_price,
        "support": nearest_support,
        "resistance": nearest_resistance,
        "support_levels": support_levels,
        "resistance_levels": resistance_levels,
        "support_distance_percent": support_distance,
        "resistance_distance_percent": resistance_distance,
    }
  
