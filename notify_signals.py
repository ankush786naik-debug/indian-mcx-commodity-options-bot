
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

        # Save first to prevent duplicate notifications.
        saved = self.history.save_signal(signal)

        if not saved:
            logger.info("Duplicate signal suppressed.")
            return False

        success = self.telegram.send_signal(signal)

        if success:
            logger.info(
                "Telegram signal sent: %s %s",
                signal.get("commodity"),
                signal.get("signal"),
            )
        else:
            logger.error("Telegram delivery failed.")

        return success


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print(
        "Notifier module ready. "
        "It sends validated signals supplied by the scanner."
    )
