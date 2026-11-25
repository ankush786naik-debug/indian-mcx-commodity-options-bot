
import logging
import os
import re
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
    """Match Upstox quote keys safely, including MCX symbol-style keys."""
    if not isinstance(quote_data, dict) or not isinstance(instrument, dict):
        return None

    def normalize(value):
        return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())

    segment = instrument.get("segment")
    instrument_key = instrument.get("instrument_key")
    symbol = instrument.get("trading_symbol")
    expected = set()

    if segment and symbol:
        expected.add(f"{segment}:{symbol}")
    if instrument_key:
        expected.add(instrument_key.replace("|", ":"))

    # Upstox's MCX quote endpoint may key the response by trading symbol,
    # e.g. MCX_FO:CRUDEOIL26DECFUT, rather than MCX_FO|<numeric token>.
    base = (
        instrument.get("underlying_symbol")
        or instrument.get("name")
        or instrument.get("short_name")
    )
    expiry = get_expiry(instrument)
    instrument_type = str(instrument.get("instrument_type", "")).upper()

    if base and expiry and instrument_type in ("FUT", "CE", "PE"):
        base = re.sub(r"[^A-Z0-9]", "", str(base).upper())
        expiry_code = expiry.strftime("%y%b").upper()
        if instrument_type == "FUT":
            suffix = "FUT"
        else:
            strike = instrument.get("strike_price")
            try:
                strike_value = float(strike)
                strike_text = str(int(strike_value)) if strike_value.is_integer() else str(strike_value)
                suffix = f"{strike_text}{instrument_type}"
            except (TypeError, ValueError):
                suffix = instrument_type
        if base and suffix:
            expected.add(f"{segment}:{base}{expiry_code}{suffix}")

    expected_normalized = {normalize(key) for key in expected}

    for key, quote in quote_data.items():
        if normalize(key) in expected_normalized:
            return quote

        if not isinstance(quote, dict):
            continue

        # Some API responses also include the canonical key in the quote body.
        quote_keys = (
            quote.get("instrument_key"),
            quote.get("instrument_token"),
            quote.get("trading_symbol"),
            quote.get("symbol"),
        )
        if any(normalize(value) in expected_normalized for value in quote_keys if value):
            return quote

    return None

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
        return {"commodity": commodity, "status": "NO_DATA", "reason": "No valid unexpired futures contract."}

    future = min(valid_futures, key=lambda item: get_expiry(item))
    future_key = future["instrument_key"]

    future_quotes = market.get_market_quote([future_key])
    future_quote = find_quote(future_quotes, future)

    if not future_quote or float(future_quote.get("last_price", 0)) <= 0:
        logger.warning("%s: live futures quote unavailable.", commodity)
        return {"commodity": commodity, "status": "NO_DATA", "reason": "Fresh futures quote unavailable or could not be matched."}

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
        return {
            "commodity": commodity,
            "status": "NO_TRADE",
            "reason": f"Technical score {analysis['score']}; no qualifying setup.",
            "score": analysis["score"],
        }

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
        return {"commodity": commodity, "status": "BLOCKED", "reason": news_result["reason"]}

    option_type = (
        "CE" if analysis["signal"] == "BUY_CALL" else "PE"
    )

    contracts = options_api.get_contracts(future_key)

    selected = options_api.select_contract(
        contracts,
        option_type,
        float(future_quote["last_price"]),
    )

    if not selected:
        logger.warning("%s: no suitable option contract.", commodity)
        return {"commodity": commodity, "status": "NO_DATA", "reason": "No suitable option contract."}

    option_quotes = market.get_market_quote(
        [selected["instrument_key"]]
    )

    option_quote = find_quote(option_quotes, selected)

    if not option_quote:
        logger.warning("%s: option quote unavailable.", commodity)
        return {"commodity": commodity, "status": "NO_DATA", "reason": "Option quote unavailable or could not be matched."}

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
        logger.warning(
            "%s: option rejected: %s",
            commodity,
            ", ".join(option_result["reasons"]),
        )
        return {"commodity": commodity, "status": "REJECTED", "reason": ", ".join(option_result["reasons"])}

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
        return {"commodity": commodity, "status": "SIGNAL_SENT", "reason": analysis["signal"]}
    logger.warning("%s: signal delivery failed or was already sent.", commodity)
    return {"commodity": commodity, "status": "SIGNAL_NOT_SENT", "reason": analysis["signal"]}


