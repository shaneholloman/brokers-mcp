from mcp import Tool
from mcp.types import TextContent

from ..client import ib
from ..common import ibkr_tool_prefix

tools = [
    Tool(
        name=f"{ibkr_tool_prefix}_place_new_order",
        description="Place an order for a stock. Could be market or limit order. Optionally include a take profit and stop loss",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The symbol of the stock to place an order for"},
                "size": {"type": "number", "description": "The size of the order"},
                "order_type": {
                    "type": "string",
                    "description": "The type of the order. Either 'Market' or 'Limit'. Default is 'Market'",
                    "enum": ["Market", "Limit"],
                    "default": "Market"
                },
                "buy_sell": {
                    "type": "string",
                    "description": "Either 'Buy' or 'Sell'",
                    "enum": ["Buy", "Sell"]
                },
                "price": {"type": "number", "description": "The price of the order, if it's a limit order"},
                "take_profit": {"type": "number", "description": "The take profit price, optional"},
                "stop_loss": {"type": "number", "description": "The stop loss price, optional"}
            },
            "required": ["symbol", "size", "buy_sell"]
        }
    ),
    Tool(
        name=f"{ibkr_tool_prefix}_modify_order",
        description="Modify an existing order by its id",
        inputSchema={
            "type": "object",
            "properties": {
                "order_id": {"type": "number", "description": "The id of the order to modify"},
                "price": {"type": "number", "description": "The new price of the order"},
            },
            "required": ["order_id"]
        }
    ),
]

async def handler(name, arguments):
    if name == f"{ibkr_tool_prefix}_place_new_order":
        return [
            TextContent(
                type="text",
                text=str(await ib.order(
                    symbol=arguments["symbol"],
                    size=arguments["size"],
                    order_type=arguments.get("order_type", "Market"),
                    buy_sell=arguments["buy_sell"],
                    price=arguments.get("price"),
                    take_profit=arguments.get("take_profit"),
                    stop_loss=arguments.get("stop_loss")
                ))
            )
        ]
    elif name == f"{ibkr_tool_prefix}_modify_order":
        return [
            TextContent(
                type="text",
                text=str(ib.modify_order(
                    order_id=arguments["order_id"],
                    price=arguments["price"]
                ))
            )
        ]