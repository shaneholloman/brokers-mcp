from datetime import datetime, timedelta
from logging import getLogger

# If you have your Alpaca settings in a helper class:
from common_lib.alpaca_helpers import AlpacaSettings

# Assume you’re using the same resource pattern as before:
from mcp.server.fastmcp.resources import FunctionResource, ResourceTemplate

# Alpaca imports:
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderStatus, OrderType
from alpaca.trading.requests import GetOrdersRequest, QueryOrderStatus
import pytz

logger = getLogger(__name__)

# Initialize your trading client
settings = AlpacaSettings()
trading_client = TradingClient(settings.api_key, settings.api_secret)

def get_portfolio(symbol: str) -> str:
    """
    Get account portfolio holdings, including stocks (and possibly crypto if enabled).
    Returns a nicely formatted multiline string.
    """
    positions = trading_client.get_all_positions()
    if not positions:
        return "No positions found."

    lines = ["------------------"]
    for pos in positions:
        if pos.symbol == symbol or symbol == "all":
            lines.append(
                f"Symbol: {pos.symbol}, "
                f"Size: {pos.qty}, "
                f"Avg Entry Price: {pos.avg_entry_price}, "
                f"Market Value: {pos.market_value}, "
                f"Unrealized P/L: {float(pos.unrealized_pl):.2f}, "
                f"Unrealized P/L %: {float(pos.unrealized_plpc):.2%}, "
                f"Side: {pos.side}, "
                f"Current Price: {pos.current_price}, "
            )
    return "\n".join(lines)

portfolio_resource = ResourceTemplate(
    uri_template="account://portfolio/{symbol}",
    name="Get account portfolio holdings",
    description="Get account portfolio holdings (stocks, etc.)",
    fn=get_portfolio,
    parameters={
        "symbol": {
            "type": "string",
            "description": "The symbol of the portfolio to get holdings for",
            "default": "all"
        }
    }
)

def get_account_summary() -> str:
    """
    Get high-level account information, like buying power, equity, etc.,
    returned in a simple multiline string.
    """
    account = trading_client.get_account()
    lines = [
        "Account Summary:",
        "----------------",
        f"Account ID: {account.id}",
        f"Account Number: {account.account_number}",
        f"Account Status: {account.status}",
        f"Buying Power: {account.buying_power}",
        f"Equity: {account.equity}",
        f"Portfolio Value: {account.portfolio_value}",
        f"Currency: {account.currency}",
        f"Maintenance Margin: {account.maintenance_margin}",
    ]
    return "\n".join(lines)

account_summary_resource = FunctionResource(
    uri="account://account_summary",
    name="Get account summary information",
    description="Get high-level account info such as buying power, equity, etc.",
    fn=get_account_summary,
)

def get_completed_orders(symbol: str) -> str:
    orders = trading_client.get_orders(filter=GetOrdersRequest(
        status=QueryOrderStatus.CLOSED,
        after=datetime.now() - timedelta(days=1),
        symbol=symbol
    ))
    lines = ["--------------------------------"]
    for o in orders:
        if o.status == OrderStatus.FILLED:
            lines.append(
                f"Order ID: {o.id}, "
                f"Symbol: {o.symbol}, "
                f"Side: {o.side}, "
                f"Qty: {o.qty}, "
                f"Type: {o.type}, "
                f"Status: {o.status}, "
                f"Filled Quantity: {o.filled_qty}, "
                f"Filled Average Price: {o.filled_avg_price}, "
                f"Filled At: {o.filled_at.astimezone(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S') if o.filled_at else 'N/A'}, "
                f"Position Intent: {o.position_intent.value if o.position_intent else 'N/A'}, "
        )
    return "\n".join(lines)

completed_orders_resource = ResourceTemplate(
    uri_template="brokerage://completed_orders/{symbol}",
    name="Get all orders in the account from the current session",
    description="Get all orders in the account from the current session (excluding canceled).",
    fn=get_completed_orders,
    parameters={
        "symbol": {
            "type": "string",
            "description": "The symbol of the orders to get",
            "default": "all"
        }
    }
)

def get_open_orders(symbol: str) -> str:
    """
    Get only open orders in the account and return them in a multiline string.
    """
    open_orders = trading_client.get_orders(
        filter=GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            symbol=symbol
        )
    )
    if not open_orders:
        return "No open orders found."

    lines = []
    for o in open_orders:
        line = (
            f"Order ID: {o.id}, "
            f"Symbol: {o.symbol}, "
            f"Side: {o.side}, "
            f"Qty: {o.qty}, "
            f"Status: {o.status}, "
            f"Type: {o.type}, "
            f"Position Intent: {o.position_intent.value if o.position_intent else 'N/A'}, "
            f"Created At: {o.created_at.astimezone(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S') if o.created_at else 'N/A'}, "
        )
        if o.type == OrderType.LIMIT:
            line += f"Limit Price: {o.limit_price}, "
        if o.type == OrderType.STOP:
            line += f"Stop Price: {o.stop_price}, "
        lines.append(line)
    return "\n".join(lines)

open_orders_resource = ResourceTemplate(
    uri_template="brokerage://open_orders/{symbol}",
    name="Get all open orders in the account",
    description="Get all open orders in the account",
    fn=get_open_orders,
    parameters={
        "symbol": {
            "type": "string",
            "description": "The symbol of the orders to get",
            "default": "all"
        }
    }
)
