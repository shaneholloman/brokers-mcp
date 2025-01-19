import matplotlib

matplotlib.use("Agg")
import io
import logging
import pandas_ta
import pandas as pd
from matplotlib import pyplot as plt
import mplfinance as mpf


logger = logging.getLogger(__name__)


def indicator_min_bars_back(indicator: str) -> int:
    """Return the minimum number of bars back required for an indicator"""
    if indicator.startswith("sma_"):
        return int(indicator.split("_")[1])
    elif indicator.startswith("ema_"):
        return int(indicator.split("_")[1])
    elif indicator.startswith("rsi_"):
        return int(indicator.split("_")[1])
    elif indicator.startswith("macd_"):
        return max(
            int(indicator.split("_")[1]),
            int(indicator.split("_")[2]),
            int(indicator.split("_")[3]),
        )
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
                bars[f"rsi_{window_period}"] = pandas_ta.rsi(
                    bars["close"], window_period
                )
            except Exception as e:
                logger.debug(f"Error calculating RSI {window_period}: {e}")
        elif indicator.startswith("macd_"):
            fast_period, slow_period, signal_period = map(int, indicator.split("_")[1:])
            try:
                macd = pandas_ta.macd(
                    bars["close"], fast_period, slow_period, signal_period
                )
                bars[f"macd_{fast_period}_{slow_period}_{signal_period}"] = macd.iloc[
                    :, 0
                ]
                bars[f"macd_signal_{fast_period}_{slow_period}_{signal_period}"] = (
                    macd.iloc[:, 2]
                )
                bars[f"macd_histogram_{fast_period}_{slow_period}_{signal_period}"] = (
                    macd.iloc[:, 1]
                )
            except Exception as e:
                logger.debug(
                    f"Error calculating MACD {fast_period}_{slow_period}_{signal_period}: {e}"
                )
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


def plot_bars(bars: pd.DataFrame):
    """
    Plots a candlestick chart with volume, moving averages, RSI, and MACD if present in the DataFrame.
    """
    # Ensure the DataFrame index is a datetime index for mplfinance
    if not isinstance(bars.index, pd.DatetimeIndex):
        bars = bars.set_index(pd.to_datetime(bars.index))

    # Prepare additional plots
    add_plots = []
    panel_num = 2  # Start from panel 2 (0 is main plot, 1 is volume by default)
    panel_ratios = [3, 1]  # Ratios for the main plot and volume

    # Moving Averages on main chart (panel 0)
    ma_columns = [
        col for col in bars.columns if col.startswith("sma_") or col.startswith("ema_")
    ]
    if ma_columns:
        # Assign different colors for moving averages
        ma_colors = ["blue", "orange", "green", "red", "purple"]
        for i, ma_col in enumerate(ma_columns):
            color = ma_colors[i % len(ma_colors)]
            add_plots.append(
                mpf.make_addplot(
                    bars[ma_col],
                    type="line",
                    linestyle="solid",
                    width=1,
                    color=color,
                    panel=0,
                )
            )

    # VWAP Indicator
    if "vwap" in bars.columns:
        add_plots.append(
            mpf.make_addplot(
                bars["vwap"],
                type="line",
                linestyle="solid",
                width=1,
                color="gold",
                panel=0,
            )
        )

    # RSI Indicator
    rsi_columns = [col for col in bars.columns if col.startswith("rsi_")]
    if rsi_columns:
        for rsi_col in rsi_columns:
            add_plots.append(
                mpf.make_addplot(
                    bars[rsi_col], panel=panel_num, color="purple", ylabel="RSI"
                )
            )
        panel_ratios.append(1)  # Adjust panel ratio for RSI
        panel_num += 1

    # MACD Indicator
    macd_base = [
        col
        for col in bars.columns
        if col.startswith("macd_")
        and not col.startswith("macd_signal_")
        and not col.startswith("macd_histogram_")
    ]
    for macd_col in macd_base:
        # Extract MACD parameters from the column name (e.g., 'macd_12_26_9')
        params = macd_col.split("_")[1:]
        signal_col = f"macd_signal_" + "_".join(params)
        histogram_col = f"macd_histogram_" + "_".join(params)

        # Check if corresponding signal and histogram columns exist
        if signal_col in bars.columns and histogram_col in bars.columns:
            data = pd.DataFrame(
                {
                    "macd": bars[macd_col],
                    "signal": bars[signal_col],
                    "histogram": bars[histogram_col],
                },
                index=bars.index,
            )

            # Add MACD line
            add_plots.append(
                mpf.make_addplot(
                    data["macd"], panel=panel_num, color="blue", ylabel="MACD"
                )
            )
            # Add MACD signal line
            add_plots.append(
                mpf.make_addplot(data["signal"], panel=panel_num, color="red")
            )
            # Add MACD histogram
            add_plots.append(
                mpf.make_addplot(
                    data["histogram"],
                    type="bar",
                    panel=panel_num,
                    color="grey",
                    alpha=0.5,
                )
            )
            panel_ratios.append(1)  # Adjust panel ratio for MACD
            panel_num += 1

    # BBands Indicator
    bbands_base = [
        col
        for col in bars.columns
        if col.startswith("bbands_") and not col.endswith("mid")
    ]
    for bbands_col in bbands_base:
        # Extract BBands parameters from the column name (e.g., 'bbands_20_2')
        params = bbands_col.split("_")[1:-1]
        mid_col = f"bbands_" + "_".join(params) + "_mid"
        if mid_col in bars.columns:
            data = pd.DataFrame(
                {
                    "upper": bars[bbands_col],
                    "mid": bars[mid_col],
                    "lower": bars[bbands_col],
                },
                index=bars.index,
            )

            # Add BBands lines
            add_plots.append(
                mpf.make_addplot(
                    data[["upper", "mid", "lower"]],
                    panel=0,
                    color="grey",
                    linestyle="dashed",
                    width=0.5,
                )
            )

    fig, axes = mpf.plot(
        bars,
        type="candle",  # Candlestick chart
        style="charles",  # Chart style
        volume=True,  # Include volume subplot
        ylabel="Price",  # Y-axis label for price
        ylabel_lower="Volume",  # Y-axis label for volume
        title="Stock Prices",  # Chart title
        figsize=(12, 8),  # Figure size
        addplot=add_plots,  # Additional plots (moving averages, RSI, MACD)
        panel_ratios=panel_ratios,  # Adjust the panel ratios
        returnfig=True,  # Return the figure and axes,
        datetime_format="%Y-%m-%d %H:%M:%S",
    )
    # Save the figure to a BytesIO object
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)  # Close the figure to free memory
    buf.seek(0)  # Seek to the beginning of the BytesIO buffer
    return buf
