
import numpy as np
import pandas as pd
import pytest

from indicators import (
    add_indicators,
    calculate_rsi,
    calculate_atr,
    calculate_adx,
    validate_ohlcv,
)


def sample_data(rows=250):
    dates = pd.date_range(
        "2026-01-01",
        periods=rows,
        freq="5min",
    )

    close = np.linspace(100, 150, rows)

    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(rows, 1000),
        },
        index=dates,
    )


def test_indicator_columns():
    result = add_indicators(sample_data())

    expected = [
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
        "atr_14",
        "adx_14",
        "plus_di_14",
        "minus_di_14",
        "relative_volume",
        "vwap",
    ]

    for column in expected:
        assert column in result.columns


def test_ema_200_available():
    result = add_indicators(sample_data(250))
    assert not pd.isna(result["ema_200"].iloc[-1])


def test_rsi_range():
    result = add_indicators(sample_data())
    latest_rsi = result["rsi_14"].iloc[-1]
    assert 0 <= latest_rsi <= 100


def test_atr_positive():
    result = add_indicators(sample_data())
    assert result["atr_14"].iloc[-1] > 0


def test_adx_and_directional_indicators():
    result = add_indicators(sample_data(250))

    adx = result["adx_14"].iloc[-1]
    plus_di = result["plus_di_14"].iloc[-1]
    minus_di = result["minus_di_14"].iloc[-1]

    assert np.isfinite(adx)
    assert np.isfinite(plus_di)
    assert np.isfinite(minus_di)

    assert 0 <= adx <= 100
    assert 0 <= plus_di <= 100
    assert 0 <= minus_di <= 100

    # Sample data trends upward.
    assert plus_di > minus_di


def test_calculate_adx_returns_three_series():
    adx, plus_di, minus_di = calculate_adx(sample_data())

    assert isinstance(adx, pd.Series)
    assert isinstance(plus_di, pd.Series)
    assert isinstance(minus_di, pd.Series)


def test_invalid_ohlcv():
    data = sample_data()
    data.loc[data.index[-1], "high"] = 50

    with pytest.raises(ValueError):
        validate_ohlcv(data)


def test_missing_volume():
    data = sample_data().drop(columns=["volume"])

    with pytest.raises(ValueError):
        validate_ohlcv(data)


def test_rsi_flat_market():
    close = pd.Series([100.0] * 30)
    result = calculate_rsi(close, 14)

    assert np.isnan(result.iloc[-1])
        
