from logging import getLogger
import json

from common_lib.ib import get_ib
from mcp.server.fastmcp.resources import FunctionResource

from common_lib.util import unpack

from orders import _filter_keys

logger = getLogger(__name__)

def get_portfolio() -> str:
    ib = get_ib()
    """Get account portfolio holdings, including stocks, options, and futures"""
    positions = ib.reqPositions()
    as_json = json.dumps(unpack(positions), default=str)
    return as_json

portfolio_resource = FunctionResource(
    uri="account://portfolio",
    name="Get account portfolio holdings",
    description="Get account portfolio holdings, including stocks, options, and futures",
    fn=get_portfolio,
)

def get_account_summary() -> str:
    """Get account summary information"""
    ib = get_ib()
    tags = ('AccountType,NetLiquidation,TotalCashValue,SettledCash,'
            'AccruedCash,BuyingPower,EquityWithLoanValue,'
            'PreviousDayEquityWithLoanValue,GrossPositionValue').split(',')
    account_values = ib.accountSummary()
    filtered = {value.tag: value.value for value in account_values if value.tag in tags}
    return json.dumps(filtered, default=str)

account_summary_resource = FunctionResource(
    uri="account://account_summary",
    name="Get account summary information",
    description="Get account summary information",
    fn=get_account_summary,
)

def get_all_orders() -> str:
    """Get all orders in the account from the current session"""
    ib = get_ib()
    all_orders = ib.reqCompletedOrders(apiOnly=True)
    all_orders += ib.reqOpenOrders()
    filled_and_open_orders = [order for order in all_orders if not order.orderStatus.status == "Cancelled"]
    as_json = json.dumps([_filter_keys(order) for order in filled_and_open_orders], default=str)
    return as_json

all_orders_resource = FunctionResource(
    uri="brokerage://all_orders",
    name="Get all orders in the account from the current session",
    description="Get all orders in the account from the current session",
    fn=get_all_orders,
)

def get_open_orders() -> str:
    """Get all open orders in the account"""
    ib = get_ib()
    open_orders = ib.openTrades()
    as_json = json.dumps([_filter_keys(order) for order in open_orders], default=str)
    return as_json

open_orders_resource = FunctionResource(
    uri="brokerage://open_orders",
    name="Get all open orders in the account",
    description="Get all open orders in the account",
    fn=get_open_orders,
)

def get_orders_for_symbol(symbol: str) -> str:
    """Get all orders for a specific symbol from the current session"""
    ib = get_ib()
    all_orders = ib.trades()
    symbol_orders = [order for order in all_orders 
                    if order.contract.symbol == symbol 
                    and not order.orderStatus.status == "Cancelled"]
    as_json = json.dumps([_filter_keys(order) for order in symbol_orders], default=str)
    return as_json

symbol_orders_resource = FunctionResource(
    uri="brokerage://all_orders/{symbol}",
    name="Get orders for a specific symbol",
    description="Get all orders for a specific symbol from the current session", 
    fn=get_orders_for_symbol,
)
