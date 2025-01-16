from mcp.server.fastmcp import FastMCP

from alpaca_api.tools import place_order, cancel_order, modify_order
from alpaca_api.resources import (
    account_summary_resource,
    completed_orders_resource,
    open_orders_resource,
    portfolio_resource,
)

# Create main FastMCP server
mcp = FastMCP("Brokerage Service")
    
# Add IBKR resources and tools
mcp.add_resource(account_summary_resource)
mcp._resource_manager._templates[completed_orders_resource.uri_template] = completed_orders_resource
mcp._resource_manager._templates[open_orders_resource.uri_template] = open_orders_resource
mcp._resource_manager._templates[portfolio_resource.uri_template] = portfolio_resource
mcp.add_tool(place_order)
mcp.add_tool(cancel_order)
mcp.add_tool(modify_order)


def main():
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
    

