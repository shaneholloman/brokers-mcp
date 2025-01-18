from datetime import datetime
import io
import logging
from typing import Optional
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import mplfinance as mpf
from mcp.server.fastmcp import Image
import pandas_ta
import os

# Initialize Alpaca client
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

SUPPORTED_INDICATORS = [
    "sma_{period}",
    "ema_{period}",
    "rsi_{window_period}",
    "macd_{fast_period}_{slow_period}_{signal_period}",
    "vwap",
    "bbands_{window_period}_{num_std}",
]

logger = logging.getLogger(__name__)

def get_timeframe(unit: str, bar_size: int) -> TimeFrame:
    """Convert unit and bar_size to Alpaca TimeFrame"""
    if unit == "Minute":
        if bar_size == 1:
            return TimeFrame.Minute
        elif bar_size == 5:
            return TimeFrame.Min5
        elif bar_size == 15:
            return TimeFrame.Min15
        elif bar_size == 30:
            return TimeFrame.Min30
        elif bar_size == 60:
            return TimeFrame.Hour
        else:
            raise ValueError(f"Unsupported minute bar size: {bar_size}")
    elif unit == "Daily":
        return TimeFrame.Day
    elif unit == "Weekly": 
        return TimeFrame.Week
    elif unit == "Monthly":
        return TimeFrame.Month
    else:
        raise ValueError(f"Unsupported unit: {unit}")

def default_bars_back(unit: str, bar_size: int) -> int:
    if unit == "Minute":
        return 1170 // bar_size # 3 days
    elif unit == "Daily":
        return 30 // bar_size # 30 days
    elif unit == "Weekly":
        return 52 // bar_size # 52 weeks
    elif unit == "Monthly":
        return 24 // bar_size # 24 months
    else:
        raise ValueError(f"Unknown unit: {unit}")

# Reuse your existing indicator functions
def indicator_min_bars_back(indicator: str) -> int:
    """Return the minimum number of bars back required for an indicator"""
    if indicator.startswith("sma_"):
        return int(indicator.split("_")[1])
    elif indicator.startswith("ema_"):
        return int(indicator.split("_")[1])
    elif indicator.startswith("rsi_"):
        return int(indicator.split("_")[1])
    elif indicator.startswith("macd_"):
        return max(int(indicator.split("_")[1]), int(indicator.split("_")[2]), int(indicator.split("_")[3]))
    elif indicator.startswith("vwap"):
        return 1
    elif indicator.startswith("bbands_"):
        return int(indicator.split("_")[1])
    return 1

# Reuse your existing add_indicators function
def add_indicators_to_bars_df(bars: pd.DataFrame, indicators: list[str]):
    """Add technical indicators to the bars dataframe"""
    for indicator in indicators:
        if indicator.startswith("sma_"):
            period = int(indicator.split("_")[1])
            try:
                bars[f"sma_{period}"] = bars["close"].rolling(period).mean()
            except Exception as e:
                logger.debug(f"Error calculating SMA {period}: {e}")
        elif indicator.startswith("ema_"):
            period = int(indicator.split("_")[1])
            try:
                bars[f"ema_{period}"] = bars["close"].ewm(span=period).mean()
            except Exception as e:
                logger.debug(f"Error calculating EMA {period}: {e}")
        elif indicator.startswith("rsi_"):
            window_period = int(indicator.split("_")[1])
            try:
                bars[f"rsi_{window_period}"] = pandas_ta.rsi(bars["close"], window_period)
            except Exception as e:
                logger.debug(f"Error calculating RSI {window_period}: {e}")
        elif indicator.startswith("macd_"):
            fast_period, slow_period, signal_period = map(int, indicator.split("_")[1:])
            try:
                macd = pandas_ta.macd(bars["close"], fast_period, slow_period, signal_period)
                bars[f"macd_{fast_period}_{slow_period}_{signal_period}"] = macd.iloc[:, 0]
                bars[f"macd_signal_{fast_period}_{slow_period}_{signal_period}"] = macd.iloc[:, 2]
                bars[f"macd_histogram_{fast_period}_{slow_period}_{signal_period}"] = macd.iloc[:, 1]
            except Exception as e:
                logger.debug(f"Error calculating MACD {fast_period}_{slow_period}_{signal_period}: {e}")
        elif indicator == "vwap":
            try:
                bars["vwap"] = pandas_ta.vwap(bars["high"], bars["low"], bars["close"], bars["volume"])
            except Exception as e:
                logger.debug(f"Error calculating VWAP: {e}")
        elif indicator.startswith("bbands_"):
            window_period, num_std = map(int, indicator.split("_")[1:])
            try:
                bbands = pandas_ta.bbands(bars["close"], window_period, num_std)
                bars[f"bbands_{window_period}_{num_std}_upper"] = bbands.iloc[:, 0]
                bars[f"bbands_{window_period}_{num_std}_mid"] = bbands.iloc[:, 1]
                bars[f"bbands_{window_period}_{num_std}_lower"] = bbands.iloc[:, 2]
            except Exception as e:
                logger.debug(f"Error calculating BBands {window_period}_{num_std}: {e}")
        else:
            raise ValueError(f"Unknown indicator: {indicator}")

