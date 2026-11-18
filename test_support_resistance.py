import pandas as pd
import pytest

from support_resistance import (
    find_support_resistance,
    validate_price_data,
)


def sample_data():
    return pd.DataFrame({
        "high": [
            102, 104, 110, 105, 103,
            106, 108, 104, 102, 105,
            107, 103, 101, 104, 106,
            103, 105, 102, 104, 106,
        ],
        "low": [
            98, 99, 100, 97, 96,
            98, 99, 95, 94, 97,
            99, 96, 93, 97, 98,
            96, 98, 95, 97, 99,
        ],
        "close": [
            100, 102, 105, 101, 100,
            103, 104, 100, 98, 101,
            104, 100, 97, 101, 103,
            100, 102, 99, 101, 104,
        ],
    })


def test_returns_expected_keys():
    result = find_support_resistance(sample_data())

    expected = [
        "current_price",
        "support",
        "resistance",
        "support_levels",
        "resistance_levels",
        "support_distance_percent",
        "resistance_distance_percent",
    ]

    for key in expected:
        assert key in result


def test_support_below_current_price():
    result = find_support_resistance(sample_data())

    if result["support"] is not None:
        assert result["support"] < result["current_price"]


def test_resistance_above_current_price():
    result = find_support_resistance(sample_data())

    if result["resistance"] is not None:
        assert result["resistance"] > result["current_price"]


def test_insufficient_data():
    data = sample_data().head(5)

    with pytest.raises(ValueError):
        find_support_resistance(data)


def test_missing_column():
    data = sample_data().drop(columns=["high"])

    with pytest.raises(ValueError):
        validate_price_data(data)


def test_invalid_window():
    with pytest.raises(ValueError):
        find_support_resistance(sample_data(), window=1)
      
