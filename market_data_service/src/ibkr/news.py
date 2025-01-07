from datetime import datetime, timedelta
import os
from typing import Annotated
from logging import getLogger

from ib_insync import IB
import pytz

from src.common import datetime_to_time_ago, list_items
from src.ibkr.global_state import get_contract
from src.ibkr import client as ib_client

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
    ib = ib_client.get_ib()
    stock = await get_contract(symbol, "stock")
    
    news = await ib.reqHistoricalNewsAsync(
        stock.conId,
        providerCodes="BRFG+BRFUPDN+DJ-N+DJ-RT+DJ-RTA+DJ-RTE+DJ-RTG+DJNL",
        startDateTime=datetime.now(tz=pytz.timezone("US/Eastern")) - timedelta(days=days_back),
        endDateTime=datetime.now(tz=pytz.timezone("US/Eastern")),
        totalResults=50
    )
    
    # Convert news timestamp to "how long ago"
    edited = []
    for news_item in news:
        time_ago_string = datetime_to_time_ago(news_item.time)
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
    ib = ib_client.get_ib()
    article = await ib.reqNewsArticleAsync(
        provider_code,
        article_id
    )
    return str(article)
