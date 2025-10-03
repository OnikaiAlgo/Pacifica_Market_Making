import argparse
import pandas as pd
import numpy as np
import sys
import os
import json
from datetime import datetime
import asyncio
from numba import jit, njit
from api_client import ApiClient


@jit(nopython=True)
def _calculate_performance_numba(entry_prices, exit_prices, signals, trading_fee):
    """
    Calculates performance metrics using Numba for speed.
    Assumes inputs are clean NumPy arrays.
    """
    # Calculate logarithmic returns for each trade
    log_returns = np.log(exit_prices / entry_prices)

    # Adjust for short positions (where the signal was -1)
    # Numba supports this kind of advanced indexing
    log_returns[signals == -1] *= -1

    # Apply trading fee
    log_returns -= trading_fee

    # Calculate Metrics
    num_flips = len(log_returns)

    std_dev = np.std(log_returns)
    if std_dev == 0.0 or np.isnan(std_dev):
        sharpe_ratio = 0.0
    else:
        sharpe_ratio = np.mean(log_returns) / std_dev

    cumulative_return = np.exp(np.sum(log_returns)) - 1

    return num_flips, sharpe_ratio, cumulative_return


@njit(cache=True)
def _supertrend_direction_numba(high, low, close, period, multiplier):
    n = close.shape[0]
    if n <= period:
        return np.zeros(n, dtype=np.int8), -1

    tr = np.empty(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        high_low = high[i] - low[i]
        high_close = abs(high[i] - close[i - 1])
        low_close = abs(low[i] - close[i - 1])
        tr[i] = max(high_low, high_close, low_close)

    atr = np.empty(n, dtype=np.float64)
    for i in range(period - 1):
        atr[i] = 0.0

    rolling_sum = 0.0
    for i in range(period):
        rolling_sum += tr[i]
    atr[period - 1] = rolling_sum / period

    factor = period - 1
    for i in range(period, n):
        atr[i] = (atr[i - 1] * factor + tr[i]) / period

    hl2 = (high + low) * 0.5
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    final_upper = np.empty(n, dtype=np.float64)
    final_lower = np.empty(n, dtype=np.float64)
    direction = np.zeros(n, dtype=np.int8)

    start = period - 1
    final_upper[start] = upper[start]
    final_lower[start] = lower[start]
    direction[start] = 1

    for i in range(start + 1, n):
        prev_upper = final_upper[i - 1]
        prev_lower = final_lower[i - 1]

        if upper[i] < prev_upper or close[i - 1] > prev_upper:
            final_upper[i] = upper[i]
        else:
            final_upper[i] = prev_upper

        if lower[i] > prev_lower or close[i - 1] < prev_lower:
            final_lower[i] = lower[i]
        else:
            final_lower[i] = prev_lower

        if close[i] > final_upper[i - 1]:
            direction[i] = 1
        elif close[i] < final_lower[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]

        if direction[i] == 1 and final_lower[i] < prev_lower:
            final_lower[i] = prev_lower
        elif direction[i] == -1 and final_upper[i] > prev_upper:
            final_upper[i] = prev_upper

    return direction, start


@njit(cache=True)
def _run_backtest_numba(open_prices, high, low, close, period, multiplier, trading_fee):
    n = close.shape[0]
    if n <= period + 1:
        return 0, 0.0, 0.0, 0, False

    direction, start = _supertrend_direction_numba(high, low, close, period, multiplier)
    if start == -1:
        return 0, 0.0, 0.0, 0, False

    max_trades = n
    entry_prices = np.empty(max_trades, dtype=np.float64)
    exit_prices = np.empty(max_trades, dtype=np.float64)
    signals = np.empty(max_trades, dtype=np.int8)

    trade_count = 0
    previous_signal = direction[start]
    if previous_signal == 0:
        for idx in range(start + 1, n):
            if direction[idx] != 0:
                previous_signal = direction[idx]
                break
        if previous_signal == 0:
            return 0, 0.0, 0.0, 0, False

    for i in range(start + 1, n - 1):
        current_signal = direction[i]
        if current_signal == 0 or current_signal == previous_signal:
            continue

        entry_prices[trade_count] = open_prices[i + 1]
        signals[trade_count] = current_signal

        if trade_count > 0:
            exit_prices[trade_count - 1] = entry_prices[trade_count]

        trade_count += 1
        previous_signal = current_signal

    if trade_count < 2:
        return 0, 0.0, 0.0, int(direction[n - 1]), False

    exit_prices[trade_count - 1] = close[n - 1]

    entry_prices = entry_prices[:trade_count]
    exit_prices = exit_prices[:trade_count]
    signals = signals[:trade_count]

    num_flips, sharpe_ratio, cumulative_return = _calculate_performance_numba(
        entry_prices, exit_prices, signals, trading_fee
    )

    return num_flips, sharpe_ratio, cumulative_return, int(direction[n - 1]), True


def run_backtest(price_data, atr_period, atr_multiplier, trading_fee=0.0010):
    """
    Runs a simple stop-and-reverse backtest on the Supertrend strategy.
    Expects pre-cached NumPy arrays in price_data to avoid per-iteration DataFrame work.
    """
    open_prices = price_data['open']
    high = price_data['high']
    low = price_data['low']
    close = price_data['close']

    if open_prices.shape[0] < atr_period + 2:
        return None

    num_flips, sharpe_ratio, cumulative_return, last_signal, is_valid = _run_backtest_numba(
        open_prices, high, low, close, atr_period, atr_multiplier, trading_fee
    )

    if not is_valid:
        return None

    return {
        'period': atr_period,
        'multiplier': atr_multiplier,
        'flips': num_flips,
        'sharpe': sharpe_ratio,
        'return': cumulative_return,
        'last_signal': last_signal
    }


async def fetch_klines_data(symbol, interval, limit, total_candles, kline_cache_file):
    """
    Loads kline data from cache file.
    Note: Klines should be generated separately using generate_klines.py
    """
    all_klines = []

    # Load cached data if exists
    if os.path.exists(kline_cache_file):
        print(f"Loading cached k-lines from {kline_cache_file}...")
        df_cache = pd.read_csv(kline_cache_file)
        all_klines = df_cache.values.tolist()
        print(f"Loaded {len(all_klines)} klines from cache")

        if len(all_klines) >= total_candles:
            print(f"✓ Sufficient klines available ({len(all_klines)}/{total_candles})")
            return all_klines
        else:
            print(f"⚠️  Only {len(all_klines)}/{total_candles} klines available. Need more historical data.")
            print(f"   Tip: Let data_collector run longer to collect more trades")
            return all_klines
    else:
        print(f"⚠️  No kline cache found: {kline_cache_file}")
        print(f"   Run generate_klines.py first to create klines from collected trades")
        return []


def perform_grid_search(symbol, interval):
    """
    Performs a grid search to find the best Supertrend parameters.
    """
    # --- Parameter Grid ---
    # ATR Periods: From 100 to 1000, in steps of 20
    atr_periods = range(100, 1001, 20)
    # ATR Multipliers: From 1.8 to roughly 8.1, in steps of 0.3
    atr_multipliers = np.arange(1.8, 8.4, 0.3)

    # --- Fetch Data ---
    limit = 500  # Pacifica default limit
    total_candles = 10000

    # --- Caching Logic ---
    os.makedirs('PACIFICA_data', exist_ok=True)
    kline_cache_file = f"PACIFICA_data/klines_{symbol}_{interval}.csv"

    # Fetch klines asynchronously
    all_klines = asyncio.run(fetch_klines_data(symbol, interval, limit, total_candles, kline_cache_file))

    if not all_klines:
        print("Failed to fetch k-line data.")
        return

    # --- Process and Save Final Dataset ---
    # Detect format: generate_klines.py produces 7 columns, API would produce 12
    if len(all_klines[0]) == 7:
        # Format from generate_klines.py: timestamp, open, high, low, close, volume, trades_count
        df = pd.DataFrame(all_klines, columns=['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Number of Trades'])
    else:
        # Original API format (12 columns)
        df = pd.DataFrame(all_klines, columns=['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time',
                                               'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume',
                                               'Taker Buy Quote Asset Volume', 'Ignore'])
    df.drop_duplicates(subset=['Open Time'], keep='last', inplace=True)
    df = df.tail(total_candles)
    df.to_csv(kline_cache_file, index=False)

    klines = df.values.tolist()
    print(f"Saved {len(klines)} k-lines to cache.")

    # Use the same format detection as before
    if len(klines[0]) == 7:
        # Format from generate_klines.py
        df = pd.DataFrame(klines, columns=['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Number of Trades'])
    else:
        # Original API format (12 columns)
        df = pd.DataFrame(klines, columns=['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time',
                                           'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume',
                                           'Taker Buy Quote Asset Volume', 'Ignore'])
    df['Open Time'] = pd.to_numeric(df['Open Time'])
    df = df.astype({'Open': 'float', 'High': 'float', 'Low': 'float', 'Close': 'float', 'Volume': 'float'})

    price_data = {
        'open': np.ascontiguousarray(df['Open'].to_numpy(dtype=np.float64)),
        'high': np.ascontiguousarray(df['High'].to_numpy(dtype=np.float64)),
        'low': np.ascontiguousarray(df['Low'].to_numpy(dtype=np.float64)),
        'close': np.ascontiguousarray(df['Close'].to_numpy(dtype=np.float64)),
    }

    # --- Data Continuity Check ---
    print("Verifying data continuity...")
    # Convert interval string to milliseconds
    interval_map = {'m': 60000, 'h': 3600000, 'd': 86400000}
    interval_unit = interval[-1]
    interval_value = int(interval[:-1])
    expected_interval_ms = interval_value * interval_map[interval_unit]

    time_diffs = df['Open Time'].diff().dropna()
    gaps = time_diffs[time_diffs > expected_interval_ms]

    if not gaps.empty:
        print(f"Warning: Found {len(gaps)} gaps in the data. The largest gap is {gaps.max() / expected_interval_ms:.1f} candles.")
    else:
        print("Data continuity verified. No gaps found.")

    print(f"Using {len(klines)} candles for backtest.")
    print("Running backtest grid search...")
    results = []
    total_tests = len(atr_periods) * len(atr_multipliers)
    test_count = 0

    for period in atr_periods:
        for multiplier in atr_multipliers:
            test_count += 1
            progress = (test_count / total_tests) * 100
            sys.stdout.write(f"\rProgress: {progress:.1f}% ({test_count}/{total_tests})")
            sys.stdout.flush()

            result = run_backtest(price_data, period, multiplier)
            if result:
                results.append(result)

    print("\n\nFinding the best result based on Sharpe Ratio...")
    if not results:
        print("No valid backtest results found.")
        return

    # Sort by Sharpe Ratio to find the best individual performer and the top performers for consensus
    sorted_results = sorted(results, key=lambda x: x['sharpe'], reverse=True)

    if not sorted_results:
        print("Could not determine a best result.")
        return

    best = sorted_results[0]
    print("\n--- Best Overall Result (based on Sharpe Ratio) ---")
    print(f"Period: {best['period']}, Multiplier: {best['multiplier']:.1f}, Flips: {best['flips']}, Sharpe: {best['sharpe']:.4f}, Return: {best['return']:.2%}")

    # --- Determine Consensus Trend from Top 5% ---
    top_count = max(1, int(len(sorted_results) * 0.05))
    print(f"\nDetermining consensus trend from top {top_count} results (~5% of grid)...")
    top_slice = sorted_results[:top_count]

    consensus_signals = [params['last_signal'] for params in top_slice if params['last_signal'] != 0]

    if not consensus_signals:
        print("Could not determine a consensus signal. Defaulting to +1.")
        consensus_trend = 1
    else:
        signal_sum = sum(consensus_signals)
        if signal_sum >= 0:  # Default to +1 on a 50/50 split
            consensus_trend = 1
        else:
            consensus_trend = -1
        print(f"Consensus signal sum: {signal_sum} -> Final Trend: {consensus_trend} ({consensus_signals.count(1)} UP vs {consensus_signals.count(-1)} DOWN)")

    # --- Save Best Parameters and Current Trend ---
    print("\nSaving best parameters and consensus trend to JSON file...")

    last_candle_timestamp = pd.to_datetime(klines[-1][0], unit='ms').isoformat()

    output_data = {
        'best_parameters': {
            'atr_period': best['period'],
            'atr_multiplier': best['multiplier']
        },
        'backtest_performance': {
            'sharpe_ratio': best['sharpe'],
            'cumulative_return_pct': best['return'] * 100,
            'trades': best['flips']
        },
        'current_signal': {
            'trend': consensus_trend,
            'interval': interval,
            'timestamp_utc': last_candle_timestamp
        }
    }

    # Ensure 'params' directory exists
    if not os.path.exists('params'):
        os.makedirs('params')

    # Create filename - symbol is already without suffix in Pacifica (e.g., "BTC" not "BTCUSDT")
    file_path = f'params/supertrend_params_{symbol}.json'
    with open(file_path, 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"Successfully saved data to {file_path}")
    print("\n--- JSON File Content ---")
    print(json.dumps(output_data, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backtest Supertrend strategy and find best parameters for Pacifica.')
    parser.add_argument('--symbol', type=str, default='BTC',
                        help='The trading symbol to backtest (e.g., BTC, ETH, SOL). Defaults to BTC.')
    parser.add_argument('--interval', type=str, default='1m',
                        help='The k-line interval (e.g., 1m, 5m, 1h, 1d). Defaults to 1m.')
    args = parser.parse_args()

    perform_grid_search(args.symbol, args.interval)