import asyncio
import base64
import io
from logging import getLogger

import pandas as pd
import pandas_ta
from ib_insync import util, Stock, Option, Contract
from matplotlib import pyplot as plt
from mcp import Tool
import mplfinance as mpf
from mcp.types import TextContent, ImageContent

# from src.portfolio_service.brokers.ibkr.client import ib
# from src.portfolio_service.brokers.ibkr.common import ibkr_tool_prefix
# from src.portfolio_service.brokers.ibkr.global_state import qualify_contracts

from ..client import ib
from ..common import ibkr_tool_prefix
from ..global_state import qualify_contracts, get_contract

SUPPORTED_INDICATORS_5min = [
    "sma_{period}",
    "ema_{period}",
    "rsi_{window_period}",
    "macd_{fast_period}_{slow_period}_{signal_period}",
    "vwap"
]

SUPPORTED_INDICATORS_DAILY = list(set(SUPPORTED_INDICATORS_5min) - {"vwap"})

# region Tools
tools = [
    Tool(
        name=f"{ibkr_tool_prefix}_get_bars",
        description="Get market data as ohlc volume bars for a stock or index. set the use_rth flag to False to include pre and post market data",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The symbol of the stock (or the underlying) to get bars for"},
                "type": {
                    "type": "string",
                    "description": "The type of the symbol, either 'stock' or 'index'. Default is 'stock'",
                    "enum": ["stock", "index"],
                    "default": "stock"
                },
                "duration": {
                    "type": "string",
                    "description": "Time span of all the bars. Examples: ‘60 S’, ‘30 D’, ‘13 W’, ‘6 M’, ‘10 Y’"
                },
                "bar_size": {
                    "type": "string",
                    "description": "Time period of one bar. Must be one of: ‘1 secs’,"
                                   " ‘5 secs’, ‘10 secs’ 15 secs’, ‘30 secs’, ‘1 min’,"
                                   " ‘2 mins’, ‘3 mins’, ‘5 mins’, ‘10 mins’, ‘15 mins’,"
                                   " ‘20 mins’, ‘30 mins’, ‘1 hour’, ‘2 hours’, ‘3 hours’,"
                                   " ‘4 hours’, ‘8 hours’, ‘1 day’, ‘1 week’, ‘1 month’."
                },
                "end_datetime": {
                    "type": "string",
                    "description": "The end date and time of the bars, leave empty for update-to-date bars."
                                   " Format: 'yyyyMMdd HH:mm:ss'. Assumed to be in the New York timezone."
                },
                "use_rth": {
                    "type": "boolean",
                    "description": "Whether to use regular trading hours only. Default is True",
                    "default": True
                }
            },
            "required": ["symbol", "duration", "bar_size"],
        },
    ),
    Tool(
        name=f"{ibkr_tool_prefix}_5_minute_candlestick_chart",
        description="Plot a candlestick chart for a stock or index using 5 minute bars dating 3 days back from the current date",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The symbol of the stock (or the underlying) to get bars for"},
                "type": {
                    "type": "string",
                    "description": "The type of the symbol, either 'stock' or 'index'. Default is 'stock'",
                    "enum": ["stock", "index"],
                    "default": "stock"
                },
                "indicators": {
                    "type": "string",
                    "description": "A list of indicators to plot on the chart separated by ','. Supported indicators are: " + ','.join(SUPPORTED_INDICATORS_5min),
                }
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name=f"{ibkr_tool_prefix}_1_minute_candlestick_chart",
        description="Plot a candlestick chart for a stock or index using 1 minute bars dating 1 day back from the current date",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The symbol of the stock (or the underlying) to get bars for"},
                "type": {
                    "type": "string",
                    "description": "The type of the symbol, either 'stock' or 'index'. Default is 'stock'",
                    "enum": ["stock", "index"],
                    "default": "stock"
                },
                "indicators": {
                    "type": "string",
                    "description": "A list of indicators to plot on the chart separated by ','. Supported indicators are: " + ','.join(SUPPORTED_INDICATORS_5min),
                }
            },
        }
    ),
    Tool(
        name=f"{ibkr_tool_prefix}_daily_candlestick_chart",
        description="Plot a candlestick chart for a stock or index using daily bars dating 1 year back 3 months back from the current date",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The symbol of the stock (or the underlying) to get bars for"},
                "type": {
                    "type": "string",
                    "description": "The type of the symbol, either 'stock' or 'index'. Default is 'stock'",
                    "enum": ["stock", "index"],
                    "default": "stock"
                },
                "period": {
                    "type": "string",
                    "description": "The period of the bars. Must be one of: '1 Y', ''3 M', default is '3 M'"
                },
                "indicators": {
                    "type": "string",
                    "description": "A list of indicators to plot on the chart separated by ','. Supported indicators are: " + ','.join(SUPPORTED_INDICATORS_DAILY),
                }
            },
            "required": ["symbol"],
        }
    )
]
# endregion

