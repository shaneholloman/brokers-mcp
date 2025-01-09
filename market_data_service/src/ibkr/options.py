from logging import getLogger

from common_lib.util import list_items
from common_lib.ib import get_ib, get_contract

logger = getLogger(__name__)

async def get_option_expirations(symbol: str) -> str:
    """Get available option expiration dates for a symbol
    
    Args:
        symbol: The symbol to get option expirations for
        
    Returns:
        str: List of expiration dates
    """
    ib = get_ib()
    stock = await get_contract(symbol, "stock")
    chains = await ib.reqSecDefOptParamsAsync(
        stock.symbol, 
        "", 
        stock.secType, 
        stock.conId
    )
    
    expirations = sorted(list(set(
        exp for chain in chains
        for exp in chain.expirations
    )))
    
    return list_items(expirations)

async def read_option_chain(
    symbol: str,
    expiration: str,
    right: str = "C"
) -> str:
    """Read the option chain for a specific expiration date
    
    Args:
        symbol: The symbol to get options for
        expiration: The expiration date in YYYYMMDD format
        right: The option right (C for calls, P for puts)
        
    Returns:
        str: List of options contracts
    """
    ib = get_ib()
    stock = await get_contract(symbol, "stock")
    
    chains = await ib.reqSecDefOptParamsAsync(
        stock.symbol, 
        "", 
        stock.secType, 
        stock.conId
    )
    
    strikes = []
    for chain in chains:
        if chain.expirations and expiration in chain.expirations:
            strikes.extend(chain.strikes)
    strikes = sorted(list(set(strikes)))
    
    contracts = [
        await get_contract(
            symbol,
            "option",
            expiry=expiration,
            strike=strike,
            right=right
        )
        for strike in strikes
    ]
    
    return list_items(contracts)
