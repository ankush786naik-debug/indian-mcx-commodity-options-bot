import pytest

from paper_trading import PaperTrading


@pytest.fixture
def simulator(tmp_path):
    return PaperTrading(tmp_path / "paper_test.db")


def sample_signal():
    return {
        "status": "PAPER_CANDIDATE",
        "signal": "BUY_CALL",
        "entry": 250.0,
        "stop_loss": 200.0,
        "target1": 325.0,
        "target2": 375.0,
        "quantity": 100,
        "option": {
            "instrument_key": "MCX_FO|GOLD_TEST_CE",
        },
    }


def test_open_paper_trade(simulator):
    trade_id = simulator.open_trade(sample_signal())

    assert trade_id > 0

    trades = simulator.get_open_trades()

    assert len(trades) == 1
    assert trades[0]["status"] == "OPEN"


def test_stop_loss_execution(simulator):
    trade_id = simulator.open_trade(sample_signal())

    result = simulator.update_trade(trade_id, 195)

    assert result["status"] == "STOP_LOSS"
    assert result["pnl"] == -5500


def test_target1_execution(simulator):
    trade_id = simulator.open_trade(sample_signal())

    result = simulator.update_trade(trade_id, 325)

    assert result["status"] == "TARGET1"
    assert result["pnl"] == 7500


def test_target2_execution(simulator):
    trade_id = simulator.open_trade(sample_signal())

    result = simulator.update_trade(trade_id, 375)

    assert result["status"] == "TARGET2"
    assert result["pnl"] == 12500


def test_trade_remains_open(simulator):
    trade_id = simulator.open_trade(sample_signal())

    result = simulator.update_trade(trade_id, 270)

    assert result["status"] == "OPEN"


def test_invalid_signal_rejected(simulator):
    signal = sample_signal()
    signal["status"] = "REJECTED"

    with pytest.raises(ValueError):
        simulator.open_trade(signal)


def test_invalid_quantity_rejected(simulator):
    signal = sample_signal()
    signal["quantity"] = 0

    with pytest.raises(ValueError):
        simulator.open_trade(signal)


def test_invalid_price_rejected(simulator):
    trade_id = simulator.open_trade(sample_signal())

    with pytest.raises(ValueError):
        simulator.update_trade(trade_id, 0)


def test_closed_trade_not_updated_again(simulator):
    trade_id = simulator.open_trade(sample_signal())

    simulator.update_trade(trade_id, 195)

    result = simulator.update_trade(trade_id, 375)

    assert result["status"] == "STOP_LOSS"
  
