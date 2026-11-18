from pathlib import Path
import yaml


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.yaml"


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_FILE}"
        )

    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("config.yaml must contain a YAML mapping.")

    validate_config(config)
    return config


def validate_config(config):
    required_sections = [
        "app",
        "commodities",
        "timeframes",
        "strategy",
        "options",
        "news_filter",
        "signals",
        "telegram",
        "reports",
    ]

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing configuration section: {section}")

    if config["app"].get("mode") != "paper":
        raise ValueError("Only paper trading mode is supported.")

    if config["signals"].get("live_orders_enabled") is not False:
        raise ValueError("Live order execution must remain disabled.")

    if config["news_filter"].get("mode") != "filter_only":
        raise ValueError("News must be used as a filter only.")

    score = config["strategy"].get("minimum_score", 0)
    if not 0 <= score <= 100:
        raise ValueError("minimum_score must be between 0 and 100.")

    if not config["commodities"]:
        raise ValueError("At least one commodity must be configured.")


if __name__ == "__main__":
    settings = load_config()
    print("Configuration loaded successfully.")
    print("Mode:", settings["app"]["mode"])
    print("Commodities:", ", ".join(settings["commodities"]))
    
