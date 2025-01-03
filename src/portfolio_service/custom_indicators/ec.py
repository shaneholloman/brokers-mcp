import numpy as np
import pandas as pd
import yfinance as yf

def compute_ec_collision_entropy(corr_matrix):
    """
    Compute EC (Collision Entropy-based) for a given correlation matrix.
    Steps:
      1) Eigenvalues of the correlation matrix
      2) Normalize eigenvalues -> probability measure p_i
      3) Collision entropy H_2 = - log( sum(p_i^2) )
      4) EC = 1 / (1 + H_2)
    """
    eigvals, _ = np.linalg.eigh(corr_matrix)
    # clip negative values (possible small numerical errors) to zero
    eigvals = np.clip(eigvals, a_min=0, a_max=None)
    total = np.sum(eigvals)
    if total <= 0:
        return np.nan
    p = eigvals / total
    sum_p_sq = np.sum(p**2)
    if sum_p_sq <= 0:
        return np.nan
    H2 = -np.log(sum_p_sq)
    EC = 1.0 / (1.0 + H2)
    return EC

def main():
    # 1) Define your tickers for the S&P 500 sectors (excluding Real Estate) + SPY
    tickers = [
        "XLC",  # Communication Services
        "XLY",  # Consumer Discretionary
        "XLP",  # Consumer Staples
        "XLE",  # Energy
        "XLF",  # Financials
        "XLV",  # Healthcare
        "XLI",  # Industrials
        "XLB",  # Materials
        "XLK",  # Technology
        "XLU",  # Utilities
        "SPY"   # S&P 500 ETF
    ]

    # 2) Define the date range for 2024
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    # 3) Fetch daily data for the entire 2024 range
    data = yf.download(tickers, start=start_date, end=end_date, progress=False)["Close"]

    # 4) Compute daily log returns
    log_returns = np.log(data).diff().dropna()

    # 5) We will compute the monthly EC for each calendar month in 2024.
    #    Let's create a range of monthly periods from Jan 2024 to Dec 2024.
    months_2024 = pd.period_range(start="2024-01", end="2024-12", freq="M")

    # Prepare a dict or list to store results
    ec_results = {}

    for month_period in months_2024:
        # Convert Period to start/end timestamps for the given month
        month_start = month_period.asfreq("D", how="start")
        month_end = month_period.asfreq("D", how="end")

        # Slice the log_returns DataFrame for just this month
        # We do [month_start:month_end] to get all rows in that date range
        this_month_data = log_returns.loc[str(month_start) : str(month_end)]

        # If there are no rows (e.g., the market was closed or data not available),
        # skip computation
        if this_month_data.empty:
            ec_results[str(month_period)] = np.nan
            continue

        # Standardize
        this_month_std = (this_month_data - this_month_data.mean()) / this_month_data.std()

        # Correlation matrix
        corr_matrix = this_month_std.corr()

        # Compute EC
        ec_value = compute_ec_collision_entropy(corr_matrix)

        # Store
        ec_results[str(month_period)] = ec_value

    # Convert results to a Series (or DataFrame if you want more columns)
    ec_series = pd.Series(ec_results, name="EC_value")

    print("Monthly EC values for 2024:")
    print(ec_series)

if __name__ == "__main__":
    main()