def add_indicators_to_bars_df(bars: pd.DataFrame, indicators: list[str]):
    for indicator in indicators:
        if indicator.startswith("sma_"):
            period = int(indicator.split("_")[1])
            bars[f"sma_{period}"] = bars["close"].rolling(period).mean()
        elif indicator.startswith("ema_"):
            period = int(indicator.split("_")[1])
            bars[f"ema_{period}"] = bars["close"].ewm(span=period).mean()
        elif indicator.startswith("rsi_"):
            window_period = int(indicator.split("_")[1])
            bars[f"rsi_{window_period}"] = pandas_ta.rsi(bars["close"], window_period)
        elif indicator.startswith("macd_"):
            fast_period, slow_period, signal_period = map(int, indicator.split("_")[1:])
            macd = pandas_ta.macd(bars["close"], fast_period, slow_period, signal_period)
            bars[f"macd_{fast_period}_{slow_period}_{signal_period}"] = macd.iloc[:, 0]
            bars[f"macd_signal_{fast_period}_{slow_period}_{signal_period}"] = macd.iloc[:, 2]
            bars[f"macd_histogram_{fast_period}_{slow_period}_{signal_period}"] = macd.iloc[:, 1]
        elif indicator == "vwap":
            bars["vwap"] = pandas_ta.vwap(bars["high"], bars["low"], bars["close"], bars["volume"])
        else:
            raise ValueError(f"Unknown indicator: {indicator}")

def plot_bars(bars: pd.DataFrame):
    """
    Plots a candlestick chart with volume, moving averages, RSI, and MACD if present in the DataFrame.

    Args:
        bars (pd.DataFrame): DataFrame containing OHLCV data with required columns:
                             ['open', 'high', 'low', 'close', 'volume'] and a datetime index.
    """
    # Ensure the DataFrame index is a datetime index for mplfinance
    if not isinstance(bars.index, pd.DatetimeIndex):
        bars = bars.set_index(pd.to_datetime(bars.index))

    # Prepare additional plots
    add_plots = []
    panel_num = 2  # Start from panel 2 (0 is main plot, 1 is volume by default)
    panel_ratios = [3, 1]  # Ratios for the main plot and volume

    # Moving Averages on main chart (panel 0)
    ma_columns = [col for col in bars.columns if col.startswith('sma_') or col.startswith('ema_')]
    if ma_columns:
        # Assign different colors for moving averages
        ma_colors = ['blue', 'orange', 'green', 'red', 'purple']
        for i, ma_col in enumerate(ma_columns):
            color = ma_colors[i % len(ma_colors)]
            add_plots.append(mpf.make_addplot(
                bars[ma_col],
                type='line',
                linestyle='solid',
                width=1,
                color=color,
                panel=0
            ))

    # VWAP Indicator
    if 'vwap' in bars.columns:
        add_plots.append(mpf.make_addplot(
            bars['vwap'],
            type='line',
            linestyle='solid',
            width=1,
            color='gold',
            panel=0
        ))

    # RSI Indicator
    rsi_columns = [col for col in bars.columns if col.startswith('rsi_')]
    if rsi_columns:
        for rsi_col in rsi_columns:
            add_plots.append(mpf.make_addplot(
                bars[rsi_col],
                panel=panel_num,
                color='purple',
                ylabel='RSI'
            ))
        panel_ratios.append(1)  # Adjust panel ratio for RSI
        panel_num += 1

    # MACD Indicator
    macd_base = [col for col in bars.columns if col.startswith('macd_') and not col.startswith('macd_signal_') and not col.startswith('macd_histogram_')]
    for macd_col in macd_base:
        # Extract MACD parameters from the column name (e.g., 'macd_12_26_9')
        params = macd_col.split('_')[1:]
        signal_col = f'macd_signal_' + '_'.join(params)
        histogram_col = f'macd_histogram_' + '_'.join(params)

        # Check if corresponding signal and histogram columns exist
        if signal_col in bars.columns and histogram_col in bars.columns:
            data = pd.DataFrame({
                'macd': bars[macd_col],
                'signal': bars[signal_col],
                'histogram': bars[histogram_col]
            }, index=bars.index)

            # Add MACD line
            add_plots.append(mpf.make_addplot(
                data['macd'],
                panel=panel_num,
                color='blue',
                ylabel='MACD'
            ))
            # Add MACD signal line
            add_plots.append(mpf.make_addplot(
                data['signal'],
                panel=panel_num,
                color='red'
            ))
            # Add MACD histogram
            add_plots.append(mpf.make_addplot(
                data['histogram'],
                type='bar',
                panel=panel_num,
                color='grey',
                alpha=0.5
            ))
            panel_ratios.append(1)  # Adjust panel ratio for MACD
            panel_num += 1

    fig, axes = mpf.plot(
        bars,
        type='candle',  # Candlestick chart
        style='charles',  # Chart style
        volume=True,  # Include volume subplot
        ylabel='Price',  # Y-axis label for price
        ylabel_lower='Volume',  # Y-axis label for volume
        title="Stock Prices",  # Chart title
        figsize=(12, 8),  # Figure size
        addplot=add_plots,  # Additional plots (moving averages, RSI, MACD)
        panel_ratios=panel_ratios,  # Adjust the panel ratios
        returnfig=True,  # Return the figure and axes,
        datetime_format="%Y-%m-%d %H:%M:%S"
    )
    # Save the figure to a BytesIO object
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    buf.seek(0)  # Seek to the beginning of the BytesIO buffer
    return buf


