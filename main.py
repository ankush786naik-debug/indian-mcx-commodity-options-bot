
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from config import load_config
from historical_data import HistoricalData
from instruments import InstrumentMaster
from market_data import MarketData
from news_filter import NewsFilter
from notify_signals import SignalNotifier
from option_contracts import OptionContracts
from option_analysis import analyze_option_quote
from strategy import analyze_market


IST = ZoneInfo("Asia/Kolkata")

NEWS_FEEDS = [
    "https://news.google.com/rss/search?q=crude+oil+OR+OPEC+OR+petroleum&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=natural+gas+OR+LNG+OR+gas+storage&hl=en-IN&gl=IN&ceid=IN:en",
]


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def get_expiry(item):
    value = item.get("expiry")

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(
            value / 1000, tz=IST
        ).date()

    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    return None


def find_quote(quote_data, instrument):
    expected_keys = []

    segment = instrument.get("segment")
    symbol = instrument.get("trading_symbol")
    instrument_key = instrument.get("instrument_key")

    if segment and symbol:
        expected_keys.append(f"{segment}:{symbol}")

    if instrument_key:
        expected_keys.append(instrument_key.replace("|", ":"))

    for key in expected_keys:
        if key in quote_data:
            return quote_data[key]

    for quote in quote_data.values():
        if (
            isinstance(quote, dict)
            and quote.get("instrument_token") == instrument_key
        ):
            return quote

    return None


def quote_mismatch_detail(quote_data, instrument):
    expected = instrument.get("instrument_key", "unknown")
    symbol = instrument.get("trading_symbol", "unknown")
    returned = []

    if isinstance(quote_data, dict):
        for key, quote in list(quote_data.items())[:5]:
            if isinstance(quote, dict):
                token = quote.get("instrument_token") or quote.get("instrument_key")
                quote_symbol = quote.get("symbol") or quote.get("trading_symbol")
                returned.append(
                    "%s token=%s symbol=%s" % (key, token, quote_symbol)
                )
            else:
                returned.append(str(key))

    return (
        "Expected key=%s symbol=%s; returned=%s"
        % (expected, symbol, "; ".join(returned) if returned else "none")
    )[:350]


