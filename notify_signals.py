
import logging

from config import load_config
from signal_history import SignalHistory
from telegram_alerts import TelegramAlerts


logger = logging.getLogger(__name__)


class SignalNotifier:

    def __init__(self):
        self.config = load_config()
        self.history = SignalHistory()
        self.telegram = TelegramAlerts()

    def send(self, signal):
        """
        Send a validated BUY CALL or BUY PUT paper candidate
        to Telegram, with duplicate protection.
        """

        if not self.config["telegram"].get("enabled", False):
            logger.warning("Telegram notifications are disabled.")
            return False

        if signal.get("status") != "PAPER_CANDIDATE":
            logger.info("Signal is not a validated paper candidate.")
            return False

        if signal.get("signal") not in ("BUY_CALL", "BUY_PUT"):
            logger.info("No directional option signal to send.")
            return False

        if not signal.get("option", {}).get("instrument_key"):
            logger.warning("Option contract is missing.")
            return False

        # Check for a previously delivered signal. Save it only after Telegram
        # confirms delivery, so a temporary Telegram failure can be retried.
        if self.history.has_signal(signal):
            logger.info("Duplicate signal suppressed.")
            return False

        success = self.telegram.send_signal(signal)

        if not success:
            logger.error("Telegram delivery failed; signal remains retryable.")
            return False

        saved = self.history.save_signal(signal)
        if not saved:
            logger.warning(
                "Telegram delivered, but signal history could not record it."
            )

        logger.info(
            "Telegram signal delivered: %s %s",
            signal.get("commodity"),
            signal.get("signal"),
        )

        return success


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print(
        "Notifier module ready. "
        "It sends validated signals supplied by the scanner."
    )