async def handler(name, arguments):
    if name == f"{ibkr_tool_prefix}_get_bars":
        contract = await get_contract(arguments["symbol"], arguments.get("type", "stock"))
        return [
            TextContent(
                type="text",
                text=str(
                    util.df(await ib.reqHistoricalDataAsync(
                        contract,
                        endDateTime=arguments.get("end_datetime", ""),
                        durationStr=arguments["duration"],
                        barSizeSetting=arguments["bar_size"],
                        useRTH=arguments.get("use_rth", True),
                        whatToShow="TRADES",
                        formatDate=1
                    ))
                )
            )
        ]
    elif name == f"{ibkr_tool_prefix}_5_minute_candlestick_chart":
        contract = await get_contract(arguments["symbol"], arguments.get("type", "stock"))
        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr="3 D",
            barSizeSetting="5 mins",
            useRTH=True,
            whatToShow="TRADES",
            formatDate=1
        )
        bars = util.df(bars)
        bars.set_index("date", inplace=True)
        indicators = arguments.get("indicators", "")
        if indicators:
            indicators = indicators.split(",")
            add_indicators_to_bars_df(bars, indicators)
        buf = plot_bars(bars)
        return [
            ImageContent(
                type="image",
                data=base64.b64encode(buf.read()).decode("utf-8"),
                mimeType="image/png"
            )
        ]
    elif name == f"{ibkr_tool_prefix}_1_minute_candlestick_chart":
        contract = await get_contract(arguments["symbol"], arguments.get("type", "stock"))
        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr="1 D",
            barSizeSetting="1 min",
            useRTH=True,
            whatToShow="TRADES",
            formatDate=1
        )
        bars = util.df(bars)
        bars.set_index("date", inplace=True)
        indicators = arguments.get("indicators", "")
        if indicators:
            indicators = indicators.split(",")
            add_indicators_to_bars_df(bars, indicators)
        buf = plot_bars(bars)
        return [
            ImageContent(
                type="image",
                data=base64.b64encode(buf.read()).decode("utf-8"),
                mimeType="image/png"
            )
        ]
    elif name == f"{ibkr_tool_prefix}_daily_candlestick_chart":
        contract = await get_contract(arguments["symbol"], arguments.get("type", "stock"))
        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=arguments.get("period", "3 M"),
            barSizeSetting="1 day",
            useRTH=True,
            whatToShow="TRADES",
            formatDate=1
        )
        bars = util.df(bars)
        bars.set_index("date", inplace=True)
        indicators = arguments.get("indicators", "")
        if indicators:
            indicators = indicators.split(",")
            add_indicators_to_bars_df(bars, indicators)
        buf = plot_bars(bars)
        return [
            ImageContent(
                type="image",
                data=base64.b64encode(buf.read()).decode("utf-8"),
                mimeType="image/png"
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    asyncio.run(handler(f"{ibkr_tool_prefix}_daily_candlestick_chart", {"symbol": "AAPL", "indicators": "vwap"}))
