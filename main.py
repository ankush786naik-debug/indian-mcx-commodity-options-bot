import logging
from pathlib import Path

from config import load_config


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main():
    setup_logging()
    logger = logging.getLogger("mcx_scanner")

    try:
        config = load_config()
    except Exception:
        logger.exception("Configuration validation failed.")
        raise

    logger.info("MCX Commodity Options Bot starting.")
    logger.info("Mode: %s", config["app"]["mode"])
    logger.info(
        "Configured commodities: %s",
        ", ".join(config["commodities"]),
    )
    logger.info(
        "Signal threshold: %s/100",
        config["strategy"]["minimum_score"],
    )

    logger.info(
        "News filter enabled: %s",
        config["news_filter"]["enabled"],
    )

    logger.info(
        "Live orders enabled: %s",
        config["signals"]["live_orders_enabled"],
    )

    logger.info(
        "Startup checks completed. Market data integration is not "
        "configured yet; no trading signals have been generated."
    )


if __name__ == "__main__":
    main()
  
