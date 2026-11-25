import pytest

from risk_management import calculate_trade_risk


def test_basic_risk_calculation():
    result = calculate_trade_risk(
        entry_price=250,
        lot_size=100,
        capital=100000,
    )

    assert result["entry"] == 250
    assert result["stop_loss"] == 200
    assert result["target1"] == 325
    assert result["target2"] == 375


def test_position_sizing():
    result = calculate_trade_risk(
        entry_price=250,
        lot_size=100,
        capital=1000000,
    )

    assert result["lots"] == 2
    assert result["quantity"] == 200
    assert result["position_value"] == 50000
    assert result["maximum_planned_loss"] == 10000



def test_risk_budget():
    result = calculate_trade_risk(
        entry_price=250,
        lot_size=100,
        capital=100000,
        risk_percent=1,
    )

    assert result["risk_budget"] == 1000


def test_zero_entry_rejected():
    with pytest.raises(ValueError):
        calculate_trade_risk(
            entry_price=0,
            lot_size=100,
            capital=100000,
        )


def test_invalid_lot_size_rejected():
    with pytest.raises(ValueError):
        calculate_trade_risk(
            entry_price=250,
            lot_size=0,
            capital=100000,
        )


def test_invalid_capital_rejected():
    with pytest.raises(ValueError):
        calculate_trade_risk(
            entry_price=250,
            lot_size=100,
            capital=0,
        )


def test_target_order():
    with pytest.raises(ValueError):
        calculate_trade_risk(
            entry_price=250,
            lot_size=100,
            capital=100000,
            target1_r=2.5,
            target2_r=1.5,
        )


def test_zero_lots_when_capital_insufficient():
    result = calculate_trade_risk(
        entry_price=1000,
        lot_size=100,
        capital=1000,
    )

    assert result["lots"] == 0
    assert result["quantity"] == 0
