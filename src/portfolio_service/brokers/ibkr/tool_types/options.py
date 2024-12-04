import asyncio
from logging import getLogger

import pandas as pd
from ib_insync import Option
from mcp import Tool
from mcp.types import TextContent


# from src.portfolio_service.brokers.common import list_items
# from src.portfolio_service.brokers.ibkr.client import ib
# from src.portfolio_service.brokers.ibkr.common import ibkr_tool_prefix
# from src.portfolio_service.brokers.ibkr.global_state import qualify_contracts
# from src.portfolio_service.brokers.ibkr.tool_types.market_data import get_contract

logger = getLogger(__name__)

from ..client import ib
from ..common import ibkr_tool_prefix
from ...common import list_items
from ..global_state import get_contract
from ..global_state import qualify_contracts

tools = [
    Tool(
        name=f"{ibkr_tool_prefix}_get_option_expirations",
        description="Get the expiration dates for options of an underlying",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The symbol of the underlying"
                },
                "type": {
                    "type": "string",
                    "description": "The type of the underlying, either 'stock', 'index', or 'future'. Default is 'stock'",
                    "enum": ["stock", "index", "future"],
                    "default": "stock"
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name=f"{ibkr_tool_prefix}_read_option_chain",
        description="Read the option chain for an underlying at a specific expiration date",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The symbol of the underlying"},
                "expiration": {"type": "string", "description": "The expiration date of the options, format: 'YYYYMMDD'"},
                "strike_distance": {"type": "number", "description": "The distance from the current price to the strike price of the options that are displayed"},
                "type": {"type": "string", "description": "The type of the underlying, either 'stock', 'index', or 'future'. Default is 'stock'"},
            },
            "required": ["symbol", "expiration", "strike_distance"]
        }
    )
]

async def handler(name, arguments):
    if name == f"{ibkr_tool_prefix}_get_option_expirations":
        contract = await get_contract(arguments["symbol"], arguments.get("type", "stock"))
        chains = await ib.reqSecDefOptParamsAsync(contract.symbol, "", contract.secType, contract.conId)
        try:
            smart = [c for c in chains if c.exchange == "SMART"][0]
            return [TextContent(
                type="text",
                text=list_items(smart.expirations)
            )]
        except IndexError:
            raise ValueError("No option chain found")
    elif name == f"{ibkr_tool_prefix}_read_option_chain":
        contract = await get_contract(arguments["symbol"], arguments.get("type", "stock"))
        current_price = (await ib.reqTickersAsync(contract))[0].marketPrice()
        chains = await ib.reqSecDefOptParamsAsync(contract.symbol, "", contract.secType, contract.conId)
        try:
            option_chains = [e for e in chains if e.exchange == "SMART"][0]
        except IndexError:
            raise ValueError("No option chain found")

        strikes = [s for s in option_chains.strikes if current_price - arguments["strike_distance"] < s < current_price + arguments["strike_distance"]]
        rights = ["P", "C"]
        contracts = [
            Option(
                contract.symbol,
                arguments.get("expiration"),
                strike,
                right,
                'SMART',
            )
            for strike in strikes
            for right in rights
        ]
        contracts = await qualify_contracts(*contracts)
        tickers = await ib.reqTickersAsync(*contracts)
        retries = 0
        while not all([ticker.modelGreeks and ticker.modelGreeks.delta for ticker in tickers]) and retries < 8:
            ib.sleep(0.5)
            retries += 1
            logger.info("Retrying to get greeks")

        chain_df = pd.DataFrame([
            {
                "symbol": ticker.contract.symbol,
                "strike": ticker.contract.strike,
                "call_put": ticker.contract.right,
                "last": ticker.last,
                "bid": ticker.bid,
                "ask": ticker.ask,
                "volume": ticker.volume,
                "openInterest": ticker.callOpenInterest if ticker.contract.right == "C" else ticker.putOpenInterest,
                "delta": ticker.modelGreeks.delta if ticker.modelGreeks else "N/A",
                "gamma": ticker.modelGreeks.gamma if ticker.modelGreeks else "N/A",
                "vega": ticker.modelGreeks.vega if ticker.modelGreeks else "N/A",
                "theta": ticker.modelGreeks.theta if ticker.modelGreeks else "N/A",
                "impliedVolatility": ticker.modelGreeks.impliedVol if ticker.modelGreeks else "N/A",
            }
            for ticker in tickers
        ])
        return [TextContent(
            type="text",
            text=str(chain_df)
        )]

    else:
        raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    asyncio.run(handler(f"{ibkr_tool_prefix}_read_option_chain", {"symbol": "AAPL", "expiration": "20241220", "strike_distance": 20}))