# Reuse your existing plot_bars function
plot_bars = your_existing_plot_bars_function  # Copy from tradestation/tools.py

async def get_alpaca_bars(
    symbol: str,
    unit: str,
    bars_back: Optional[int] = None,
    bar_size: int = 1,
    indicators: Optional[str] = None,
    extended_hours: bool = False
) -> str:
    """Get historical bars data from Alpaca"""
    timeframe = get_timeframe(unit, bar_size)
    
    if indicators:
        min_bars_back = max(indicator_min_bars_back(i) for i in indicators.split(','))
        if bars_back is not None:
            bars_back = min_bars_back + bars_back
    
    if bars_back is None:
        bars_back = default_bars_back(unit, bar_size)

    # Create the request
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        limit=bars_back,
        adjustment='all',
        feed='sip' if extended_hours else 'iex'
    )

    # Get the bars
    bars_response = stock_client.get_stock_bars(request)
    
    # Convert to DataFrame
    bars_df = bars_response.df
    if isinstance(bars_df.index, pd.MultiIndex):
        bars_df = bars_df.xs(symbol)
    
    # Add indicators if requested
    if indicators:
        indicator_list = [i.strip() for i in indicators.split(',')]
        add_indicators_to_bars_df(bars_df, indicator_list)
    
    # Format datetime
    bars_df = bars_df.reset_index()
    bars_df["timestamp"] = bars_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    bars_df = bars_df.rename(columns={"timestamp": "datetime"})
    
    return bars_df.to_json(orient="records", lines=True)

async def plot_alpaca_bars_with_indicators(
    symbol: str,
    unit: str,
    bar_size: int,
    indicators: str = "",
    bars_back: Optional[int] = None,
    extended_hours: bool = False
) -> tuple[Image, str]:
    """Plot bars with indicators using Alpaca data"""
    bars_back_requested = bars_back if bars_back else default_bars_back(unit, bar_size)
    
    # Get the bars data
    bars_df = pd.read_json(
        await get_alpaca_bars(
            symbol=symbol,
            unit=unit,
            bar_size=bar_size,
            indicators=indicators,
            bars_back=bars_back_requested,
            extended_hours=extended_hours,
        ),
        lines=True,
        orient="records"
    )
    
    bars_df["datetime"] = pd.to_datetime(bars_df["datetime"], format="%Y-%m-%d %H:%M:%S")
    bars_df.set_index("datetime", inplace=True)
    
    # Generate the plot
    buf = plot_bars(bars_df)
    
    bars_df.reset_index(inplace=True)
    bars_df["datetime"] = bars_df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # Return both the image and the data
    return (
        Image(data=buf.read(), format="png"),
        bars_df.iloc[-100:].to_json(orient="records", lines=True)
    ) 