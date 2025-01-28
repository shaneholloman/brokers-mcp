from datetime import datetime, timedelta
from alpaca.data.requests import NewsRequest
from common_lib.alpaca_helpers.async_impl.news_client import AsyncNewsClient
from mcp.server.fastmcp.resources import ResourceTemplate
from common_lib.util import datetime_to_time_ago
from common_lib.alpaca_helpers.env import AlpacaSettings

settings = AlpacaSettings()
news_client = AsyncNewsClient(settings.api_key, settings.api_secret)


async def get_news(symbols: str, days_back: int = 1) -> str:
    """
    Get news for a list of symbols, separated by commas

    Args:
        symbols: list[str]
        days_back: int = 1

    Returns:
        str
    """
    request = NewsRequest(
        symbols=symbols,
        start=datetime.now() - timedelta(days=days_back),
        end=datetime.now(),
        sort="asc",
    )
    all_news = []
    news = await news_client.get_news(request)
    all_news.extend(news.data["news"])
    while news.next_page_token:
        request.next_page_token = news.next_page_token
        news = news_client.get_news(request)
        all_news.extend(news.data["news"])

    news_string = ""
    for news_item in all_news:
        when = datetime_to_time_ago(news_item.updated_at)
        news_string += f"*{news_item.headline}*\n{when}\n{news_item.summary}\n\n"

    return news_string or "No news found"


async def latest_headline(symbol: str) -> str:
    request = NewsRequest(
        symbols=symbol,
        start=datetime.now() - timedelta(hours=4),
        end=datetime.now(),
        sort="desc",
    )
    news_items = (await news_client.get_news(request)).data["news"]
    if len(news_items) == 0:
        return "No headline from the past 4 hours"

    return (
        f"*{news_items[0].headline}*\n{datetime_to_time_ago(news_items[0].updated_at)}"
    )


latest_headline_resource = ResourceTemplate(
    uri_template="news://latest_headline/{symbol}",
    name="Get the latest headline for a symbol",
    description="Get the latest headline for a symbol",
    fn=latest_headline,
    parameters={
        "symbol": {
            "type": "string",
            "description": "The symbol to get the latest headline for",
            "required": True,
        }
    },
)