def candles_to_dataframe(candles):
    if not candles:
        raise ValueError("No historical candles returned.")

    rows = []

    for candle in candles:
        if len(candle) < 6:
            continue

        rows.append({
            "timestamp": candle[0],
            "open": candle[1],
            "high": candle[2],
            "low": candle[3],
            "close": candle[4],
            "volume": candle[5],
        })

    if not rows:
        raise ValueError("No usable OHLCV candles.")

    df = pd.DataFrame(rows)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], utc=True
    ).dt.tz_convert(IST)

    df = df.drop_duplicates(subset=["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")

    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(
        subset=["open", "high", "low", "close", "volume"]
    )

    return df


def get_market_data(history, instrument_key):
    now = datetime.now(IST)
    today = now.date()

    daily_start = today - timedelta(days=365)
    intraday_start = today - timedelta(days=28)

    daily = history.get_historical_candles(
        instrument_key,
        "days",
        1,
        today.isoformat(),
        daily_start.isoformat(),
    )

    fifteen = history.get_historical_candles(
        instrument_key,
        "minutes",
        15,
        today.isoformat(),
        intraday_start.isoformat(),
    )

    five = history.get_historical_candles(
        instrument_key,
        "minutes",
        5,
        today.isoformat(),
        intraday_start.isoformat(),
    )

    return (
        candles_to_dataframe(daily),
        candles_to_dataframe(fifteen),
        candles_to_dataframe(five),
    )


def make_signal(commodity, direction, score, contract,
                option_quote, market_analysis, news_status):

    entry = float(option_quote["ask"])
    stop_loss = round(entry * 0.80, 2)
    risk = entry - stop_loss

    return {
        "commodity": commodity,
        "signal": direction,
        "status": "PAPER_CANDIDATE",
        "technical_score": score,
        "option": {
            "instrument_key": contract["instrument_key"],
            "option_type": contract["instrument_type"],
            "expiry": contract["expiry"],
            "strike": contract["strike_price"],
            "lot_size": contract["lot_size"],
        },
        "entry": round(entry, 2),
        "stop_loss": stop_loss,
        "target1": round(entry + (risk * 1.5), 2),
        "target2": round(entry + (risk * 2.5), 2),
        "underlying_price": market_analysis["underlying_price"],
        "support": market_analysis.get("support"),
        "resistance": market_analysis.get("resistance"),
        "news_status": news_status,
        "reasons": market_analysis.get("reasons", []),
        "timestamp": datetime.now(IST).isoformat(),
        "execution_mode": "PAPER_ONLY",
    }


def scan_commodity(
    commodity, config, master, history, market,
    options_api, news_filter, notifier
):
    logger = logging.getLogger(__name__)
    logger.info("Scanning %s", commodity)

    def outcome(status, detail):
        return {"commodity": commodity, "status": status, "detail": str(detail)}

    futures = master.get_mcx_futures(commodity)
    today = datetime.now(IST).date()

    valid_futures = [
        item for item in futures
        if get_expiry(item) is not None
        and get_expiry(item) >= today
        and item.get("instrument_key")
    ]

    if not valid_futures:
        logger.warning("%s: no valid futures contract.", commodity)
        return outcome("SKIPPED", "No valid non-expired futures contract")

    future = min(valid_futures, key=lambda item: get_expiry(item))
    future_key = future["instrument_key"]

    future_quotes = market.get_market_quote([future_key])
    future_quote = find_quote(future_quotes, future)

    if not future_quote or float(future_quote.get("last_price", 0)) <= 0:
        logger.warning("%s: live futures quote unavailable.", commodity)
        return outcome(
            "NO_LIVE_QUOTE",
            quote_mismatch_detail(future_quotes, future)
            + "; no signal generated",
        )

    daily, fifteen, five = get_market_data(history, future_key)
    analysis = analyze_market(
        daily,
        fifteen,
        five,
        minimum_score=config["strategy"]["minimum_score"],
    )

    logger.info(
        "%s: %s | score %s",
        commodity,
        analysis["signal"],
        analysis["score"],
    )

    if analysis["signal"] == "NO_TRADE":
        reasons = analysis.get("reasons", [])
        detail = "Score %s; %s" % (
            analysis.get("score", "n/a"),
            ", ".join(map(str, reasons)) if reasons else "No qualifying setup",
        )
        return outcome("NO_TRADE", detail)

    news = news_filter.fetch_news()
    news_result = news_filter.evaluate(
        commodity,
        news["articles"],
        available=news["available"],
    )

    if not news_result["allow_trade"]:
        logger.warning(
            "%s: news filter blocked signal: %s",
            commodity,
            news_result["reason"],
        )
        return outcome("NEWS_BLOCKED", news_result["reason"])

    option_type = "CE" if analysis["signal"] == "BUY_CALL" else "PE"
    contracts = options_api.get_contracts(future_key)
    selected = options_api.select_contract(
        contracts,
        option_type,
        float(future_quote["last_price"]),
    )

    if not selected:
        logger.warning("%s: no suitable option contract.", commodity)
        return outcome("NO_OPTION_CONTRACT", "No eligible option contract selected")

    option_quotes = market.get_market_quote([selected["instrument_key"]])
    option_quote = find_quote(option_quotes, selected)

    if not option_quote:
        logger.warning("%s: option quote unavailable.", commodity)
        return outcome(
            "NO_OPTION_QUOTE",
            quote_mismatch_detail(option_quotes, selected),
        )

    option_result = analyze_option_quote(
        selected,
        option_quote,
        minimum_volume=config["options"]["minimum_volume"],
        minimum_open_interest=config["options"]["minimum_open_interest"],
        maximum_spread_percent=config["options"][
            "maximum_bid_ask_spread_percent"
        ],
    )

    if not option_result["eligible"]:
        reasons = ", ".join(option_result["reasons"])
        logger.warning("%s: option rejected: %s", commodity, reasons)
        return outcome("OPTION_REJECTED", reasons)

    signal = make_signal(
        commodity,
        analysis["signal"],
        analysis["score"],
        selected,
        option_result,
        analysis,
        news_result["status"],
    )

    if notifier.send(signal):
        logger.info("%s: Telegram signal sent.", commodity)
        return outcome(
            "SIGNAL_ALERT_SENT",
            "%s candidate sent; paper only" % analysis["signal"],
        )

    logger.warning("%s: signal alert not sent or duplicate.", commodity)
    return outcome(
        "SIGNAL_ALERT_NOT_CONFIRMED",
        "%s candidate existed; signal alert was not confirmed (duplicate or delivery issue)"
        % analysis["signal"],
    )


def format_scan_summary(results, started_at, fatal_error=None):
    lines = [
        "MCX BOT - SCAN REPORT",
        "Mode: PAPER ONLY",
        "Started (IST): %s" % started_at.isoformat(timespec="seconds"),
    ]

    if not results:
        lines.append("No commodity scan results were produced.")

    for result in results:
        detail = result.get("detail", "")
        lines.append(
            "%s: %s%s" % (
                result.get("commodity", "Unknown"),
                result.get("status", "UNKNOWN"),
                (" - " + detail) if detail else "",
            )
        )

    if fatal_error:
        lines.append("Scanner error: %s" % str(fatal_error)[:250])

    lines.append("Live orders: DISABLED")
    lines.append("No order was placed.")
    return "\n".join(lines)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    started_at = datetime.now(IST)

    config = load_config()
    if config["signals"]["live_orders_enabled"]:
        raise RuntimeError("Live order execution must remain disabled.")

    master = InstrumentMaster()
    history = HistoricalData()
    market = MarketData()
    options_api = OptionContracts()
    news_filter = NewsFilter(rss_feeds=NEWS_FEEDS)
    notifier = SignalNotifier()

    results = []
    fatal_error = None

    try:
        master.download()

        for commodity in config["commodities"]:
            if commodity not in ("CRUDEOIL", "NATURALGAS"):
                logger.warning("Skipping unsupported commodity: %s", commodity)
                results.append({
                    "commodity": commodity,
                    "status": "SKIPPED",
                    "detail": "Unsupported commodity",
                })
                continue

            try:
                result = scan_commodity(
                    commodity,
                    config,
                    master,
                    history,
                    market,
                    options_api,
                    news_filter,
                    notifier,
                )
                results.append(result or {
                    "commodity": commodity,
                    "status": "UNKNOWN",
                    "detail": "Scanner returned no status",
                })
            except Exception as exc:
                logger.exception("%s scan failed.", commodity)
                results.append({
                    "commodity": commodity,
                    "status": "ERROR",
                    "detail": "%s: %s" % (type(exc).__name__, str(exc)[:200]),
                })

    except Exception as exc:
        fatal_error = "%s: %s" % (type(exc).__name__, str(exc)[:250])
        logger.exception("MCX scanner setup or instrument download failed.")

    finally:
        for resource in (history, market, options_api, notifier.history):
            try:
                resource.close()
            except Exception:
                logger.exception("Resource cleanup failed.")

        summary = format_scan_summary(results, started_at, fatal_error)
        logger.info("Sending scan summary to Telegram.")
        delivered = notifier.telegram.send_message(summary)

        if not delivered:
            logger.critical(
                "Telegram scan summary could not be delivered. "
                "GitHub Actions failure notification will retry."
            )
            fatal_error = fatal_error or "Telegram scan summary delivery failed"

    logger.info("MCX scan completed. Paper-only mode.")

    if fatal_error or any(item.get("status") == "ERROR" for item in results):
        raise RuntimeError(
            fatal_error or "One or more commodity scans failed."
        )




if __name__ == "__main__":
    main()
    
