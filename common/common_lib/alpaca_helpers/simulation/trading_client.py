from datetime import datetime
from typing import Optional, List, Union
from uuid import UUID, uuid4
import json

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

from .db import Database, Order, Position, Asset, Account

class SimulationTradingClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        oauth_token: Optional[str] = None,
        paper: bool = True,
        raw_data: bool = False,
        url_override: Optional[str] = None,
        db_path: str = "sqlite+aiosqlite:///simulation_trading.db"
    ) -> None:
        """
        Initializes a simulated trading client that mirrors the real Alpaca trading client
        but uses SQLite for storage.

        Args:
            db_path (str): SQLAlchemy database URL
        """
        self._use_raw_data = raw_data
        self.db = Database(db_path)

    async def __aenter__(self):
        await self.db.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()

    async def submit_order(self, order_data: OrderRequest) -> Union[AlpacaOrder, RawData]:
        """Creates a simulated order with optional take profit and stop loss orders"""
        order_id = str(uuid4())
        now = datetime.now()
        
        async with (await self.db.get_session()) as session:
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
                
            # Add all orders to session
            session.add(order)
            for leg_order in leg_orders:
                session.add(leg_order)
                
            await session.commit()
            
            if self._use_raw_data:
                return order.__dict__
            
            return AlpacaOrder(**order.__dict__)

    async def get_orders(
        self, filter: Optional[GetOrdersRequest] = None
    ) -> Union[List[AlpacaOrder], RawData]:
        """Gets all simulated orders"""
        async with (await self.db.get_session()) as session:
            query = session.query(Order)
            
            if filter:
                if filter.status:
                    query = query.filter(Order.status == filter.status)
                if filter.limit:
                    query = query.limit(filter.limit)
            
            orders = await query.all()
            
            if self._use_raw_data:
                return [order.__dict__ for order in orders]
            
            return [AlpacaOrder(**order.__dict__) for order in orders]

    async def get_order_by_id(
        self, order_id: Union[UUID, str], filter: Optional[GetOrderByIdRequest] = None
    ) -> Union[AlpacaOrder, RawData]:
        """Returns a specific order by its order id."""
        async with (await self.db.get_session()) as session:
            query = session.query(Order).filter(Order.id == str(order_id))
            order = await query.first()
            
            if not order:
                raise ValueError(f"Order with id {order_id} not found")
            
            if self._use_raw_data:
                return order.__dict__
            
            return AlpacaOrder(**order.__dict__)

    async def get_order_by_client_id(self, client_id: str) -> Union[AlpacaOrder, RawData]:
        """Returns a specific order by its client order id."""
        async with (await self.db.get_session()) as session:
            query = session.query(Order).filter(Order.client_order_id == client_id)
            order = await query.first()
            
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
        async with (await self.db.get_session()) as session:
            order = await session.query(Order).filter(Order.id == str(order_id)).first()
            
            if not order:
                raise ValueError(f"Order with id {order_id} not found")
            
            if order_data:
                update_data = order_data.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(order, key, value)
                
                order.updated_at = datetime.now()
            
            await session.commit()
            
            if self._use_raw_data:
                return order.__dict__
            
            return AlpacaOrder(**order.__dict__)

    async def cancel_orders(self) -> Union[List[CancelOrderResponse], RawData]:
        """Cancels all orders."""
        async with (await self.db.get_session()) as session:
            orders = await session.query(Order).filter(
                Order.status.in_(["new", "accepted", "partially_filled"])
            ).all()
            
            now = datetime.now()
            responses = []
            
            for order in orders:
                order.status = "canceled"
                order.canceled_at = now
                responses.append({"id": order.id, "status": 200})
            
            await session.commit()
            
            if self._use_raw_data:
                return responses
            
            return [CancelOrderResponse(**resp) for resp in responses]

    async def cancel_order_by_id(self, order_id: Union[UUID, str]) -> None:
        """Cancels a specific order by its order id."""
        async with (await self.db.get_session()) as session:
            order = await session.query(Order).filter(Order.id == str(order_id)).first()
            
            if not order:
                raise ValueError(f"Order with id {order_id} not found")
            
            order.status = "canceled"
            order.canceled_at = datetime.now()
            await session.commit()

    async def get_all_positions(self) -> Union[List[AlpacaPosition], RawData]:
        """Gets all the current open positions."""
        async with (await self.db.get_session()) as session:
            positions = await session.query(Position).all()
            
            if self._use_raw_data:
                return [pos.__dict__ for pos in positions]
            
            return [AlpacaPosition(**pos.__dict__) for pos in positions]

    async def get_open_position(
        self, symbol_or_asset_id: Union[UUID, str]
    ) -> Union[AlpacaPosition, RawData]:
        """Gets the open position for an account for a single asset."""
        async with (await self.db.get_session()) as session:
            position = await session.query(Position).filter(
                (Position.symbol == str(symbol_or_asset_id)) | 
                (Position.id == str(symbol_or_asset_id))
            ).first()
            
            if not position:
                raise ValueError(f"Position for {symbol_or_asset_id} not found")
            
            if self._use_raw_data:
                return position.__dict__
            
            return AlpacaPosition(**position.__dict__)

    async def close_all_positions(
        self, cancel_orders: Optional[bool] = None
    ) -> Union[List[ClosePositionResponse], RawData]:
        """Liquidates all positions for an account."""
        async with (await self.db.get_session()) as session:
            if cancel_orders:
                await self.cancel_orders()
            
            positions = await session.query(Position).all()
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
                session.add(order)
                await session.delete(position)
                
                responses.append({
                    "symbol": position.symbol,
                    "status": 200,
                    "order_id": order.id
                })
            
            await session.commit()
            
            if self._use_raw_data:
                return responses
            
            return [ClosePositionResponse(**resp) for resp in responses]

    async def close_position(
        self,
        symbol_or_asset_id: Union[UUID, str],
        close_options: Optional[ClosePositionRequest] = None,
    ) -> Union[AlpacaOrder, RawData]:
        """Liquidates the position for a single asset."""
        async with (await self.db.get_session()) as session:
            position = await session.query(Position).filter(
                (Position.symbol == str(symbol_or_asset_id)) | 
                (Position.id == str(symbol_or_asset_id))
            ).first()
            
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
            
            session.add(order)
            await session.delete(position)
            await session.commit()
            
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
        async with (await self.db.get_session()) as session:
            query = session.query(Asset)
            
            if filter:
                if filter.status:
                    query = query.filter(Asset.status == filter.status)
                if filter.asset_class:
                    query = query.filter(Asset.asset_class == filter.asset_class)
            
            assets = await query.all()
            
            if self._use_raw_data:
                return [asset.__dict__ for asset in assets]
            
            return [AlpacaAsset(**asset.__dict__) for asset in assets]

    async def get_asset(self, symbol_or_asset_id: Union[UUID, str]) -> Union[AlpacaAsset, RawData]:
        """Gets a specific asset."""
        async with (await self.db.get_session()) as session:
            asset = await session.query(Asset).filter(
                (Asset.symbol == str(symbol_or_asset_id)) | 
                (Asset.id == str(symbol_or_asset_id))
            ).first()
            
            if not asset:
                raise ValueError(f"Asset {symbol_or_asset_id} not found")
            
            if self._use_raw_data:
                return asset.__dict__
            
            return AlpacaAsset(**asset.__dict__)

    async def get_account(self) -> Union[TradeAccount, RawData]:
        """Gets account details."""
        async with (await self.db.get_session()) as session:
            account = await session.query(Account).first()
            
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
                session.add(account)
                await session.commit()
            
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
