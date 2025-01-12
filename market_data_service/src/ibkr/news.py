from datetime import datetime, timedelta
from logging import getLogger

import re
import pytz

from common_lib.util import list_items, datetime_to_time_ago
from common_lib.ib import get_ib, get_contract

logger = getLogger(__name__)

async def get_news_headlines(
    symbol: str,
    days_back: int
) -> str:
    """Fetch news headlines for a symbol in a specific date range
    
    Args:
        symbol: The symbol to get news for
        days_back: The number of days back to fetch news headlines for
        
    Returns:
        str: List of news headlines
    """
    ib = get_ib()
    stock = await get_contract(symbol, "stock")
    start_date = datetime.now(tz=pytz.timezone("US/Eastern")) - timedelta(days=days_back)
    end_date = datetime.now(tz=pytz.timezone("US/Eastern"))
    news = await ib.reqHistoricalNewsAsync(
        stock.conId,
        providerCodes="BRFG+BRFUPDN+DJ-N+DJ-RT+DJ-RTA+DJ-RTE+DJ-RTG+DJNL",
        startDateTime=start_date,
        endDateTime=end_date,
        totalResults=50
    )
    
    # Convert news timestamp to "how long ago"
    edited = []
    for news_item in news:
        if news_item.time < start_date.replace(tzinfo=None):
            break
        time_ago_string = datetime_to_time_ago(news_item.time)
        news_item = news_item._replace(headline=re.sub(r'\{.*?\}', '', news_item.headline).strip())
        edited.append(news_item._replace(time=time_ago_string))

    return list_items(edited)

async def get_news_article(
    article_id: str,
    provider_code: str
) -> str:
    """Fetch a news article body by its id
    
    Args:
        article_id: The id of the article to fetch
        provider_code: The provider code of the article to fetch
        
    Returns:
        str: The article body
    """
    ib = get_ib()
    article = await ib.reqNewsArticleAsync(
        provider_code,
        article_id
    )
    return str(article)
