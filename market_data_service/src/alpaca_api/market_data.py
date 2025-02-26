from datetime import datetime, timedelta
import logging
import math
from typing import Optional
from common_lib.alpaca_helpers.async_impl.stock_client import (
    AsyncStockHistoricalDataClient,
)
from common_lib.alpaca_helpers.env import AlpacaSettings
from common_lib.mcp import get_current_market_time, is_realtime
import pandas as pd
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from pandas.tseries.offsets import BDay, BusinessHour
from ta.indicators import add_indicators_to_bars_df, indicator_min_bars_back, plot_bars
from mcp.server.fastmcp import Image

# Initialize Alpaca client
settings = AlpacaSettings()
stock_client = AsyncStockHistoricalDataClient(settings.api_key, settings.api_secret)

SUPPORTED_INDICATORS = {
    "sma_{period}": {
        "df_columns": ["sma_{period}"]
    },
    "ema_{period}": {
        "df_columns": ["ema_{period}"]
    },
    "rsi_{window_period}": {
        "df_columns": ["rsi_{window_period}"]
    },
    "macd_{fast_period}_{slow_period}_{signal_period}": {
        "df_columns": [
            "macd_{fast_period}_{slow_period}_{signal_period}",
            "macd_signal_{fast_period}_{slow_period}_{signal_period}",
            "macd_histogram_{fast_period}_{slow_period}_{signal_period}"
        ]
    },
    "bbands_{window_period}_{num_std}": {
        "df_columns": [
            "bb_upper_{window_period}_{num_std}",
            "bb_middle_{window_period}_{num_std}",
            "bb_lower_{window_period}_{num_std}"
        ]
    }
}

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
    if unit == "MINUTE" and bar_size < 5:
        return 120 // bar_size  # 2 hours
    elif unit == "MINUTE" and bar_size < 15:
        return 60 * 7 // bar_size  # 1 day
    elif unit == "MINUTE" and bar_size < 30:
        return 60 * 13 // bar_size  # 2 days
    elif unit == "HOUR":
        return 5 * 24 // bar_size  # 1 week
    elif unit == "DAILY":
        return 30 // bar_size  # 30 days
    elif unit == "WEEKLY":
        return 26 // bar_size  # 26 weeks
    elif unit == "MONTHLY":
        return 12 // bar_size  # 12 months
    else:
        raise ValueError(f"Unknown unit: {unit}")


def bars_back_to_datetime(
    unit: str, bar_size: int, bars_back: int
) -> datetime:
    now = get_current_market_time()
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
        
    return now - (interval * (bars_back + 10)) # the + 10 is a safety margin


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
    if is_realtime() or timeframe.unit in [TimeFrameUnit.Minute, TimeFrameUnit.Hour]:
        end = get_current_market_time()
    else:
        if timeframe.unit == TimeFrameUnit.Day:
            end = get_current_market_time() - timedelta(days=1)
        elif timeframe.unit == TimeFrameUnit.Week:
            end = get_current_market_time() - timedelta(days=7)
        elif timeframe.unit == TimeFrameUnit.Month:
            end = get_current_market_time() - timedelta(days=30)
            
    # Create the request
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
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
    plot_bar_count = max(bars_back, default_bars_back(unit, bar_size))
    bars_df = pd.read_json(
        await get_alpaca_bars(
            symbol=symbol,
            unit=unit,
            bar_size=bar_size,
            indicators=indicators,
            bars_back=plot_bar_count,
            truncate_bars=False,
        ),
        lines=True,
        orient="records",
    )

    bars_df["datetime"] = pd.to_datetime(
        bars_df["datetime"], format="%Y-%m-%d %H:%M:%S"
    )
    bars_df.set_index("datetime", inplace=True)
    total_time_span = (bars_df.index[-1] - bars_df.iloc[-plot_bar_count:].index[0]).total_seconds() / 60 / 60
    time_span_str = f"{int(math.ceil(total_time_span))} hours"
    if unit == "Daily":
        time_span_str = f"{int(math.ceil(total_time_span / 24))} days"
    elif unit == "Weekly":
        time_span_str = f"{int(math.ceil(total_time_span / 24 / 7))} weeks"
    elif unit == "Monthly":
        time_span_str = f"{int(math.ceil(total_time_span / 24 / 30))} months"

    # Generate the plot
    buf = plot_bars(
        bars_df.iloc[-plot_bar_count:],
        f"{symbol}\nbar size: {bar_size}\nbar unit: {unit}\ntotal time span: {time_span_str}",
    )

    bars_df.reset_index(inplace=True)
    bars_df["datetime"] = bars_df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Return both the image and the data
    return (
        Image(data=buf.read(), format="png"),
        bars_df.iloc[-(bars_back or plot_bar_count):]
        .to_json(orient="records", lines=True),
    )
