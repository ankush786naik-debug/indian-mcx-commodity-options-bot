import logging
import re
from datetime import datetime, timedelta, timezone

import feedparser


logger = logging.getLogger(__name__)


COMMODITY_KEYWORDS = {
    "GOLD": ["gold", "bullion", "precious metals"],
    "GOLDM": ["gold", "bullion", "precious metals"],
    "SILVER": ["silver", "precious metals"],
    "SILVERM": ["silver", "precious metals"],
    "CRUDEOIL": ["crude oil", "oil prices", "opec", "petroleum"],
    "NATURALGAS": ["natural gas", "lng", "gas storage"],
    "COPPER": ["copper", "base metals", "copper supply"],
}

RISK_KEYWORDS = [
    "war",
    "attack",
    "sanctions",
    "emergency",
    "explosion",
    "supply disruption",
    "production cut",
    "export ban",
    "export restriction",
    "central bank decision",
    "interest rate decision",
    "inflation report",
    "inventory shock",
    "hurricane",
    "earthquake",
]


class NewsFilter:
    def __init__(self, rss_feeds=None, timeout=15):
        self.rss_feeds = rss_feeds or []
        self.timeout = timeout

    def fetch_news(self):
        """
        Fetch RSS headlines.

        An empty feed list or feed failure is treated as unavailable.
        """
        articles = []
        successful_feeds = 0

        for feed_url in self.rss_feeds:
            try:
                parsed = feedparser.parse(
                    feed_url,
                    request_headers={"User-Agent": "MCXNewsFilter/1.0"},
                )

                if getattr(parsed, "bozo", False) and not parsed.entries:
                    logger.warning("RSS feed could not be parsed.")
                    continue

                successful_feeds += 1

                for entry in parsed.entries:
                    articles.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "published": entry.get("published", ""),
                        "link": entry.get("link", ""),
                    })

            except Exception:
                logger.exception("RSS feed retrieval failed.")

        return {
            "articles": articles,
            "available": successful_feeds > 0,
        }

    @staticmethod
    def _matches_commodity(article, commodity):
        keywords = COMMODITY_KEYWORDS.get(commodity.upper(), [])

        text = (
            str(article.get("title", "")) + " " +
            str(article.get("summary", ""))
        ).lower()

        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _contains_risk_keyword(article):
        text = (
            str(article.get("title", "")) + " " +
            str(article.get("summary", ""))
        ).lower()

        return any(
            re.search(r"\b" + re.escape(keyword) + r"\b", text)
            for keyword in RISK_KEYWORDS
        )

    def evaluate(self, commodity, articles, available=True):
        """
        Evaluate news as a trading filter only.

        No sentiment score or directional signal is generated.
        """
        if not available:
            return {
                "status": "UNAVAILABLE",
                "allow_trade": False,
                "risk_headlines": [],
                "reason": "News source unavailable.",
            }

        relevant = [
            article for article in articles
            if self._matches_commodity(article, commodity)
        ]

        risks = [
            article for article in relevant
            if self._contains_risk_keyword(article)
        ]

        if risks:
            return {
                "status": "RISK_DETECTED",
                "allow_trade": False,
                "risk_headlines": risks,
                "reason": "Potential commodity-related event risk detected.",
            }

        return {
            "status": "NO_KEYWORD_RISK_DETECTED",
            "allow_trade": True,
            "risk_headlines": [],
            "reason": (
                "No configured risk keywords detected. "
                "This does not establish that the market is safe."
            ),
        }
      
