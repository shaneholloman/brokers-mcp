import logging
import os
import dotenv
from ib_insync import IB
import nest_asyncio

from mcp.server.fastmcp import FastMCP
import pytz

from src.tradestation.tools import get_bars, plot_bars_with_indicators
from src.ibkr.news import get_news_headlines, get_news_article
from src.ibkr import client as ib_client
from src.ibkr.options import get_option_expirations, read_option_chain

# Load environment variables and configure logging
dotenv.load_dotenv()
nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market-data-service")

# Create main FastMCP server
mcp = FastMCP("Market Data Service")

# Add tools
mcp.add_tool(get_bars)
mcp.add_tool(plot_bars_with_indicators)
mcp.add_tool(get_news_headlines)
mcp.add_tool(get_news_article)
mcp.add_tool(get_option_expirations)
mcp.add_tool(read_option_chain)

def main():
    try:
        print("Connecting to IBKR")
        # Get connection settings from environment variables
        client_id = os.getenv("IBKR_CLIENT_ID", 1)
        host = os.getenv("IBKR_HOST", "127.0.0.1")
        port = int(os.getenv("IBKR_PORT", "7496"))
        ib = IB()
        ib.TimezoneTWS = pytz.timezone("US/Eastern")
        ib.connect(host, port, clientId=client_id, account=os.getenv("IBKR_ACCOUNT"), timeout=30)
        ib_client.set_ib(ib)
        logger.info("Connected to IBKR successfully")
        mcp.run()
    finally:
        ib.disconnect()

if __name__ == "__main__":
    main()
