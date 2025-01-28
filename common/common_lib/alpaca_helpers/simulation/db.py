from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import create_engine, Boolean, String, DateTime, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

class Base(DeclarativeBase):
    pass

class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    client_order_id: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    asset_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    symbol: Mapped[str] = mapped_column(String)
    asset_class: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    qty: Mapped[str] = mapped_column(String)
    filled_qty: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String)
    side: Mapped[str] = mapped_column(String)
    time_in_force: Mapped[str] = mapped_column(String)
    limit_price: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stop_price: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    filled_avg_price: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)
    extended_hours: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    legs: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    trail_percent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    trail_price: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hwm: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class Position(Base):
    __tablename__ = "positions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True)
    qty: Mapped[str] = mapped_column(String)
    side: Mapped[str] = mapped_column(String)
    avg_entry_price: Mapped[str] = mapped_column(String)
    market_value: Mapped[str] = mapped_column(String)
    cost_basis: Mapped[str] = mapped_column(String)
    unrealized_pl: Mapped[str] = mapped_column(String)
    unrealized_plpc: Mapped[str] = mapped_column(String)
    current_price: Mapped[str] = mapped_column(String)
    lastday_price: Mapped[str] = mapped_column(String)
    change_today: Mapped[str] = mapped_column(String)

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

class Account(Base):
    __tablename__ = "account"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    cash: Mapped[str] = mapped_column(String)
    buying_power: Mapped[str] = mapped_column(String)
    regt_buying_power: Mapped[str] = mapped_column(String)
    daytrading_buying_power: Mapped[str] = mapped_column(String)
    non_marginable_buying_power: Mapped[str] = mapped_column(String)
    cash_withdrawable: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String)
    pattern_day_trader: Mapped[bool] = mapped_column(Boolean)
    trading_blocked: Mapped[bool] = mapped_column(Boolean)
    transfers_blocked: Mapped[bool] = mapped_column(Boolean)
    account_blocked: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String)

class Database:
    def __init__(self, db_url: str = "sqlite:///simulation_trading.db"):
        self.engine = create_async_engine(db_url)
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
