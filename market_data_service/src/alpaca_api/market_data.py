from datetime import datetime
import logging
from typing import Optional
from common_lib.alpaca_helpers.async_impl.stock_client import (
    AsyncStockHistoricalDataClient,
)
from common_lib.alpaca_helpers.env import AlpacaSettings
import pandas as pd
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from pandas.tseries.offsets import BDay, BusinessHour
import pytz
from ta.indicators import add_indicators_to_bars_df, indicator_min_bars_back, plot_bars
from mcp.server.fastmcp import Image

# Initialize Alpaca client
settings = AlpacaSettings()
stock_client = AsyncStockHistoricalDataClient(settings.api_key, settings.api_secret)

SUPPORTED_INDICATORS = [
    "sma_{period}",
    "ema_{period}",
    "rsi_{window_period}",
    "macd_{fast_period}_{slow_period}_{signal_period}",
    "bbands_{window_period}_{num_std}",
]

logger = logging.getLogger(__name__)


def get_timeframe(unit: str, bar_size: int) -> TimeFrame:
    """Convert unit and bar_size to Alpaca TimeFrame"""
    unit = unit.upper()
    if unit == "MINUTE":
        if bar_size <= 59:
            return TimeFrame(amount=bar_size, unit=TimeFrameUnit.Minute)
        else:
            return TimeFrame(amount=bar_size // 60, unit=TimeFrameUnit.Hour)
    elif unit == "HOUR":
        return TimeFrame(amount=bar_size, unit=TimeFrameUnit.Hour)
    elif unit == "DAILY":
        return TimeFrame(amount=bar_size, unit=TimeFrameUnit.Day)
    elif unit == "WEEKLY":
        return TimeFrame(amount=bar_size, unit=TimeFrameUnit.Week)
    elif unit == "MONTHLY":
        return TimeFrame(amount=bar_size, unit=TimeFrameUnit.Month)
    else:
        raise ValueError(f"Unsupported unit: {unit}")


def default_bars_back(unit: str, bar_size: int) -> int:
    unit = unit.upper()
    if unit == "MINUTE":
        return 1170 // bar_size  # 3 days
    elif unit == "HOUR":
        return 5 * 24 // bar_size  # 1 week
    elif unit == "DAILY":
        return 30 // bar_size  # 30 days
    elif unit == "WEEKLY":
        return 52 // bar_size  # 52 weeks
    elif unit == "MONTHLY":
        return 24 // bar_size  # 24 months
    else:
        raise ValueError(f"Unknown unit: {unit}")


def bars_back_to_datetime(
    unit: str, bar_size: int, bars_back: int
) -> datetime:
    now = datetime.now(tz=pytz.timezone("US/Eastern"))
    if unit == "Minute":
        total_minutes = bars_back * bar_size
        hours = (total_minutes // 60) + 1
        return bars_back_to_datetime("Hour", 1, hours)

    elif unit == "Hour":
        # 1 'business hour' bar => skip Sat/Sun
        interval = BusinessHour(n=bar_size, start="09:30", end="16:00")

    elif unit == "Daily":
        # 1 'business day' bar => skip Sat/Sun
        interval = BDay(n=bar_size)

    elif unit == "Weekly":
        # 1 'weekly' bar => treat that as 5 business days
        interval = BDay(n=5 * bar_size)

    elif unit == "Monthly":
        # Often approximate 21 business days per month
        interval = BDay(n=21 * bar_size)

    else:
        raise ValueError(f"Unknown unit: {unit}")
        
    return now - (interval * (bars_back + 10)) # the + 10 is a safety margin in 


async def get_alpaca_bars(
    symbol: str,
    unit: str,
    bars_back: Optional[int] = None,
    bar_size: int = 1,
    indicators: Optional[str] = None,
    truncate_bars: bool = True,
) -> str:
    """Get historical bars data for a stock symbol"""
    timeframe = get_timeframe(unit, bar_size)
    original_bars_back = bars_back or default_bars_back(unit, bar_size)

    if indicators:
        min_bars_back = max(indicator_min_bars_back(i) for i in indicators.split(","))
        bars_back = min_bars_back + (bars_back or 0)
    else:
        bars_back = original_bars_back

    start = bars_back_to_datetime(unit, bar_size, bars_back)
    # Create the request
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start,
        end=datetime.now(),
        adjustment="all",
        feed="iex",  # todo: switch to SIP when subscribed to real time alpaca data
    )

    # Get the bars
    bars_df = (await stock_client.get_stock_bars(request)).df
    if isinstance(bars_df.index, pd.MultiIndex):
        bars_df = bars_df.xs(symbol)

    bars_df.drop(columns=["trade_count"], inplace=True)
    # Convert index timezone to US/Eastern
    bars_df.index = bars_df.index.tz_convert("US/Eastern").tz_localize(None)

    # Add indicators if requested
    if indicators:
        indicator_list = [i.strip() for i in indicators.split(",")]
        add_indicators_to_bars_df(bars_df, indicator_list)

    # Format datetime
    bars_df = bars_df.reset_index()
    bars_df["timestamp"] = bars_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    bars_df = bars_df.rename(columns={"timestamp": "datetime"})
    if truncate_bars:
        bars_df = bars_df.iloc[-original_bars_back:]

    return bars_df.to_json(orient="records", lines=True)


async def plot_alpaca_bars_with_indicators(
    symbol: str,
    unit: str,
    bar_size: int,
    indicators: str = "",
    bars_back: Optional[int] = None,
) -> tuple[Image, str]:
    """Plot bars with indicators using Alpaca data"""
    bars_back_requested = bars_back if bars_back else default_bars_back(unit, bar_size)
    bars_df = pd.read_json(
        await get_alpaca_bars(
            symbol=symbol,
            unit=unit,
            bar_size=bar_size,
            indicators=indicators,
            bars_back=bars_back_requested,
            truncate_bars=False,
        ),
        lines=True,
        orient="records",
    )

    bars_df["datetime"] = pd.to_datetime(
        bars_df["datetime"], format="%Y-%m-%d %H:%M:%S"
    )
    bars_df.set_index("datetime", inplace=True)

    # Generate the plot
    buf = plot_bars(
        bars_df.iloc[-bars_back_requested:],
        f"{symbol} bar size: {bar_size} bar unit: {unit} bar count: {bars_back_requested} ",
    )

    bars_df.reset_index(inplace=True)
    bars_df["datetime"] = bars_df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Return both the image and the data
    return (
        Image(data=buf.read(), format="png"),
        bars_df.iloc[-bars_back_requested:]
        .to_json(orient="records", lines=True),
    )
