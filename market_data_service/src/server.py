import os
from dotenv import load_dotenv

load_dotenv()
import logging
from alpaca_api.news import get_news, latest_headline_resource
from alpaca_api.market_data import (
    SUPPORTED_INDICATORS,
    get_alpaca_bars as get_bars,
    plot_alpaca_bars_with_indicators as plot_bars_with_indicators,
)
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("market-data-service")

# Create main FastMCP server
mcp = FastMCP(name="Market Data Service")

# Add tools
mcp.add_tool(
    get_bars,
    name="get_bars",
    description=f"""Fetch bars for a given symbol.
    Args:
        symbol: The symbol to fetch bars for
        unit: Unit of time for the bars. Possible values are Minute, Hour, Daily, Weekly, Monthly ONLY. NO OTHER VALUES ARE SUPPORTED.
        bar_size: Interval that each bar will consist of - for minute bars, the number of minutes 
            aggregated in a single bar.
            For example, bar_size=5 and unit=Minute will fetch 5-minute bars.
            bar_size=60 and unit=Minute will fetch 1-hour bars.
            Default is 1.
        bars_back: Number of bars back to fetch. Max 57,600 for intraday. No limit for 
            daily/weekly/monthly.
        indicators: Optional indicators to plot, comma-separated. Supported: {SUPPORTED_INDICATORS}
    
    Returns:
        str: json records with lines=true
    """,
)

mcp.add_tool(
    plot_bars_with_indicators,
    name="plot_bars_with_indicators",
    description=f"""Plot a chart with optional indicators for a given symbol.
    
    Args:
        symbol: The symbol to fetch bars for
        unit: Unit of time for the bars. Possible values are Minute, Hour, Daily, Weekly, Monthly. ONLY THESE VALUES ARE SUPPORTED.
        bar_size: Interval that each bar will consist of - for minute bars, the number of minutes 
            aggregated in a single bar.
            For example, bar_size=5 and unit=Minute will fetch 5-minute bars.
            bar_size=1 and unit=Hour will fetch 1-hour bars.
            Default is 1.
        bars_back: Number of bars back to fetch. Max 57,600 for intraday. No limit for 
            daily/weekly/monthly.
        indicators: Optional indicators to plot, comma-separated. Supported: {SUPPORTED_INDICATORS}
    
    Returns:
        A tuple of (Image, str) where the first element is the chart image and the second element is the bars (and indicators) data in json records with lines=true
    """,
)
mcp.add_tool(get_news)
mcp._resource_manager._templates[latest_headline_resource.uri_template] = (
    latest_headline_resource
)

def main():
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
