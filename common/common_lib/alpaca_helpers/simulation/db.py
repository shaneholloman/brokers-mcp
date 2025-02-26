from datetime import datetime
from typing import Optional, List, Type, TypeVar, Any
from uuid import UUID

from sqlalchemy import create_engine, Boolean, String, DateTime, Float, Integer, ForeignKey, Index, Numeric, UniqueConstraint, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.sql import Select

class Base(DeclarativeBase):
    pass

class MarketData(Base):
    """Table for storing OHLCV market data"""
    __tablename__ = "market_data"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    open: Mapped[float] = mapped_column(Numeric(precision=10, scale=4))
    high: Mapped[float] = mapped_column(Numeric(precision=10, scale=4))
    low: Mapped[float] = mapped_column(Numeric(precision=10, scale=4))
    close: Mapped[float] = mapped_column(Numeric(precision=10, scale=4))
    volume: Mapped[int] = mapped_column(Integer)
    timeframe: Mapped[str] = mapped_column(String)  # e.g., '1min', '5min', '1day'
    
    __table_args__ = (
        Index('idx_market_data_lookup', 'symbol', 'timestamp', 'timeframe'),
        UniqueConstraint('symbol', 'timestamp', 'timeframe', name='unique_market_data')
    )

class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    client_order_id: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    symbol: Mapped[str] = mapped_column(String)
    qty: Mapped[str] = mapped_column(String)
    filled_qty: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String)  # market, limit, stop, stop_limit
    side: Mapped[str] = mapped_column(String)  # buy, sell
    time_in_force: Mapped[str] = mapped_column(String)  # day, gtc, ioc, fok
    limit_price: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stop_price: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    filled_avg_price: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)  # new, filled, partially_filled, canceled, expired, rejected, pending_new, accepted
    legs: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JSON string of related order IDs
    
    fills = relationship("OrderFill", back_populates="order")

class OrderFill(Base):
    """Table for tracking individual order fills"""
    __tablename__ = "order_fills"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(String, ForeignKey('orders.id'))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    price: Mapped[float] = mapped_column(Numeric(precision=10, scale=4))
    qty: Mapped[float] = mapped_column(Numeric(precision=10, scale=4))
    
    order = relationship("Order", back_populates="fills")

class Position(Base):
    __tablename__ = "positions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True)
    qty: Mapped[str] = mapped_column(String)
    side: Mapped[str] = mapped_column(String)  # long, short
    avg_entry_price: Mapped[str] = mapped_column(String)
    market_value: Mapped[str] = mapped_column(String)
    cost_basis: Mapped[str] = mapped_column(String)
    unrealized_pl: Mapped[str] = mapped_column(String)
    unrealized_plpc: Mapped[str] = mapped_column(String)
    current_price: Mapped[str] = mapped_column(String)
    lastday_price: Mapped[str] = mapped_column(String)
    change_today: Mapped[str] = mapped_column(String)
    realized_pl: Mapped[str] = mapped_column(String, default="0")
    realized_plpc: Mapped[str] = mapped_column(String, default="0")

class Asset(Base):
    __tablename__ = "assets"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    exchange: Mapped[str] = mapped_column(String)
    asset_class: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    tradable: Mapped[bool] = mapped_column(Boolean)
    marginable: Mapped[bool] = mapped_column(Boolean)
    shortable: Mapped[bool] = mapped_column(Boolean)
    easy_to_borrow: Mapped[bool] = mapped_column(Boolean)
    fractionable: Mapped[bool] = mapped_column(Boolean)
    last_updated: Mapped[datetime] = mapped_column(DateTime)
    
    __table_args__ = (
        Index('idx_asset_lookup', 'symbol', 'status'),
    )

