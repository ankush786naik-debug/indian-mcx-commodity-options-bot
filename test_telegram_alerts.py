from unittest.mock import Mock, patch

import pytest

from telegram_alerts import TelegramAlerts


def test_missing_credentials():
    telegram = TelegramAlerts(
        bot_token="",
        chat_id="",
    )

    assert telegram.send_message("Test") is False


def test_empty_message_rejected():
    telegram = TelegramAlerts(
        bot_token="test-token",
        chat_id="12345",
    )

    with pytest.raises(ValueError):
        telegram.send_message("")


def test_format_no_trade():
    telegram = TelegramAlerts(
        bot_token="test-token",
        chat_id="12345",
    )

    message = telegram.format_signal({
        "commodity": "GOLD",
        "signal": "NO_TRADE",
        "reason": "News risk detected",
    })

    assert "NO TRADE" in message
    assert "GOLD" in message


def test_format_buy_call():
    telegram = TelegramAlerts(
        bot_token="test-token",
        chat_id="12345",
    )

    message = telegram.format_signal({
        "commodity": "GOLD",
        "signal": "BUY_CALL",
        "entry": 250,
        "stop_loss": 200,
        "target1": 325,
        "target2": 375,
        "lots": 2,
        "technical_score": 85,
        "timestamp": "2026-11-18T10:30:00",
        "news_status": "CLEAR",
        "option": {
            "instrument_key": "MCX_TEST",
            "expiry": "2026-12-31",
            "strike": 70000,
        },
    })

    assert "BUY_CALL" in message
    assert "PAPER ONLY" in message
    assert "NO LIVE ORDER PLACED" in message


@patch("telegram_alerts.requests.post")
def test_successful_message(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    telegram = TelegramAlerts(
        bot_token="test-token",
        chat_id="12345",
    )

    assert telegram.send_message("Test alert") is True


@patch("telegram_alerts.requests.post")
def test_failed_message(mock_post):
    mock_post.side_effect = Exception("Network error")

    telegram = TelegramAlerts(
        bot_token="test-token",
        chat_id="12345",
    )

    assert telegram.send_message("Test alert") is False
