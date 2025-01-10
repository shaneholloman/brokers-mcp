import logging
from textwrap import dedent
import nest_asyncio
nest_asyncio.apply()

from dotenv import load_dotenv
load_dotenv()

from common_lib.ib import connect_ib
from common_lib.mcp import AsyncioFastMCP

from tradestation.tools import SUPPORTED_INDICATORS, get_bars, plot_bars_with_indicators
from ibkr.news import get_news_headlines, get_news_article
from ibkr.options import get_option_expirations, read_option_chain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market-data-service")

# Create main FastMCP server
mcp = AsyncioFastMCP("Market Data Service")

# Add tools
mcp.add_tool(
    get_bars,
    description=dedent(f"""Fetch bars for a given symbol.
    
    Args:
        symbol: The symbol to fetch bars for
        unit: Unit of time for the bars. Possible values are Minute, Daily, Weekly, Monthly.
        interval: Interval that each bar will consist of - for minute bars, the number of minutes 
            aggregated in a single bar.
        bars_back: Number of bars back to fetch. Max 57,600 for intraday. No limit for 
            daily/weekly/monthly.
        firstdate: The first date formatted as YYYY-MM-DD OR YYYY-MM-DDTHH:mm:SSZ.
        lastdate: The last date formatted as YYYY-MM-DD,2020-04-20T18:00:00Z.
        extended_hours: If True, includes extended hours data.
    
    Returns:
        str: bars data as a json records
    """)
)
mcp.add_tool(
    plot_bars_with_indicators,
    description=dedent(f"""Calculate bars with optional indicators and plot candlestick chart
    
    Args:
        symbol: The symbol to plot
        unit: Unit of time for the bars. Possible values are Minute, Daily, Weekly, Monthly.
        interval: Interval that each bar will consist of - for minute bars, the number of minutes 
            aggregated in a single bar.
        indicators: Optional indicators to plot, comma-separated. Supported: {SUPPORTED_INDICATORS}
        bars_back: Number of bars back to fetch. Max 57,600 for intraday. No limit for 
            daily/weekly/monthly.
        firstdate: The first date formatted as YYYY-MM-DD OR YYYY-MM-DDTHH:mm:SSZ.
        lastdate: The last date formatted as YYYY-MM-DD,2020-04-20T18:00:00Z.
        extended_hours: If True, includes extended hours data.
    
    Returns:
        A candlestick chart with indicators (if given) and the bars data
    """)
)
mcp.add_tool(get_news_headlines)
mcp.add_tool(get_news_article)
mcp.add_tool(get_option_expirations)
mcp.add_tool(read_option_chain)

def main():
    try:
        ib = connect_ib()
        logger.info("Connected to IBKR successfully")
        mcp.run(transport="sse")
    finally:
        ib.disconnect()

if __name__ == "__main__":
    main()
