import numpy as np
import pandas as pd


def validate_ohlcv(df):
    required = ["open", "high", "low", "close", "volume"]

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if len(df) < 2:
        raise ValueError("At least two candles are required.")

    result = df.copy()

    for col in required:
        result[col] = pd.to_numeric(result[col], errors="coerce")

    if result[required].isnull().any().any():
        raise ValueError("OHLCV data contains invalid values.")

    if (result["volume"] < 0).any():
        raise ValueError("Volume cannot be negative.")

    if (
        (result["high"] < result["low"]).any()
        or (result["high"] < result["close"]).any()
        or (result["low"] > result["close"]).any()
    ):
        raise ValueError("Invalid OHLC candle values.")

    return result


def calculate_ema(series, period):
    return series.ewm(
        span=period,
        adjust=False,
        min_periods=period
    ).mean()


def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100)
    rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0)

    return rsi


def calculate_atr(df, period=14):
    previous_close = df["close"].shift(1)

    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


def calculate_vwap(df):
    typical_price = (
        df["high"] + df["low"] + df["close"]
    ) / 3

    if isinstance(df.index, pd.DatetimeIndex):
        session = df.index.date
    elif "timestamp" in df.columns:
        session = pd.to_datetime(df["timestamp"]).dt.date
    else:
        session = pd.Series(0, index=df.index)

    price_volume = typical_price * df["volume"]

    cumulative_pv = price_volume.groupby(session).cumsum()
    cumulative_volume = df["volume"].groupby(session).cumsum()

    return cumulative_pv / cumulative_volume.replace(0, np.nan)


def add_indicators(df):
    result = validate_ohlcv(df)

    result["ema_20"] = calculate_ema(result["close"], 20)
    result["ema_50"] = calculate_ema(result["close"], 50)
    result["ema_200"] = calculate_ema(result["close"], 200)

    result["rsi_14"] = calculate_rsi(result["close"], 14)

    ema_12 = calculate_ema(result["close"], 12)
    ema_26 = calculate_ema(result["close"], 26)

    result["macd"] = ema_12 - ema_26
    result["macd_signal"] = calculate_ema(result["macd"], 9)
    result["macd_histogram"] = (
        result["macd"] - result["macd_signal"]
    )

    result["atr_14"] = calculate_atr(result, 14)

    result["average_volume"] = (
        result["volume"].rolling(20, min_periods=20).mean()
    )

    result["relative_volume"] = (
        result["volume"] / result["average_volume"].replace(0, np.nan)
    )

    result["vwap"] = calculate_vwap(result)

    return result
  
