from logging import getLogger

from ib_insync import util, Stock, Option
from mcp import Tool
from mcp.types import TextContent

from ..client import ib
from ..common import ibkr_tool_prefix
from ..global_state import qualify_contracts

tools = [Tool(
    name=f"{ibkr_tool_prefix}_get_bars",
    description="Get market data as ohlc volume bars for a stock or index. set the use_rth flag to False to include pre and post market data",
    inputSchema={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "The symbol of the stock (or the underlying) to get bars for"},
            "type": {
                "type": "string",
                "description": "The type of the symbol, either 'stock' or 'index'. Default is 'stock'",
                "enum": ["stock", "index"],
                "default": "stock"
            },
            "duration": {
                "type": "string",
                "description": "Time span of all the bars. Examples: ‘60 S’, ‘30 D’, ‘13 W’, ‘6 M’, ‘10 Y’"
            },
            "bar_size": {
                "type": "string",
                "description": "Time period of one bar. Must be one of: ‘1 secs’,"
                               " ‘5 secs’, ‘10 secs’ 15 secs’, ‘30 secs’, ‘1 min’,"
                               " ‘2 mins’, ‘3 mins’, ‘5 mins’, ‘10 mins’, ‘15 mins’,"
                               " ‘20 mins’, ‘30 mins’, ‘1 hour’, ‘2 hours’, ‘3 hours’,"
                               " ‘4 hours’, ‘8 hours’, ‘1 day’, ‘1 week’, ‘1 month’."
            },
            "end_datetime": {
                "type": "string",
                "description": "The end date and time of the bars, leave empty for update-to-date bars."
                               " Format: 'yyyyMMdd HH:mm:ss'. Assumed to be in the New York timezone."
            },
            "use_rth": {
                "type": "boolean",
                "description": "Whether to use regular trading hours only. Default is True",
                "default": True
            }
        },
        "required": ["symbol", "duration", "bar_size"],
    },
)]

async def handler(name, arguments):
    if name == f"{ibkr_tool_prefix}_get_bars":
        if arguments.get("type", "stock") == "stock":
            contract = Stock(arguments["symbol"], "SMART", "USD")
        elif arguments["type"] == "index":
            raise NotImplementedError("Index is not yet supported")
        else:
            raise ValueError(f"Unknown symbol type: {arguments['type']}")
        contracts = await qualify_contracts(contract)
        return [
            TextContent(
                type="text",
                text=str(
                    util.df(await ib.reqHistoricalDataAsync(
                        contracts[0],
                        endDateTime=arguments.get("end_datetime", ""),
                        durationStr=arguments["duration"],
                        barSizeSetting=arguments["bar_size"],
                        useRTH=arguments.get("use_rth", True),
                        whatToShow="TRADES",
                        formatDate=1
                    ))
                )
            )
        ]
