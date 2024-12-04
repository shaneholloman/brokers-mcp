from datetime import datetime, timedelta
from logging import getLogger

import pytz
from ib_insync import Stock
from mcp import Tool
from mcp.types import TextContent

from ..client import ib
from ..common import ibkr_tool_prefix
from ..global_state import qualify_contracts
from ...common import list_items

logger = getLogger(__name__)

tools = [
    Tool(
        name=f"{ibkr_tool_prefix}_get_news_headlines",
        description="Fetch news headlines for a symbol in a specific date range",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The symbol to get news for"},
                "days_back": {"type": "number", "description": "The number of days back to fetch news headlines for"},
            },
            "required": ["symbol", "days_back"]
        }
    ),
    Tool(
        name=f"{ibkr_tool_prefix}_get_news_article",
        description="Fetch a news article body by its id",
        inputSchema={
            "type": "object",
            "properties": {
                "article_id": {"type": "number", "description": "The id of the article to fetch"},
            },
            "required": ["article_id"]
        }
    ),
]

async def handler(name, arguments):
    if name == f"{ibkr_tool_prefix}_get_news_headlines":
        stock = Stock(arguments["symbol"], "SMART", "USD")
        stock = (await qualify_contracts(stock))[0]
        news = await ib.reqHistoricalNewsAsync(
            stock.conId,
            providerCodes="BRFG+BRFUPDN+DJ-N+DJ-RT+DJ-RTA+DJ-RTE+DJ-RTG+DJNL",
            startDateTime=datetime.now(tz=pytz.timezone("US/Eastern")) - timedelta(days=arguments["days_back"]),
            endDateTime=datetime.now(pytz.timezone("US/Eastern")),
            totalResults=50
        )
        return [
            TextContent(
                type="text",
                text=list_items(news)
            )
        ]
    elif name == f"{ibkr_tool_prefix}_get_news_article":
        return [
            TextContent(
                type="text",
                text=str(await ib.reqNewsArticleAsync(
                    article_id=arguments["article_id"]
                ))
            )
        ]
