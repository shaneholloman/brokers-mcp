import asyncio
import json
import logging
from common_lib.util import is_market_open
from ib_insync import LimitOrder, OrderStatus, Trade
from common_lib.ib import get_ib, get_contract

logger = logging.getLogger(__name__)

async def _wait_for_order_to_submit(order: Trade) -> Trade:
    retries = 200
    while order.orderStatus.status in OrderStatus.ActiveStates and order.orderStatus.status != OrderStatus.Submitted:
        if retries <= 0:
            get_ib().cancelOrder(order.order)
            raise TimeoutError(f"Order {order.order.orderId} failed to submit")
        logger.info(f"Waiting for order {order.order.orderId} to be submitted, order_id: {order.order.orderId}, current status: {order.orderStatus.status}")
        await asyncio.sleep(0.01)
    return order

def _filter_keys(trade: Trade) -> dict:
    common_keys = {
        "order_id": trade.order.orderId,
        "exchange": trade.contract.exchange,
        "primary_exchange": trade.contract.primaryExchange,
        "symbol": trade.contract.symbol,
        "action": trade.order.action,
        "parent_id": trade.order.parentId,
        "order_type": trade.order.orderType,
        "total_quantity": trade.order.totalQuantity,
        "lmt_price": trade.order.lmtPrice,
        "status": trade.orderStatus.status,
        "filled": trade.orderStatus.filled,
        "remaining": trade.orderStatus.remaining,
        "average_fill_price": trade.orderStatus.avgFillPrice,
    }
    
    sec_type = trade.contract.secType
    if sec_type == "STK":
        return common_keys
    elif sec_type == "OPT":
        # todo: add more keys when starting to support options
        return common_keys
    
    return common_keys
    

async def place_new_order(
    symbol: str,
    size: float,
    buy_sell: str,
    price: float,
    take_profit: float | None = None,
    stop_loss: float | None = None
) -> str:
    """Place an order for a stock. Could be market or limit order. Optionally include a take profit and stop loss
    
    Args:
        symbol: The symbol of the stock to place an order for
        size: The size of the order
        buy_sell: Either 'Buy' or 'Sell'
        price: The limit price of the order
        take_profit: The take profit price, optional
        stop_loss: The stop loss price, optional

    > Note: Market orders are strictly not allowed.
    """
    if not is_market_open():
        raise ValueError("Cannot submit orders outside of market hours")
    
    ib = get_ib()
    contract = await get_contract(symbol, "stock")
    action = buy_sell.upper()
    if not action in ["BUY", "SELL"]:
        raise ValueError(f"Invalid action: {action}, must be 'Buy' or 'Sell'")
    
    # todo: need to decide whether to allow models to place market orders
    order = LimitOrder(action, size, price)

    # If take profit and stop loss are provided, create bracket order
    if take_profit is not None and stop_loss is not None:
        bracket = ib.bracketOrder(
            action=action,
            quantity=size,
            limitPrice=price,
            takeProfitPrice=take_profit,
            stopLossPrice=stop_loss
        )
        
        # Place all bracket orders
        trades = []
        for o in bracket:
            trades.append(ib.placeOrder(contract, o))
        
        parent_order = [trade for trade in trades if trade.order.parentId == 0][0]
        await _wait_for_order_to_submit(parent_order)
        
        return json.dumps(_filter_keys(parent_order), default=str)
    
    # Place single order
    trade = ib.placeOrder(contract, order)
    await _wait_for_order_to_submit(trade)

    return json.dumps(_filter_keys(trade), default=str)

async def modify_order(order_id: int, price: float | None = None) -> str:
    """Modify an existing order by its id
    
    Args:
        order_id: The id of the order to modify
        price: The new price of the order
    """
    if not is_market_open():
        raise ValueError("Cannot modify orders outside of market hours")
    ib = get_ib()
    
    # Find the trade by order ID
    trades = ib.trades()
    trade = next((t for t in trades if t.order.orderId == order_id), None)
    
    if not trade:
        raise ValueError(f"No order found with ID {order_id}")
        
    # Create new order with modified price
    if price is not None:
        trade.order.lmtPrice = price
        
    # Place modified order
    modified_trade = ib.placeOrder(trade.contract, trade.order)
    await _wait_for_order_to_submit(modified_trade)
    
    return json.dumps(_filter_keys(modified_trade), default=str)

async def cancel_order(order_id: int) -> str:
    """Cancel an existing order by its id
    
    Args:
        order_id: The id of the order to cancel
    """
    ib = get_ib()
    # Find the trade by order ID
    trades = ib.trades()
    trade = next((t for t in trades if t.order.orderId == order_id), None)
    
    if not trade:
        raise ValueError(f"No order found with ID {order_id}")
        
    # Cancel the order
    cancelled_trade = ib.cancelOrder(trade.order)
    await _wait_for_order_to_submit(cancelled_trade)
    
    return json.dumps(_filter_keys(cancelled_trade), default=str)
