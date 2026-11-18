from news_filter import NewsFilter


def test_news_unavailable_blocks_trade():
    news = NewsFilter()

    result = news.evaluate(
        "GOLD",
        articles=[],
        available=False,
    )

    assert result["allow_trade"] is False
    assert result["status"] == "UNAVAILABLE"


def test_gold_risk_headline_blocks_trade():
    news = NewsFilter()

    articles = [
        {
            "title": "Gold supply disruption after sanctions",
            "summary": "Precious metals market faces uncertainty.",
        }
    ]

    result = news.evaluate(
        "GOLD",
        articles,
        available=True,
    )

    assert result["allow_trade"] is False
    assert result["status"] == "RISK_DETECTED"


def test_unrelated_news_does_not_block():
    news = NewsFilter()

    articles = [
        {
            "title": "Technology companies report earnings",
            "summary": "Technology stocks remain in focus.",
        }
    ]

    result = news.evaluate(
        "GOLD",
        articles,
        available=True,
    )

    assert result["allow_trade"] is True


def test_crude_oil_news_matching():
    news = NewsFilter()

    articles = [
        {
            "title": "OPEC announces production cut",
            "summary": "Oil supply may be affected.",
        }
    ]

    result = news.evaluate(
        "CRUDEOIL",
        articles,
        available=True,
    )

    assert result["allow_trade"] is False


def test_news_does_not_generate_directional_signal():
    news = NewsFilter()

    result = news.evaluate(
        "SILVER",
        articles=[],
        available=True,
    )

    assert "signal" not in result
    assert "BUY_CALL" not in result
    assert "BUY_PUT" not in result
  
