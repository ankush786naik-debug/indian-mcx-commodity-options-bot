import pytest

from signal_history import SignalHistory


@pytest.fixture
def history(tmp_path):
    return SignalHistory(tmp_path / "signals.db")


def sample_signal():
    return {
        "commodity": "GOLD",
        "signal": "BUY_CALL",
        "status": "PAPER_CANDIDATE",
        "entry": 251.0,
        "stop_loss": 200.8,
        "target1": 326.3,
        "target2": 376.5,
        "lots": 2,
        "timestamp": "2026-11-18T10:30:00+05:30",
        "option": {
            "instrument_key": "MCX_FO|GOLD_TEST_CE",
            "expiry": "2026-12-31",
            "strike": 70000,
        },
    }


def test_save_signal(history):
    assert history.save_signal(sample_signal()) is True


def test_duplicate_signal_rejected(history):
    signal = sample_signal()

    assert history.save_signal(signal) is True
    assert history.save_signal(signal) is False


def test_recent_signals(history):
    history.save_signal(sample_signal())

    results = history.get_recent_signals()

    assert len(results) == 1
    assert results[0]["commodity"] == "GOLD"
    assert results[0]["signal"] == "BUY_CALL"


def test_invalid_signal_type(history):
    signal = sample_signal()
    signal["signal"] = "BUY_STOCK"

    with pytest.raises(ValueError):
        history.save_signal(signal)


def test_invalid_limit(history):
    with pytest.raises(ValueError):
        history.get_recent_signals(0)


def test_empty_history(history):
    assert history.get_recent_signals() == []
  
