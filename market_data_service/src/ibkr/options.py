from logging import getLogger
from typing import Annotated

import pandas as pd
from ib_insync import Option

from src.common import list_items
from src.ibkr.global_state import get_contract, qualify_contracts
from src.ibkr import client as ib_client

logger = getLogger(__name__)

async def get_option_expirations(
    symbol: str,
    type: str = "stock"
) -> str:
    """Get the expiration dates for options of an underlying
    
    Args:
        symbol: The symbol of the underlying
        type: The type of the underlying, either 'stock', 'index', or 'future'
    
    Returns:
        str: List of expiration dates
    """
    ib = ib_client.get_ib()
    contract = await get_contract(symbol, type)
    chains = await ib.reqSecDefOptParamsAsync(
        contract.symbol, 
        "", 
        contract.secType, 
        contract.conId
    )
    
    try:
        smart = [c for c in chains if c.exchange == "SMART"][0]
        return list_items(smart.expirations)
    except IndexError:
        raise ValueError("No option chain found")

async def read_option_chain(
    symbol: str,
    expiration: str,
    strike_distance: float,
    type: str = "stock"
) -> str:
    """Read the option chain for an underlying at a specific expiration date
    
    Args:
        symbol: The symbol of the underlying
        expiration: The expiration date of the options, format: 'YYYYMMDD'
        strike_distance: The distance (price delta) from the current price to show strikes
        type: The type of the underlying, either 'stock', 'index', or 'future'
    
    Returns:
        str: Option chain data as a string representation of a pandas DataFrame
    """
    ib = ib_client.get_ib()
    contract = await get_contract(symbol, type)
    current_price = (await ib.reqTickersAsync(contract))[0].marketPrice()
    chains = await ib.reqSecDefOptParamsAsync(
        contract.symbol, 
        "", 
        contract.secType, 
        contract.conId
    )
    
    try:
        option_chains = [e for e in chains if e.exchange == "SMART"][0]
    except IndexError:
        raise ValueError("No option chain found")

    # Get strikes within distance of current price
    strikes = [
        s for s in option_chains.strikes 
        if current_price - strike_distance < s < current_price + strike_distance
    ]
    
    # Create contracts for puts and calls
    rights = ["P", "C"]
    contracts = [
        Option(
            contract.symbol,
            expiration,
            strike,
            right,
            'SMART',
            "100",
            'USD'
        )
        for strike in strikes
        for right in rights
    ]
    
    # Qualify and filter contracts
    contracts = await qualify_contracts(*contracts)
    contracts = [c for c in contracts if c]  # remove invalid contracts
    
    # Get market data and greeks
    tickers = await ib.reqTickersAsync(*contracts)
    retries = 0
    while not all([ticker.modelGreeks and ticker.modelGreeks.delta for ticker in tickers]) and retries < 8:
        ib.sleep(0.5)
        retries += 1
        logger.info("Retrying to get greeks")

    # Create dataframe with option chain data
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
    
    return str(chain_df)
