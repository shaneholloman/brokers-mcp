import base64
import io
import json

import pandas as pd
import pandas_ta
from matplotlib import pyplot as plt
from mcp import Tool
from mcp.types import TextContent, ImageContent
import mplfinance as mpf

from .api import tradestation
from ..common import BrokerTools

tradestation_tools_prefix = "charts_and_prices"

SUPPORTED_INDICATORS = [
    "sma_{period}",
    "ema_{period}",
    "rsi_{window_period}",
    "macd_{fast_period}_{slow_period}_{signal_period}",
    "vwap"
]

get_bars_input_schema = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "unit": {
            "type": "string",
            "description":"Unit of time for the bars. Possible values are Minute, Daily, Weekly, Monthly."
        },
        "interval": {
            "type": "number",
            "description":"Interval that each bar will consist of - for minute bars,"
                          " the number of minutes aggregated in a single bar. For bar units other than minute,"
                          " value must be 1. For unit Minute the max allowed Interval is 1440."
        },
        "bars_back": {
            "type": "number",
            "description":"Number of bars back to fetch (or retrieve)."
                          " The maximum number of intraday bars back that a user can query is 57,600."
                          " There is no limit on daily, weekly, or monthly bars."
                          " This parameter is mutually exclusive with firstdate",
        },
        "firstdate": {
            "type": "string",
            "description":"Does not have a default value."
                          " The first date formatted as YYYY-MM-DD OR YYYY-MM-DDTHH:mm:SSZ."
                          " This parameter is mutually exclusive with barsback."
        },
        "lastdate": {
            "type": "string",
            "description":"Defaults to current timestamp. The last date formatted as YYYY-MM-DD,2020-04-20T18:00:00Z"
        },
        "extended_hours": {
            "type": "boolean",
            "description":"Defaults to False. If True, includes extended hours data.",
            "default": False
        }
    },
    "required": ["symbol", "interval", "unit"],
}

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

async def call_tool(name: str, arguments: dict):
    if name == f"{tradestation_tools_prefix}_get_bars":
        bars_df = await tradestation.get_bars(
            symbol=arguments["symbol"],
            unit=arguments["unit"],
            interval=arguments["interval"],
            barsback=arguments.get("bars_back"),
            firstdate=arguments.get("firstdate"),
            lastdate=arguments.get("lastdate"),
            extended_hours=arguments.get("extended_hours", False),
        )
        return [
            TextContent(
                type="text",
                text=str(bars_df),
            )
        ]
    elif name == f"{tradestation_tools_prefix}_plot_bars":
        bars_df = await tradestation.get_bars(
            symbol=arguments["symbol"],
            unit=arguments["unit"],
            interval=arguments["interval"],
            barsback=arguments.get("bars_back"),
            firstdate=arguments.get("firstdate"),
            lastdate=arguments.get("lastdate"),
            extended_hours=arguments.get("extended_hours", False),
        )
        indicators = arguments.get("indicators", "")
        bars_df.set_index("datetime", inplace=True)
        if indicators:
            indicators = indicators.split(',')
            add_indicators_to_bars_df(bars_df, indicators)
        buf = plot_bars(bars_df)
        return [
            ImageContent(
                type="image",
                data=base64.b64encode(buf.read()).decode("utf-8"),
                mimeType="image/png"
            ),
            TextContent(
                type="text",
                text=str(bars_df),
            )
        ]
    else:
        raise ValueError(f"Unknown tool name: {name}")

tools = BrokerTools(
    name_prefix=tradestation_tools_prefix,
    tools = [
        Tool(
            name=f"{tradestation_tools_prefix}_get_bars",
            description="Get market data as ohlc bars for a symbol",
            inputSchema=get_bars_input_schema
        ),
        Tool(
            name=f"{tradestation_tools_prefix}_plot_bars",
            description="Plot a candlestick chart with indicators (or no indicators)",
            inputSchema={
                "type": "object",
                "properties": {
                    **get_bars_input_schema["properties"],
                    "indicators": {
                        "type": "string",
                        "description": "Optional, A list of indicators to plot on the chart separated by ','. Supported indicators are: " + ','.join(SUPPORTED_INDICATORS),
                    }
                },
                "required": ["symbol", "interval", "unit"]
            }
        )
    ],
    handler=call_tool
)