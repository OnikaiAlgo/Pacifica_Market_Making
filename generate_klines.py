#!/usr/bin/env python3
"""
Script to generate kline/candlestick data from trades CSV and subscribe to real-time candles.

This script:
1. Reads historical trades from CSV files
2. Generates OHLCV klines for specified intervals
3. Connects to Pacifica WebSocket to receive new candles in real-time
4. Maintains a continuous kline history in cache
"""

import pandas as pd
import numpy as np
import os
import json
import asyncio
import websockets
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import argparse


def generate_klines_from_trades(trades_df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """
    Generate OHLCV klines from trades data.

    Args:
        trades_df: DataFrame with columns [unix_timestamp_ms, price, quantity]
        interval: Kline interval (e.g., '1m', '5m', '1h')

    Returns:
        DataFrame with kline data [timestamp, open, high, low, close, volume, trades_count]
    """
    if trades_df.empty:
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trades_count'])

    # Convert interval to pandas frequency
    interval_map = {
        '1m': '1T', '3m': '3T', '5m': '5T', '15m': '15T', '30m': '30T',
        '1h': '1H', '2h': '2H', '4h': '4H', '8h': '8H', '12h': '12H',
        '1d': '1D'
    }

    if interval not in interval_map:
        raise ValueError(f"Unsupported interval: {interval}. Supported: {list(interval_map.keys())}")

    freq = interval_map[interval]

    # Ensure timestamp is datetime
    trades_df['timestamp'] = pd.to_datetime(trades_df['unix_timestamp_ms'], unit='ms')
    trades_df = trades_df.sort_values('timestamp')

    # Set timestamp as index for resampling
    trades_df = trades_df.set_index('timestamp')

    # Resample to create klines
    klines = pd.DataFrame()
    klines['open'] = trades_df['price'].resample(freq).first()
    klines['high'] = trades_df['price'].resample(freq).max()
    klines['low'] = trades_df['price'].resample(freq).min()
    klines['close'] = trades_df['price'].resample(freq).last()
    klines['volume'] = trades_df['quantity'].resample(freq).sum()
    klines['trades_count'] = trades_df['price'].resample(freq).count()

    # Forward fill missing OHLC values (for periods with no trades)
    klines['open'] = klines['open'].fillna(method='ffill')
    klines['high'] = klines['high'].fillna(klines['close'])
    klines['low'] = klines['low'].fillna(klines['close'])
    klines['close'] = klines['close'].fillna(method='ffill')
    klines['volume'] = klines['volume'].fillna(0)
    klines['trades_count'] = klines['trades_count'].fillna(0)

    # Reset index to get timestamp as column
    klines = klines.reset_index()
    klines['timestamp'] = klines['timestamp'].astype(np.int64) // 10**6  # Convert to milliseconds

    # Drop rows where all OHLC are NaN (shouldn't happen after ffill)
    klines = klines.dropna(subset=['open', 'high', 'low', 'close'])

    return klines[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trades_count']]


async def subscribe_to_candles(symbol: str, interval: str, kline_cache_file: str, stop_event: asyncio.Event):
    """
    Subscribe to Pacifica WebSocket candle stream and update cache with new candles.

    Args:
        symbol: Trading symbol (e.g., 'BNB')
        interval: Kline interval (e.g., '5m')
        kline_cache_file: Path to kline cache CSV file
        stop_event: Event to signal when to stop
    """
    ws_url = "wss://ws.pacifica.fi/ws"

    print(f"Connecting to Pacifica WebSocket for {symbol} {interval} candles...")

    while not stop_event.is_set():
        try:
            async with websockets.connect(ws_url) as websocket:
                # Subscribe to candle stream
                subscribe_msg = {
                    "method": "subscribe",
                    "params": {
                        "source": "candle",
                        "symbol": symbol,
                        "interval": interval
                    }
                }

                await websocket.send(json.dumps(subscribe_msg))
                print(f"✓ Subscribed to {symbol} {interval} candles")

                while not stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)

                        # Check if it's a candle update
                        if data.get('channel') == 'candle':
                            candle_data = data.get('data', {})

                            # Extract candle information
                            timestamp = candle_data.get('t')  # Start time
                            open_price = float(candle_data.get('o', 0))
                            high_price = float(candle_data.get('h', 0))
                            low_price = float(candle_data.get('l', 0))
                            close_price = float(candle_data.get('c', 0))
                            volume = float(candle_data.get('v', 0))
                            trades_count = int(candle_data.get('n', 0))

                            # Create new kline row
                            new_kline = pd.DataFrame([{
                                'timestamp': timestamp,
                                'open': open_price,
                                'high': high_price,
                                'low': low_price,
                                'close': close_price,
                                'volume': volume,
                                'trades_count': trades_count
                            }])

                            # Update cache file
                            if os.path.exists(kline_cache_file):
                                existing_klines = pd.read_csv(kline_cache_file)

                                # Check if this candle already exists (update) or is new (append)
                                if timestamp in existing_klines['timestamp'].values:
                                    # Update existing candle
                                    existing_klines.loc[existing_klines['timestamp'] == timestamp] = new_kline.iloc[0]
                                else:
                                    # Append new candle
                                    existing_klines = pd.concat([existing_klines, new_kline], ignore_index=True)

                                existing_klines = existing_klines.sort_values('timestamp')
                                existing_klines.to_csv(kline_cache_file, index=False)
                            else:
                                # Create new cache file
                                new_kline.to_csv(kline_cache_file, index=False)

                            print(f"[{datetime.fromtimestamp(timestamp/1000)}] Candle: O={open_price:.2f} H={high_price:.2f} L={low_price:.2f} C={close_price:.2f} V={volume:.3f}")

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        continue

        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


async def main():
    parser = argparse.ArgumentParser(description='Generate klines from trades and stream real-time candles')
    parser.add_argument('--symbol', type=str, default='BNB', help='Trading symbol (e.g., BNB, SOL)')
    parser.add_argument('--interval', type=str, default='5m',
                       help='Kline interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d')
    parser.add_argument('--data-dir', type=str, default='./PACIFICA_data',
                       help='Directory containing trades CSV files')
    parser.add_argument('--historical-only', action='store_true',
                       help='Only generate historical klines, do not stream real-time')

    args = parser.parse_args()

    symbol = args.symbol
    interval = args.interval
    data_dir = args.data_dir

    # File paths
    trades_file = os.path.join(data_dir, f'trades_{symbol}.csv')
    kline_cache_file = os.path.join(data_dir, f'klines_{symbol}_{interval}.csv')

    print(f"=" * 80)
    print(f"KLINE GENERATOR - {symbol} {interval}")
    print(f"=" * 80)
    print()

    # Step 1: Generate historical klines from trades
    if os.path.exists(trades_file):
        print(f"Loading trades from {trades_file}...")
        trades_df = pd.read_csv(trades_file)
        print(f"Loaded {len(trades_df)} trades")

        if not trades_df.empty:
            print(f"Generating {interval} klines from trades...")
            klines = generate_klines_from_trades(trades_df, interval)
            print(f"Generated {len(klines)} historical klines")

            # Save to cache
            klines.to_csv(kline_cache_file, index=False)
            print(f"✓ Saved klines to {kline_cache_file}")

            # Display sample
            if len(klines) > 0:
                print("\nFirst 5 klines:")
                print(klines.head().to_string(index=False))
                print("\nLast 5 klines:")
                print(klines.tail().to_string(index=False))
        else:
            print("⚠️  No trades data available")
    else:
        print(f"⚠️  Trades file not found: {trades_file}")
        print("Creating empty kline cache...")
        pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trades_count']).to_csv(kline_cache_file, index=False)

    # Step 2: Subscribe to real-time candles (unless historical-only mode)
    if not args.historical_only:
        print()
        print(f"Starting real-time candle stream for {symbol} {interval}...")
        print("Press Ctrl+C to stop")
        print()

        stop_event = asyncio.Event()

        try:
            await subscribe_to_candles(symbol, interval, kline_cache_file, stop_event)
        except KeyboardInterrupt:
            print("\n\nStopping candle stream...")
            stop_event.set()

    print()
    print(f"Kline data available in: {kline_cache_file}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