def format_run_summary(outcomes, started_at):
    lines = [
        "MCX SCANNER RUN REPORT",
        "Mode: PAPER ONLY - NO LIVE ORDER",
        f"Started: {started_at}",
    ]
    run_id = os.getenv("GITHUB_RUN_ID")
    if run_id:
        lines.append(f"GitHub Actions run: {run_id}")

    if not outcomes:
        lines.append("Result: scanner produced no commodity outcomes.")
    else:
        for item in outcomes:
            lines.append(
                f"{item.get('commodity', 'SYSTEM')}: "
                f"{item.get('status', 'UNKNOWN')} - "
                f"{item.get('reason', '')}"
            )

    lines.append("This is a status report, not a trade recommendation.")
    return "\n".join(lines)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    started_at = datetime.now(IST).isoformat()
    outcomes = []
    resources = []
    notifier = SignalNotifier()
    summary_delivered = False
    fatal_error = None

    try:
        config = load_config()

        if config["signals"]["live_orders_enabled"]:
            raise RuntimeError("Live order execution must remain disabled.")

        master = InstrumentMaster()
        history = HistoricalData()
        market = MarketData()
        options_api = OptionContracts()
        news_filter = NewsFilter(rss_feeds=NEWS_FEEDS)
        resources = [history, market, options_api]

        master.download()

        for commodity in config["commodities"]:
            if commodity not in ("CRUDEOIL", "NATURALGAS"):
                logger.warning("Skipping unsupported commodity: %s", commodity)
                outcomes.append({
                    "commodity": commodity,
                    "status": "SKIPPED",
                    "reason": "Unsupported commodity.",
                })
                continue

            try:
                outcome = scan_commodity(
                    commodity,
                    config,
                    master,
                    history,
                    market,
                    options_api,
                    news_filter,
                    notifier,
                )
                outcomes.append(outcome or {
                    "commodity": commodity,
                    "status": "NO_RESULT",
                    "reason": "Scanner returned no outcome.",
                })
            except Exception as exc:
                logger.exception("%s scan failed.", commodity)
                outcomes.append({
                    "commodity": commodity,
                    "status": "ERROR",
                    "reason": f"{type(exc).__name__}: {str(exc)[:240]}",
                })

    except Exception as exc:
        fatal_error = exc
        logger.exception("MCX scanner run failed.")
        outcomes.append({
            "commodity": "SYSTEM",
            "status": "ERROR",
            "reason": f"{type(exc).__name__}: {str(exc)[:240]}",
        })

    finally:
        for resource in resources:
            try:
                resource.close()
            except Exception:
                logger.exception("Failed to close scanner resource.")

        try:
            summary = format_run_summary(outcomes, started_at)
            summary_delivered = notifier.send_status(summary)
            if not summary_delivered:
                logger.error("Telegram run summary was not delivered.")
        except Exception:
            logger.exception("Could not send Telegram run summary.")

        try:
            notifier.history.close()
        except Exception:
            logger.exception("Could not close signal history.")

    if not summary_delivered:
        raise RuntimeError(
            "Telegram run summary delivery failed. "
            "Check GitHub Actions logs and Telegram secrets."
        )

    if fatal_error or any(item.get("status") == "ERROR" for item in outcomes):
        raise RuntimeError(
            "One or more scanner components failed; see run report and logs."
        )

    logger.info("MCX scan completed. Telegram run report delivered. Paper-only mode.")


if __name__ == "__main__":
    main()
    
