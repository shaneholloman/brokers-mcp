import logging
import os
from src.orders import place_new_order, cancel_order, modify_order
from src.resources import account_summary_resource, all_orders_resource, open_orders_resource, portfolio_resource
import dotenv
from ib_insync import IB
import nest_asyncio
import pytz

from mcp.server.fastmcp import FastMCP

from src.client import set_ib

# Load environment variables and configure logging
dotenv.load_dotenv()
nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brokerage-service")

# Create main FastMCP server
mcp = FastMCP("Brokerage Service")
    
# Add IBKR resources and tools
mcp.add_resource(portfolio_resource)
mcp.add_resource(account_summary_resource)
mcp.add_resource(all_orders_resource)
mcp.add_resource(open_orders_resource)
mcp.add_tool(place_new_order)
mcp.add_tool(cancel_order)
mcp.add_tool(modify_order)

def main():
    try:
        # Get connection settings from environment variables
        client_id = os.getenv("IBKR_CLIENT_ID", 1)
        host = os.getenv("IBKR_HOST", "127.0.0.1")
        port = int(os.getenv("IBKR_PORT", "7496"))
        ib = IB()
        ib.TimezoneTWS = pytz.timezone("US/Eastern")
        ib.connect(host, port, clientId=client_id, account=os.getenv("IBKR_ACCOUNT"), timeout=30)
        set_ib(ib)
        logger.info("Connected to IBKR successfully")
        mcp.run()
    finally:
        ib.disconnect()

if __name__ == "__main__":
    main()

