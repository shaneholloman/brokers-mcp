from src.client import get_ib
from src.global_state import get_contract
from ib_insync import LimitOrder, MarketOrder


async def place_new_order(
    symbol: str,
    size: float,
    buy_sell: str,
    order_type: str = "Market",
    price: float | None = None,
    take_profit: float | None = None,
    stop_loss: float | None = None
) -> str:
    """Place an order for a stock. Could be market or limit order. Optionally include a take profit and stop loss
    
    Args:
        symbol: The symbol of the stock to place an order for
        size: The size of the order
        buy_sell: Either 'Buy' or 'Sell'
        order_type: The type of the order. Either 'Market' or 'Limit'. Default is 'Market'
        price: The price of the order, if it's a limit order
        take_profit: The take profit price, optional
        stop_loss: The stop loss price, optional
    """
    ib = get_ib()
    # Create contract for the stock
    contract = await get_contract(symbol, "stock")
    # Set up base order
    action = buy_sell.upper()
    
    if order_type == "Market":
        order = MarketOrder(action, size)
    else:
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
    return f"Placed order {repr(trade)}"

def modify_order(order_id: int, price: float | None = None) -> str:
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
    
    return f"Modified order {repr(modified_trade)}"

def cancel_order(order_id: int) -> str:
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
    
    return f"Cancelled order {repr(cancelled_trade)}"
