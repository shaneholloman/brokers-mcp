import json

from mcp import Tool
from mcp.types import TextContent

from .api import tradestation
from ..common import BrokerTools

tradestation_tools_prefix = "tradestation"

# todo: implement more sophisticated tools that allow generating bars as images, adding indicators, scanning for stocks per criteria, etc..

async def call_tool(name: str, arguments: dict):
    if name == f"{tradestation_tools_prefix}_get_bars":
        bars_df = await tradestation.get_bars(
            symbol=arguments["symbol"],
            unit=arguments["unit"],
            interval=arguments["interval"],
            barsback=arguments.get("bars_back"),
            firstdate=arguments.get("firstdate"),
            lastdate=arguments.get("lastdate"),
        )
        return [
            TextContent(
                type="text",
                text=str(bars_df),
            )
        ]
    elif name == f"{tradestation_tools_prefix}_place_buy_order":
        order_details = await tradestation.open_position(
            symbol=arguments["symbol"],
            size=arguments["size"],
            order_type=arguments.get("order_type", "Market"),
            price=arguments.get("price"),
            tp=arguments.get("take_profit", 0),
            sl=arguments.get("stop_loss", 0),
        )
        return [
            TextContent(
                type="text",
                text=json.dumps(order_details),
            )
        ]
    elif name == f"{tradestation_tools_prefix}_place_sell_order":
        order_details = await tradestation.close_position(
            symbol=arguments["symbol"],
            size=arguments["size"],
            order_type=arguments.get("order_type", "Market"),
            limit_price=arguments.get("price"),
        )
        return [
            TextContent(
                type="text",
                text=json.dumps(order_details),
            )
        ]
    elif name == f"{tradestation_tools_prefix}_get_positions":
        positions = await tradestation.get_positions()
        return [
            TextContent(
                type="text",
                text=json.dumps(positions),
            )
        ]
    elif name == f"{tradestation_tools_prefix}_get_balances":
        balances = await tradestation.get_balances()
        return [
            TextContent(
                type="text",
                text=json.dumps(balances),
            )
        ]
    else:
        raise ValueError(f"Unknown tool name: {name}")

tools = BrokerTools(
    name_prefix=tradestation_tools_prefix,
    tools = [
        Tool(
            name=f"{tradestation_tools_prefix}_get_bars",
            description="Get market data as ohlc bars for a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "unit": {
                        "type": "string",
                        "description":"Unit of time for the bars. Possible values are Minute, Daily, Weekly, Monthly."
                    },
                    "interval": {
                        "type": "number",
                        "description":"Interval that each bar will consist of - for minute bars,"
                                      " the number of minutes aggregated in a single bar. For bar units other than minute,"
                                      " value must be 1. For unit Minute the max allowed Interval is 1440."
                    },
                    "bars_back": {
                        "type": "number",
                        "description":"Number of bars back to fetch (or retrieve)."
                                      " The maximum number of intraday bars back that a user can query is 57,600."
                                      " There is no limit on daily, weekly, or monthly bars."
                                      " This parameter is mutually exclusive with firstdate",
                    },
                    "firstdate": {
                        "type": "string",
                        "description":"Does not have a default value."
                                      " The first date formatted as YYYY-MM-DD OR YYYY-MM-DDTHH:mm:SSZ."
                                      " This parameter is mutually exclusive with barsback."
                    },
                    "lastdate": {
                        "type": "string",
                        "description":"Defaults to current timestamp. The last date formatted as YYYY-MM-DD,2020-04-20T18:00:00Z"
                    },
                },
                "required": ["symbol", "interval", "unit"],
            },
        ),
        Tool(
            name=f"{tradestation_tools_prefix}_place_buy_order",
            description="Place a buy order for any symbol, returns the placed order details or an error",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbol to buy"},
                    "size": {"type": "number", "description": "Number of shares to buy"},
                    "price": {"type": "number", "description": "Price to buy at, applies to Limit orders"},
                    "order_type": {
                        "type": "string",
                        "description": "Type of order to place. Possible values are Market, Limit, StopMarket",
                    },
                    "take_profit": {"type": "number", "description": "Take profit price"},
                    "stop_loss": {"type": "number", "description": "Stop loss price"},
                },
                "required": ["symbol", "size"],
            },
        ),
        Tool(
            name=f"{tradestation_tools_prefix}_place_sell_order",
            description="Place a sell order for any symbol, returns the placed order details or an error",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbol to sell"},
                    "size": {"type": "number", "description": "Number of shares to sell"},
                    "order_type": {
                        "type": "string",
                        "description": "Type of order to place. Possible values are Market, Limit, StopMarket",
                    },
                    "take_profit": {"type": "number", "description": "Take profit price"},
                    "stop_loss": {"type": "number", "description": "Stop loss price"},
                },
                "required": ["symbol", "size"],
            },
        ),
        Tool(
            name=f"{tradestation_tools_prefix}_get_positions",
            description="Get current account positions",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name=f"{tradestation_tools_prefix}_get_balances",
            description="Get account balances",
            inputSchema={"type": "object", "properties": {}, "required": []},

        ),
    ],
    handler=call_tool
)