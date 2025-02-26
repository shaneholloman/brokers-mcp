from datetime import datetime, timedelta
from logging import getLogger
from typing import Dict, Any, List

# If you have your Alpaca settings in a helper class:
from common_lib.alpaca_helpers.async_impl.trading_client import AsyncTradingClient
from common_lib.alpaca_helpers.simulation.trading_client import SimulationTradingClient
from common_lib.alpaca_helpers.env import AlpacaSettings

# Assume you're using the same resource pattern as before:
from mcp.server.fastmcp.resources import FunctionResource, ResourceTemplate

# Alpaca imports:
from alpaca.trading.enums import OrderStatus, OrderType, QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest
import pytz

logger = getLogger(__name__)

# Initialize your trading client
settings = AlpacaSettings()
if settings.simulation:
    trading_client = SimulationTradingClient(settings.api_key, settings.api_secret)

else:
    trading_client = AsyncTradingClient(settings.api_key, settings.api_secret)

async def get_portfolio(symbol: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get account portfolio holdings, including stocks (and possibly crypto if enabled).
    
    Args:
        symbol: The symbol to get holdings for, or "all" for all holdings

    Returns:
        A dictionary containing portfolio positions
    
    Example output:
        {
            "positions": [
                {
                    "symbol": "AAPL",
                    "size": 100,
                    "avg_entry_price": 150.50,
                    "market_value": 16000.00,
                    "unrealized_pl": 500.50,
                    "unrealized_pl_percent": 0.0325,
                    "side": "long",
                    "current_price": 160.00
                }
            ]
        }
    """
    positions = await trading_client.get_all_positions()

    result = []
    for pos in positions:
        if pos.symbol == symbol or symbol == "all":
            result.append({
                "symbol": pos.symbol,
                "size": float(pos.qty),
                "avg_entry_price": float(pos.avg_entry_price),
                "market_value": float(pos.market_value),
                "unrealized_pl": float(pos.unrealized_pl),
                "unrealized_pl_percent": float(pos.unrealized_plpc),
                "side": pos.side.lower(),
                "current_price": float(pos.current_price)
            })
            
    return {"positions": result}

portfolio_resource = ResourceTemplate(
    uri_template="account://portfolio/{symbol}",
    name=get_portfolio.__name__,
    description=get_portfolio.__doc__,
    fn=get_portfolio,
    parameters={
        "symbol": {
            "type": "string",
            "description": "The symbol of the portfolio to get holdings for",
            "default": "all"
        }
    }
)

async def get_account_summary() -> Dict[str, Any]:
    """
    Get high-level account information, like buying power, equity, etc.

    Returns:
        A dictionary containing account information
    
    Example output:
        {
            "account_id": "a1b2c3d4-e5f6-g7h8-i9j0",
            "account_number": "PA12345",
            "status": "ACTIVE",
            "buying_power": 50000.00,
            "equity": 75000.00,
            "portfolio_value": 75000.00,
            "currency": "USD",
            "maintenance_margin": 25000.00
        }
    """
    account = await trading_client.get_account()
    return {
        "account_id": account.id,
        "account_number": account.account_number,
        "status": account.status,
        "buying_power": float(account.buying_power),
        "equity": float(account.equity),
        "portfolio_value": float(account.portfolio_value),
        "currency": account.currency,
        "maintenance_margin": float(account.maintenance_margin)
    }

account_summary_resource = FunctionResource(
    uri="account://account_summary",
    name=get_account_summary.__name__,
    description=get_account_summary.__doc__,
    fn=get_account_summary,
)

async def get_completed_orders(symbol: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get completed orders for a symbol.

    Args:
        symbol: The symbol to get orders for, or "all" for all symbols

    Returns:
        A list of dictionaries containing completed orders
    
    Example output:
        {
            "orders": [
                {
                    "order_id": "b0b6288f-8b45-4187-961f-7e8d7d7140d2",
                    "symbol": "AAPL",
                    "side": "buy",
                    "size": 100,
                    "type": "limit",
                    "status": "filled",
                    "filled_size": 100,
                    "filled_avg_price": 150.50,
                    "filled_at": "2024-03-20 14:30:00",
                    "position_intent": "open"
                }
            ]
        }
    """
    orders = await trading_client.get_orders(filter=GetOrdersRequest(
        status=QueryOrderStatus.CLOSED,
        after=datetime.now() - timedelta(days=1),
        symbols=[symbol]
    ))
    
    result = []
    for o in orders:
        if o.status in [OrderStatus.FILLED, OrderStatus.HELD]:
            result.append({
                "order_id": o.id,
                "symbol": o.symbol,
                "side": o.side.value.lower(),
                "size": float(o.qty),
                "type": o.type.value.lower(),
                "status": o.status.value.lower(),
                "filled_size": float(o.filled_qty),
                "filled_avg_price": float(o.filled_avg_price) if o.filled_avg_price else None,
                "filled_at": o.filled_at.astimezone(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S') if o.filled_at else None,
                "position_intent": o.position_intent.value.lower() if o.position_intent else None
            })
    
    return {"orders": result}

completed_orders_resource = ResourceTemplate(
    uri_template="brokerage://completed_orders/{symbol}",
    name=get_completed_orders.__name__,
    description=get_completed_orders.__doc__,
    fn=get_completed_orders,
    parameters={
        "symbol": {
            "type": "string",
            "description": "The symbol of the orders to get",
            "default": "all"
        }
    }
)

async def get_open_orders(symbol: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get only open orders in the account.

    Args:
        symbol: The symbol to get orders for, or "all" for all symbols

    Returns:
        A dictionary containing open orders
    
    Example output:
        {
            "orders": [
                {
                    "order_id": "b0b6288f-8b45-4187-961f-7e8d7d7140d2",
                    "symbol": "AAPL",
                    "side": "buy",
                    "size": 100,
                    "status": "new",
                    "type": "limit",
                    "price": 150.50,
                    "position_intent": "open",
                    "created_at": "2024-03-20 14:30:00"
                }
            ]
        }
    """
    open_orders = await trading_client.get_orders(
        filter=GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            symbols=[symbol]
        )
    )

    result = []
    for o in open_orders:
        result.append({
            "order_id": o.id,
            "symbol": o.symbol,
            "side": o.side.value.lower(),
            "size": float(o.qty),
            "status": o.status.value.lower(),
            "type": o.type.value.lower(),
            "price": float(o.limit_price) if o.type == OrderType.LIMIT else float(o.stop_price) if o.type in [OrderType.STOP, OrderType.STOP_LIMIT, OrderType.TRAILING_STOP] else None,
            "position_intent": o.position_intent.value.lower() if o.position_intent else None,
            "created_at": o.created_at.astimezone(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S') if o.created_at else None
        })
    
    return {"orders": result}

open_orders_resource = ResourceTemplate(
    uri_template="brokerage://open_orders/{symbol}",
    name=get_open_orders.__name__,
    description=get_open_orders.__doc__,
    fn=get_open_orders,
    parameters={
        "symbol": {
            "type": "string",
            "description": "The symbol of the orders to get",
            "default": "all"
        }
    }
)

async def has_order_filled(order_id: str) -> Dict[str, Any]:
    """
    Check if an order has been filled.

    Args:
        order_id: The ID of the order to check

    Returns:
        A dictionary containing order fill status
    
    Example output:
        {
            "is_filled": true,
            "filled_size": 100,
            "total_size": 100
        }
    """
    order = await trading_client.get_order_by_id(order_id)
    return {
        "is_filled": order.filled_qty == order.qty,
        "filled_size": float(order.filled_qty),
        "total_size": float(order.qty)
    }

order_filled_resource = ResourceTemplate(
    uri_template="brokerage://order_filled/{order_id}",
    name=has_order_filled.__name__,
    description=has_order_filled.__doc__,
    fn=has_order_filled,
    parameters={
        "order_id": {
            "type": "string",
            "description": "The ID of the order to check",
        }
    }
)