class Account(Base):
    __tablename__ = "account"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    cash: Mapped[str] = mapped_column(String)
    buying_power: Mapped[str] = mapped_column(String)
    regt_buying_power: Mapped[str] = mapped_column(String, default="0")
    daytrading_buying_power: Mapped[str] = mapped_column(String, default="0")
    non_marginable_buying_power: Mapped[str] = mapped_column(String, default="0")
    cash_withdrawable: Mapped[str] = mapped_column(String, default="0")
    currency: Mapped[str] = mapped_column(String)
    pattern_day_trader: Mapped[bool] = mapped_column(Boolean)
    trading_blocked: Mapped[bool] = mapped_column(Boolean)
    transfers_blocked: Mapped[bool] = mapped_column(Boolean)
    account_blocked: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String)
    last_equity: Mapped[str] = mapped_column(String, default="0")
    last_maintenance_margin: Mapped[str] = mapped_column(String, default="0")
    last_initial_margin: Mapped[str] = mapped_column(String, default="0")
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

T = TypeVar('T', bound=Base)

class Database:
    def __init__(self, db_url: str = "sqlite+aiosqlite:///simulation_trading.db"):
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = async_sessionmaker(self.engine, class_=AsyncSession)

    async def initialize(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        """Get a database session"""
        return self.async_session()

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()

    async def add(self, obj: Base) -> None:
        """Add a single object to the database"""
        async with self.async_session() as session:
            session.add(obj)
            await session.commit()

    async def add_all(self, objects: List[Base]) -> None:
        """Add multiple objects to the database"""
        async with self.async_session() as session:
            session.add_all(objects)
            await session.commit()

    async def get(self, model: Type[T], id: Any) -> Optional[T]:
        """Get a single object by its primary key"""
        async with self.async_session() as session:
            stmt = select(model).where(model.id == id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all(self, model: Type[T]) -> List[T]:
        """Get all objects of a given model"""
        async with self.async_session() as session:
            stmt = select(model)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def execute(self, stmt: Select) -> Any:
        """Execute a custom select statement"""
        async with self.async_session() as session:
            result = await session.execute(stmt)
            return result

    async def delete(self, obj: Base) -> None:
        """Delete an object from the database"""
        async with self.async_session() as session:
            await session.delete(obj)
            await session.commit()

    async def update(self, obj: Base, **kwargs) -> None:
        """Update an object with given attributes"""
        async with self.async_session() as session:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            session.add(obj)
            await session.commit()

    # Market Data specific methods
    async def get_latest_price(self, symbol: str, timeframe: str = "1min") -> Optional[float]:
        """Get the latest price for a symbol"""
        async with self.async_session() as session:
            stmt = (
                select(MarketData)
                .where(MarketData.symbol == symbol)
                .where(MarketData.timeframe == timeframe)
                .order_by(MarketData.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            market_data = result.scalar_one_or_none()
            return float(market_data.close) if market_data else None

    async def get_bars(
        self, 
        symbol: str, 
        timeframe: str = "1min",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[MarketData]:
        """Get historical bars for a symbol"""
        async with self.async_session() as session:
            stmt = select(MarketData).where(
                MarketData.symbol == symbol,
                MarketData.timeframe == timeframe
            )
            
            if start:
                stmt = stmt.where(MarketData.timestamp >= start)
            if end:
                stmt = stmt.where(MarketData.timestamp <= end)
                
            stmt = stmt.order_by(MarketData.timestamp.desc())
            
            if limit:
                stmt = stmt.limit(limit)
                
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # Order specific methods
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders, optionally filtered by symbol"""
        async with self.async_session() as session:
            stmt = select(Order).where(
                Order.status.in_(['new', 'accepted', 'partially_filled'])
            )
            if symbol:
                stmt = stmt.where(Order.symbol == symbol)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # Position specific methods
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol"""
        async with self.async_session() as session:
            stmt = select(Position).where(Position.symbol == symbol)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    # Account specific methods
    async def get_account(self) -> Optional[Account]:
        """Get the trading account"""
        async with self.async_session() as session:
            stmt = select(Account)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    # Asset specific methods
    async def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get asset information by symbol"""
        async with self.async_session() as session:
            stmt = select(Asset).where(Asset.symbol == symbol)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
