from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from uuid import UUID, uuid4
import json
import asyncio
import yfinance as yf
import pandas as pd

from sqlalchemy.sql import select
from alpaca.common import RawData
from alpaca.trading.models import (
    Order as AlpacaOrder, Position as AlpacaPosition, 
    ClosePositionResponse, Asset as AlpacaAsset,
    TradeAccount, AccountConfiguration,
    PortfolioHistory
)
from alpaca.trading.requests import (
    CancelOrderResponse, OrderRequest, GetOrdersRequest, GetOrderByIdRequest,
    ReplaceOrderRequest, ClosePositionRequest,
    GetAssetsRequest, GetPortfolioHistoryRequest
)

from .db import Database, Order, Position, Asset, Account, MarketData, OrderFill

DEFAULT_ASSETS = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "exchange": "NASDAQ",
        "asset_class": "us_equity",
        "status": "active",
        "tradable": True,
        "marginable": True,
        "shortable": True,
        "easy_to_borrow": True,
        "fractionable": True,
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "asset_class": "us_equity",
        "status": "active",
        "tradable": True,
        "marginable": True,
        "shortable": True,
        "easy_to_borrow": True,
        "fractionable": True,
    },
    # Add more default assets as needed
]

class SimulationTradingClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        oauth_token: Optional[str] = None,
        paper: bool = True,
        raw_data: bool = False,
        url_override: Optional[str] = None,
        db_path: str = "sqlite+aiosqlite:///simulation_trading.db",
        initial_cash: float = 100000.0
    ) -> None:
        """
        Initializes a simulated trading client that mirrors the real Alpaca trading client
        but uses SQLite for storage.

        Args:
            db_path (str): SQLAlchemy database URL
            initial_cash (float): Initial cash balance for the account
        """
        self._use_raw_data = raw_data
        self.db = Database(db_path)
        self._order_update_task = None
        self._market_data_update_task = None
        self._initial_cash = str(initial_cash)

    async def _initialize_db(self):
        """Initialize database with default data"""
        try:
            # Create tables
            await self.db.initialize()
            
            # Check if we need to initialize default data
            account = await self.db.get_account()
            if not account:
                # Create default account
                account = Account(
                    id=str(uuid4()),
                    cash=self._initial_cash,
                    buying_power=self._initial_cash,
                    regt_buying_power=self._initial_cash,
                    daytrading_buying_power=str(float(self._initial_cash) * 4),  # 4x leverage
                    non_marginable_buying_power=self._initial_cash,
                    cash_withdrawable=self._initial_cash,
                    currency="USD",
                    pattern_day_trader=False,
                    trading_blocked=False,
                    transfers_blocked=False,
                    account_blocked=False,
                    created_at=datetime.now(),
                    status="ACTIVE",
                    last_equity=self._initial_cash,
                    last_maintenance_margin="0",
                    last_initial_margin="0",
                    last_updated=datetime.now()
                )
                await self.db.add(account)
            
            # Initialize default assets if none exist
            assets = await self.db.get_all(Asset)
            if not assets:
                for asset_data in DEFAULT_ASSETS:
                    asset = Asset(
                        id=str(uuid4()),
                        last_updated=datetime.now(),
                        **asset_data
                    )
                    await self.db.add(asset)
                
                # Initialize market data for default assets
                for asset_data in DEFAULT_ASSETS:
                    symbol = asset_data["symbol"]
                    try:
                        ticker = yf.Ticker(symbol)
                        hist = ticker.history(period="1d", interval="1m")
                        if not hist.empty:
                            market_data = []
                            for timestamp, row in hist.iterrows():
                                market_data.append(MarketData(
                                    symbol=symbol,
                                    timestamp=timestamp.to_pydatetime(),
                                    open=float(row['Open']),
                                    high=float(row['High']),
                                    low=float(row['Low']),
                                    close=float(row['Close']),
                                    volume=int(row['Volume']),
                                    timeframe="1min"
                                ))
                            await self.db.add_all(market_data)
                    except Exception as e:
                        print(f"Error initializing market data for {symbol}: {e}")

        except Exception as e:
            print(f"Error initializing database: {e}")
            raise

    async def __aenter__(self):
        # Initialize database first
        await self._initialize_db()
        # Then start background tasks
        self._order_update_task = asyncio.create_task(self._update_orders())
        self._market_data_update_task = asyncio.create_task(self._update_market_data())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cancel background tasks
        if self._order_update_task:
            self._order_update_task.cancel()
        if self._market_data_update_task:
            self._market_data_update_task.cancel()
        await self.db.close()

    async def _update_market_data(self):
        """Background task to update market data using yfinance"""
        while True:
            try:
                # Get all unique symbols from orders and positions
                symbols = set()
                async with self.db.async_session() as session:
                    # Get symbols from orders
                    stmt = select(Order.symbol).distinct()
                    result = await session.execute(stmt)
                    symbols.update(row[0] for row in result)
                    
                    # Get symbols from positions
                    stmt = select(Position.symbol).distinct()
                    result = await session.execute(stmt)
                    symbols.update(row[0] for row in result)

                for symbol in symbols:
                    # Get latest data from yfinance
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="1d", interval="1m")
                    if hist.empty:
                        continue

                    # Convert to MarketData objects
                    market_data = []
                    for timestamp, row in hist.iterrows():
                        market_data.append(MarketData(
                            symbol=symbol,
                            timestamp=timestamp.to_pydatetime(),
                            open=float(row['Open']),
                            high=float(row['High']),
                            low=float(row['Low']),
                            close=float(row['Close']),
                            volume=int(row['Volume']),
                            timeframe="1min"
                        ))
                    
                    await self.db.add_all(market_data)

            except Exception as e:
                print(f"Error updating market data: {e}")
            
            await asyncio.sleep(60)  # Update every minute

    async def _update_orders(self):
        """Background task to update order status based on market data"""
        while True:
            try:
                # Get all open orders
                open_orders = await self.db.get_open_orders()
                
                for order in open_orders:
                    # Get latest price
                    latest_price = await self.db.get_latest_price(order.symbol)
                    if not latest_price:
                        continue

                    # Check if order should be filled
                    should_fill = False
                    fill_price = latest_price

                    if order.type == "market":
                        should_fill = True
                    elif order.type == "limit":
                        if order.side == "buy" and float(latest_price) <= float(order.limit_price):
                            should_fill = True
                            fill_price = float(order.limit_price)
                        elif order.side == "sell" and float(latest_price) >= float(order.limit_price):
                            should_fill = True
                            fill_price = float(order.limit_price)
                    elif order.type == "stop":
                        if order.side == "sell" and float(latest_price) <= float(order.stop_price):
                            should_fill = True
                        elif order.side == "buy" and float(latest_price) >= float(order.stop_price):
                            should_fill = True

                    if should_fill:
                        # Create order fill
                        fill = OrderFill(
                            order_id=order.id,
                            timestamp=datetime.now(),
                            price=fill_price,
                            qty=float(order.qty)
                        )
                        
                        # Update order
                        await self.db.update(order,
                            status="filled",
                            filled_at=datetime.now(),
                            filled_qty=order.qty,
                            filled_avg_price=str(fill_price)
                        )
                        
                        # Add fill
                        await self.db.add(fill)
                        
                        # Update position
                        await self._update_position(order, fill_price)

            except Exception as e:
                print(f"Error updating orders: {e}")
            
            await asyncio.sleep(1)  # Check every second

    async def _update_position(self, order: Order, fill_price: float):
        """Update position after order fill"""
        position = await self.db.get_position(order.symbol)
        qty = float(order.qty)
        
        if order.side == "sell":
            qty = -qty
            
        if position:
            # Update existing position
            new_qty = float(position.qty) + qty
            if new_qty == 0:
                # Position closed
                await self.db.delete(position)
            else:
                # Update position
                avg_price = (float(position.avg_entry_price) * float(position.qty) + fill_price * qty) / new_qty
                await self.db.update(position,
                    qty=str(abs(new_qty)),
                    side="long" if new_qty > 0 else "short",
                    avg_entry_price=str(avg_price),
                    market_value=str(new_qty * fill_price),
                    current_price=str(fill_price)
                )
        else:
            # Create new position
            position = Position(
                id=str(uuid4()),
                symbol=order.symbol,
                qty=str(abs(qty)),
                side="long" if qty > 0 else "short",
                avg_entry_price=str(fill_price),
                market_value=str(qty * fill_price),
                cost_basis=str(qty * fill_price),
                unrealized_pl="0",
                unrealized_plpc="0",
                current_price=str(fill_price),
                lastday_price=str(fill_price),
                change_today="0",
                realized_pl="0",
                realized_plpc="0"
            )
            await self.db.add(position)

    async def submit_order(self, order_data: OrderRequest) -> Union[AlpacaOrder, RawData]:
        """Creates a simulated order with optional take profit and stop loss orders"""
        order_id = str(uuid4())
        now = datetime.now()
        
        # Create main order
        order = Order(
            id=order_id,
            client_order_id=str(uuid4()),
            created_at=now,
            submitted_at=now,
            symbol=order_data.symbol,
            qty=str(order_data.qty),
            side=order_data.side,
            type=order_data.type,
            time_in_force=order_data.time_in_force,
            limit_price=str(order_data.limit_price) if order_data.limit_price else None,
            stop_price=str(order_data.stop_price) if order_data.stop_price else None,
            status="new"
        )
        
        leg_orders = []
        
        # Create take profit order if specified
        if hasattr(order_data, 'take_profit_price') and order_data.take_profit_price:
            tp_order = Order(
                id=str(uuid4()),
                client_order_id=str(uuid4()),
                created_at=now,
                symbol=order_data.symbol,
                qty=str(order_data.qty),
                side="sell" if order_data.side == "buy" else "buy",
                type="limit",
                time_in_force="gtc",
                limit_price=str(order_data.take_profit_price),
                status="held"
            )
            leg_orders.append(tp_order)
        
        # Create stop loss order if specified
        if hasattr(order_data, 'stop_loss_price') and order_data.stop_loss_price:
            sl_order = Order(
                id=str(uuid4()),
                client_order_id=str(uuid4()),
                created_at=now,
                symbol=order_data.symbol,
                qty=str(order_data.qty),
                side="sell" if order_data.side == "buy" else "buy",
                type="stop",
                time_in_force="gtc",
                stop_price=str(order_data.stop_loss_price),
                status="held"
            )
            leg_orders.append(sl_order)
        
        # Add leg order references to main order
        if leg_orders:
            order.legs = json.dumps([leg.id for leg in leg_orders])
            
        # Add orders to database
        await self.db.add(order)
        for leg_order in leg_orders:
            await self.db.add(leg_order)
        
        if self._use_raw_data:
            return order.__dict__
        
        return AlpacaOrder(**order.__dict__)

    async def get_orders(
        self, filter: Optional[GetOrdersRequest] = None
    ) -> Union[List[AlpacaOrder], RawData]:
        """Gets all simulated orders"""
        stmt = select(Order)
        
        if filter:
            if filter.status:
                stmt = stmt.where(Order.status == filter.status)
            if filter.limit:
                stmt = stmt.limit(filter.limit)
        
        result = await self.db.execute(stmt)
        orders = list(result.scalars().all())
        
        if self._use_raw_data:
            return [order.__dict__ for order in orders]
        
        return [AlpacaOrder(**order.__dict__) for order in orders]

    async def get_order_by_id(
        self, order_id: Union[UUID, str], filter: Optional[GetOrderByIdRequest] = None
    ) -> Union[AlpacaOrder, RawData]:
        """Returns a specific order by its order id."""
        order = await self.db.get(Order, str(order_id))
        
        if not order:
            raise ValueError(f"Order with id {order_id} not found")
        
        if self._use_raw_data:
            return order.__dict__
        
        return AlpacaOrder(**order.__dict__)

    async def get_order_by_client_id(self, client_id: str) -> Union[AlpacaOrder, RawData]:
        """Returns a specific order by its client order id."""
        async with self.db.async_session() as session:
            stmt = select(Order).where(Order.client_order_id == client_id)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()
            
            if not order:
                raise ValueError(f"Order with client_id {client_id} not found")
            
            if self._use_raw_data:
                return order.__dict__
            
            return AlpacaOrder(**order.__dict__)

    async def replace_order_by_id(
        self,
        order_id: Union[UUID, str],
        order_data: Optional[ReplaceOrderRequest] = None,
    ) -> Union[AlpacaOrder, RawData]:
        """Updates an order with new parameters."""
        order = await self.db.get(Order, str(order_id))
        
        if not order:
            raise ValueError(f"Order with id {order_id} not found")
        
        if order_data:
            update_data = order_data.model_dump(exclude_unset=True)
            await self.db.update(order, **update_data, updated_at=datetime.now())
        
        if self._use_raw_data:
            return order.__dict__
        
        return AlpacaOrder(**order.__dict__)

    async def cancel_orders(self) -> Union[List[CancelOrderResponse], RawData]:
        """Cancels all orders."""
        async with self.db.async_session() as session:
            stmt = select(Order).where(Order.status.in_(["new", "accepted", "partially_filled"]))
            result = await session.execute(stmt)
            orders = list(result.scalars().all())
            
            now = datetime.now()
            responses = []
            
            for order in orders:
                await self.db.update(order,
                    status="canceled",
                    canceled_at=now
                )
                responses.append({"id": order.id, "status": 200})
            
            if self._use_raw_data:
                return responses
            
            return [CancelOrderResponse(**resp) for resp in responses]

    async def cancel_order_by_id(self, order_id: Union[UUID, str]) -> None:
        """Cancels a specific order by its order id."""
        order = await self.db.get(Order, str(order_id))
        
        if not order:
            raise ValueError(f"Order with id {order_id} not found")
        
        await self.db.update(order,
            status="canceled",
            canceled_at=datetime.now()
        )

    async def get_all_positions(self) -> Union[List[AlpacaPosition], RawData]:
        """Gets all the current open positions."""
        positions = await self.db.get_all(Position)
        
        if self._use_raw_data:
            return [pos.__dict__ for pos in positions]
        
        return [AlpacaPosition(**pos.__dict__) for pos in positions]

    async def get_open_position(
        self, symbol_or_asset_id: Union[UUID, str]
    ) -> Union[AlpacaPosition, RawData]:
        """Gets the open position for an account for a single asset."""
        position = await self.db.get_position(str(symbol_or_asset_id))
        
        if not position:
            raise ValueError(f"Position for {symbol_or_asset_id} not found")
        
        if self._use_raw_data:
            return position.__dict__
        
        return AlpacaPosition(**position.__dict__)

    async def close_all_positions(
        self, cancel_orders: Optional[bool] = None
    ) -> Union[List[ClosePositionResponse], RawData]:
        """Liquidates all positions for an account."""
        if cancel_orders:
            await self.cancel_orders()
        
        positions = await self.db.get_all(Position)
        responses = []
        
        for position in positions:
            # Create closing order
            order = Order(
                id=str(uuid4()),
                client_order_id=str(uuid4()),
                created_at=datetime.now(),
                submitted_at=datetime.now(),
                symbol=position.symbol,
                qty=position.qty,
                side="sell" if position.side == "long" else "buy",
                type="market",
                time_in_force="day",
                status="filled"
            )
            await self.db.add(order)
            await self.db.delete(position)
            
            responses.append({
                "symbol": position.symbol,
                "status": 200,
                "order_id": order.id
            })
        
        if self._use_raw_data:
            return responses
        
        return [ClosePositionResponse(**resp) for resp in responses]

    async def close_position(
        self,
        symbol_or_asset_id: Union[UUID, str],
        close_options: Optional[ClosePositionRequest] = None,
    ) -> Union[AlpacaOrder, RawData]:
        """Liquidates the position for a single asset."""
        position = await self.db.get_position(str(symbol_or_asset_id))
        
        if not position:
            raise ValueError(f"Position for {symbol_or_asset_id} not found")
        
        # Create closing order
        order = Order(
            id=str(uuid4()),
            client_order_id=str(uuid4()),
            created_at=datetime.now(),
            submitted_at=datetime.now(),
            symbol=position.symbol,
            qty=position.qty if not close_options else str(close_options.qty),
            side="sell" if position.side == "long" else "buy",
            type="market",
            time_in_force="day",
            status="filled"
        )
        
        await self.db.add(order)
        await self.db.delete(position)
        
        if self._use_raw_data:
            return order.__dict__
        
        return AlpacaOrder(**order.__dict__)

    async def get_portfolio_history(
        self,
        history_filter: Optional[GetPortfolioHistoryRequest] = None,
    ) -> Union[PortfolioHistory, RawData]:
        """Gets the portfolio history statistics for an account."""
        # For simulation, return basic portfolio history
        history = {
            "timestamp": [int(datetime.now().timestamp())],
            "equity": ["100000"],
            "profit_loss": ["0"],
            "profit_loss_pct": ["0"],
            "base_value": "100000",
            "timeframe": "1D"
        }
        
        if self._use_raw_data:
            return history
        
        return PortfolioHistory(**history)

    async def get_all_assets(
        self, filter: Optional[GetAssetsRequest] = None
    ) -> Union[List[AlpacaAsset], RawData]:
        """Gets list of assets."""
        stmt = select(Asset)
        
        if filter:
            if filter.status:
                stmt = stmt.where(Asset.status == filter.status)
            if filter.asset_class:
                stmt = stmt.where(Asset.asset_class == filter.asset_class)
        
        result = await self.db.execute(stmt)
        assets = list(result.scalars().all())
        
        if self._use_raw_data:
            return [asset.__dict__ for asset in assets]
        
        return [AlpacaAsset(**asset.__dict__) for asset in assets]

    async def get_asset(self, symbol_or_asset_id: Union[UUID, str]) -> Union[AlpacaAsset, RawData]:
        """Gets a specific asset."""
        asset = await self.db.get_asset(str(symbol_or_asset_id))
        
        if not asset:
            raise ValueError(f"Asset {symbol_or_asset_id} not found")
        
        if self._use_raw_data:
            return asset.__dict__
        
        return AlpacaAsset(**asset.__dict__)

    async def get_account(self) -> Union[TradeAccount, RawData]:
        """Gets account details."""
        account = await self.db.get_account()
        
        if not account:
            # Create default account if none exists
            account = Account(
                id=str(uuid4()),
                cash="100000",
                buying_power="100000",
                created_at=datetime.now(),
                currency="USD",
                status="ACTIVE",
                pattern_day_trader=False,
                trading_blocked=False,
                transfers_blocked=False,
                account_blocked=False
            )
            await self.db.add(account)
        
        if self._use_raw_data:
            return account.__dict__
        
        return TradeAccount(**account.__dict__)

    async def get_account_configurations(self) -> Union[AccountConfiguration, RawData]:
        """Gets account configuration."""
        config = {
            "dtbp_check": "both",
            "no_shorting": False,
            "suspend_trade": False,
            "trade_confirm_email": "all",
            "trade_suspended_by_user": False
        }
        
        if self._use_raw_data:
            return config
        
        return AccountConfiguration(**config)

    async def set_account_configurations(
        self, account_configurations: AccountConfiguration
    ) -> Union[AccountConfiguration, RawData]:
        """Sets account configuration."""
        if self._use_raw_data:
            return account_configurations.model_dump()
        
        return account_configurations

    async def exercise_options_position(
        self,
        symbol_or_contract_id: Union[UUID, str],
    ) -> None:
        """Exercise options position."""
        # Implement options exercise logic here
        pass
