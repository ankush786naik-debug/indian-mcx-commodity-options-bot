import os
import logging
import time

import requests


logger = logging.getLogger(__name__)


class TelegramAlerts:
    API_URL = "https://api.telegram.org"

    def __init__(
        self, bot_token=None, chat_id=None, timeout=15,
        retries=3, retry_delay=2,
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.timeout = timeout
        self.retries = max(1, int(retries))
        self.retry_delay = max(0, float(retry_delay))

    def send_message(self, message):
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram credentials are not configured.")
            return False

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Telegram message cannot be empty.")

        url = f"{self.API_URL}/bot{self.bot_token}/sendMessage"

        for attempt in range(self.retries):
            try:
                response = requests.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "disable_web_page_preview": True,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                result = response.json()

                if result.get("ok") is True:
                    logger.info("Telegram message delivered.")
                    return True

                description = result.get("description", "unknown Telegram error")
                logger.warning(
                    "Telegram rejected message (attempt %s/%s): %s",
                    attempt + 1, self.retries, description,
                )

            except (requests.RequestException, ValueError) as exc:
                logger.warning(
                    "Telegram delivery attempt %s/%s failed: %s",
                    attempt + 1, self.retries, type(exc).__name__,
                )

            if attempt + 1 < self.retries:
                time.sleep(self.retry_delay * (2 ** attempt))

        logger.error("Telegram delivery failed after %s attempts.", self.retries)
        return False

    def format_signal(self, signal):
        if signal.get("signal") == "NO_TRADE":
            return (
                f"MCX SIGNAL: NO TRADE\n"
                f"Commodity: {signal.get('commodity', 'Unknown')}\n"
                f"Reason: {signal.get('reason', 'No valid setup')}"
            )

        option = signal.get("option", {})

        return (
            "MCX PAPER TRADING SIGNAL\n"
            "------------------------\n"
            f"Commodity: {signal.get('commodity')}\n"
            f"Signal: {signal.get('signal')}\n"
            f"Contract: {option.get('instrument_key')}\n"
            f"Expiry: {option.get('expiry')}\n"
            f"Strike: {option.get('strike')}\n"
            f"Entry: {signal.get('entry')}\n"
            f"Stop Loss: {signal.get('stop_loss')}\n"
            f"Target 1: {signal.get('target1')}\n"
            f"Target 2: {signal.get('target2')}\n"
            f"Lots: {signal.get('lots')}\n"
            f"Score: {signal.get('technical_score')}/100\n"
            f"News: {signal.get('news_status')}\n"
            f"Time: {signal.get('timestamp')}\n"
            "\nPAPER ONLY - NO LIVE ORDER PLACED"
        )

    def send_signal(self, signal):
        return self.send_message(self.format_signal(signal))
