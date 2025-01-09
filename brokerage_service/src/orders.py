import asyncio
from ib_insync import LimitOrder, OrderStatus
from common_lib.ib import get_ib, get_contract

async def place_new_order(
    symbol: str,
    size: float,
    buy_sell: str,
    price: float | None = None,
    take_profit: float | None = None,
    stop_loss: float | None = None
) -> str:
    """Place an order for a stock. Could be market or limit order. Optionally include a take profit and stop loss
    
    Args:
        symbol: The symbol of the stock to place an order for
        size: The size of the order
        buy_sell: Either 'Buy' or 'Sell'
        price: The price of the order, if it's a limit order
        take_profit: The take profit price, optional
        stop_loss: The stop loss price, optional
    """
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
            limitPrice=price or ib.ticker(contract).marketPrice(),
            takeProfitPrice=take_profit,
            stopLossPrice=stop_loss
        )
        
        # Place all bracket orders
        trades = []
        for o in bracket:
            trades.append(ib.placeOrder(contract, o))
        
        return f"Placed bracket order: {repr(trades)}"
    
    # Place single order
    trade = ib.placeOrder(contract, order)
    while trade.orderStatus.status in OrderStatus.ActiveStates and trade.orderStatus.status != OrderStatus.Submitted:
        await asyncio.sleep(0.01)

    return f"Placed order {repr(trade)}"

async def modify_order(order_id: int, price: float | None = None) -> str:
    """Modify an existing order by its id
    
    Args:
        order_id: The id of the order to modify
        price: The new price of the order
    """
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
    while modified_trade.orderStatus.status in OrderStatus.ActiveStates and modified_trade.orderStatus.status != OrderStatus.Submitted:
        await asyncio.sleep(0.01)
    
    return f"Modified order {repr(modified_trade)}"

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
    while cancelled_trade.orderStatus.status in OrderStatus.ActiveStates and cancelled_trade.orderStatus.status != OrderStatus.Submitted:
        await asyncio.sleep(0.01)
    
    return f"Cancelled order {repr(cancelled_trade)}"
