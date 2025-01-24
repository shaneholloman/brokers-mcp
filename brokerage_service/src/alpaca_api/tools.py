import asyncio
from alpaca.trading.requests import LimitOrderRequest, TakeProfitRequest, StopLossRequest, GetOrderByIdRequest, ReplaceOrderRequest, ClosePositionRequest
from alpaca.trading.enums import OrderSide, OrderClass, OrderStatus, OrderType, TimeInForce

from common_lib.alpaca_helpers.async_impl.trading_client import AsyncTradingClient
from common_lib.alpaca_helpers.env import AlpacaSettings
from common_lib.util import is_market_open

settings = AlpacaSettings()

trading_client = AsyncTradingClient(settings.api_key, settings.api_secret)

async def place_order(
    symbol: str,
    size: float,
    buy_sell: str,
    price: float,
    take_profit: float | None = None,
    stop_loss: float | None = None,

) -> str:
    """
    Place a limit order for a stock. Optionally include a take profit and stop loss to create a bracket order.

    Args:
        symbol: The symbol of the stock to place an order for
        size: The size of the order
        buy_sell: Either 'Buy' or 'Sell'
        price: The limit price of the order
        take_profit: The take profit price, optional
        stop_loss: The stop loss price, optional
    """
    if not is_market_open():
        raise Exception("Market is not open")

    if buy_sell.upper() == "BUY":
        side = OrderSide.BUY
    else:
        side = OrderSide.SELL

    order_request = LimitOrderRequest(
        symbol=symbol,
        qty=size,
        side=side,
        limit_price=price,
        type=OrderType.LIMIT,
        order_class=OrderClass.BRACKET if take_profit or stop_loss else OrderClass.SIMPLE,
        time_in_force=TimeInForce.DAY,
    )

    if take_profit:
        order_request.take_profit = TakeProfitRequest(
            limit_price=take_profit
        )
    if stop_loss:
        order_request.stop_loss = StopLossRequest(
            stop_price=stop_loss
        )

    submitted_order = await trading_client.submit_order(order_request)
    retries = 5
    while submitted_order.status in [
        OrderStatus.PENDING_NEW,
        OrderStatus.ACCEPTED_FOR_BIDDING,
        OrderStatus.ACCEPTED,
    ] and retries > 0:
        retries -= 1
        await asyncio.sleep(0.1)
        submitted_order = await trading_client.get_order_by_id(submitted_order.id, GetOrderByIdRequest(nested=True))
    
    if submitted_order.status in [OrderStatus.PENDING_CANCEL, OrderStatus.CANCELED, OrderStatus.EXPIRED, OrderStatus.REJECTED, OrderStatus.STOPPED, OrderStatus.SUSPENDED, OrderStatus.PENDING_NEW]:
        raise Exception(f"Order failed to be placed: {submitted_order.status.value}")

    placed_order_string = f"Order {submitted_order.id} successfully placed for {symbol} {size} {buy_sell} at {price}, order status: {submitted_order.status.value}"
    if take_profit:
        take_profit_order = [order for order in submitted_order.legs if order.limit_price][0]
        placed_order_string += "\n --> "
        placed_order_string += f"Take profit at {take_profit}, take profit order id: {take_profit_order.id}, order status: {take_profit_order.status.value}"
    if stop_loss:
        stop_loss_order = [order for order in submitted_order.legs if order.stop_price][0]
        placed_order_string += "\n --> "
        placed_order_string += f"Stop loss at {stop_loss}, stop loss order id: {stop_loss_order.id}, order status: {stop_loss_order.status.value}"

    return placed_order_string

async def modify_order(
    order_id: str,
    limit_price: float | None = None,
    stop_price: float | None = None,
    size: float | None = None,
) -> str:
    """
    Modify an existing order.

    Args:
        order_id: The id of the order to modify
        limit_price: The new limit price of the order (for limit orders), optional. 
        stop_price: The new stop price of the order (for stop orders), optional.
        size: The new size of the order, optional. If not provided, original order size will be used.
    """
    if limit_price and stop_price:
        raise Exception("Cannot modify order with both limit price and stop price")
    if not limit_price and not stop_price and not size:
        raise Exception("Must provide at least one of limit price, stop price, or size")
    
    replaced_order = await trading_client.replace_order_by_id(
        order_id,
        ReplaceOrderRequest(
            limit_price=limit_price,
            stop_price=stop_price,
            qty=size,
        )
    )

    # Poll until the replaced order reaches a final status or fails
    while replaced_order.status in [
        OrderStatus.PENDING_REPLACE,
        OrderStatus.ACCEPTED_FOR_BIDDING,
        OrderStatus.ACCEPTED,
    ]:
        await asyncio.sleep(0.1)
        replaced_order = await trading_client.get_order_by_id(
            replaced_order.id,
            GetOrderByIdRequest(nested=True)
        )

    # Check if the order got canceled, expired, or rejected after replace attempt
    if replaced_order.status in [
        OrderStatus.PENDING_CANCEL,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
        OrderStatus.STOPPED,
        OrderStatus.SUSPENDED,
        OrderStatus.PENDING_REPLACE
    ]:
        raise Exception(
            f"Order failed to be modified: {replaced_order.status.value}"
        )

    # Return a success message with new details
    msg = (
        f"Order successfully replaced, new order id: {replaced_order.id}\n"
        f"New qty: {replaced_order.qty}, "
    )
    if limit_price:
        msg += f"New limit price: {replaced_order.limit_price}, "
    if stop_price:
        msg += f"New stop price: {replaced_order.stop_price}, "

    return msg

async def cancel_order(order_id: str) -> str:
    """
    Cancel an existing order. If successful, returns a string confirming cancellation.
    """
    # Initiate the cancel
    await trading_client.cancel_order_by_id(order_id)

    # Poll the order until we see it's canceled (or some other final state)
    order = await trading_client.get_order_by_id(order_id, GetOrderByIdRequest(nested=True))
    while order.status not in [
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
        OrderStatus.STOPPED,
        OrderStatus.SUSPENDED
    ]:
        await asyncio.sleep(0.1)
        order = await trading_client.get_order_by_id(order_id, GetOrderByIdRequest(nested=True))

    # Check final status
    if order.status == OrderStatus.CANCELED:
        return f"Order {order_id} was successfully canceled."
    else:
        raise Exception(
            f"Order {order_id} was not canceled. Final status: {order.status.value}"
        )
    
async def liquidate_position(symbol: str) -> str:
    """
    Liquidate 100% of a position in a given symbol. This also cancels all open orders for the symbol.
    """
    try:
        await trading_client.close_position(symbol, ClosePositionRequest(percentage="100"))
        return f"Position {symbol} was successfully liquidated."
    except Exception as e:
        return f"Failed to liquidate position {symbol}: {repr(e)}"