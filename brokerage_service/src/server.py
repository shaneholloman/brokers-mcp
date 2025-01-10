import logging
import nest_asyncio
nest_asyncio.apply()

from common_lib.ib import connect_ib
from common_lib.mcp import AsyncioFastMCP

from orders import place_new_order, cancel_order, modify_order
from resources import (
    account_summary_resource,
    all_orders_resource,
    open_orders_resource,
    portfolio_resource,
    symbol_orders_resource,
)
import dotenv
# Load environment variables and configure logging
dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brokerage-service")

# Create main FastMCP server
mcp = AsyncioFastMCP("Brokerage Service")
    
# Add IBKR resources and tools
mcp.add_resource(portfolio_resource)
mcp.add_resource(account_summary_resource)
mcp.add_resource(all_orders_resource)
mcp.add_resource(open_orders_resource)
mcp._resource_manager.add_template(
    symbol_orders_resource.fn,
    uri_template=str(symbol_orders_resource.uri),
    name=symbol_orders_resource.name,
    description=symbol_orders_resource.description,
    mime_type=symbol_orders_resource.mime_type,
)
mcp.add_tool(place_new_order)
mcp.add_tool(cancel_order)
mcp.add_tool(modify_order)


def main():
    try:
        ib = connect_ib()
        logger.info("Connected to IBKR successfully")
        mcp.run(transport="sse")
    finally:
        ib.disconnect()

if __name__ == "__main__":
    main()

