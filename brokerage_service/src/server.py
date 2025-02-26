from mcp.server.fastmcp import FastMCP

from alpaca_api.tools import place_order, cancel_order, modify_order, liquidate_position, place_trailing_stop
from alpaca_api.resources import (
    account_summary_resource,
    completed_orders_resource,
    open_orders_resource,
    portfolio_resource,
    order_filled_resource,
)

mcp = FastMCP("Brokerage Service")
    
mcp.add_resource(account_summary_resource)
# fast mcp has a bug when doing add_resource on template resources, so we need to manually add them
mcp._resource_manager._templates[completed_orders_resource.uri_template] = completed_orders_resource
mcp._resource_manager._templates[open_orders_resource.uri_template] = open_orders_resource
mcp._resource_manager._templates[portfolio_resource.uri_template] = portfolio_resource
mcp._resource_manager._templates[order_filled_resource.uri_template] = order_filled_resource
mcp.add_tool(place_order)
mcp.add_tool(cancel_order)
mcp.add_tool(modify_order)
mcp.add_tool(liquidate_position)
mcp.add_tool(place_trailing_stop)


def main():
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
    

