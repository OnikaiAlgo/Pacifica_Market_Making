"""
Get YOUR personal trading volume for the last N days from Pacifica Finance DEX.

This script fetches your account's trade history and calculates your total trading volume
for a specified symbol over a configurable time period.

Usage:
    python get_my_trading_volume.py --symbol ETH --days 7
    python get_my_trading_volume.py --symbol BTC --days 30
    python get_my_trading_volume.py --days 7  # All symbols
"""

import asyncio
import argparse
import time
from datetime import datetime, timedelta
from api_client import ApiClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API credentials
PRIVATE_KEY = os.getenv('PRIVATE_KEY')


async def get_my_trading_volume(symbol: str = None, days: int = 7):
    """
    Fetch YOUR trading volume for the last N days.

    Args:
        symbol: Trading pair symbol (e.g., 'ETH', 'BTC'), or None for all symbols
        days: Number of days to look back (default: 7)

    Returns:
        dict: Your volume statistics including base volume, quote volume, and trade count
    """
    client = ApiClient(PRIVATE_KEY, release_mode=False)

    # Calculate time range
    end_time = int(time.time() * 1000)  # Current time in milliseconds
    start_time = end_time - (days * 24 * 60 * 60 * 1000)  # N days ago

    print(f"[INFO] Fetching YOUR trading volume")
    if symbol:
        print(f"[INFO] Symbol: {symbol}")
    else:
        print(f"[INFO] Symbol: ALL")
    print(f"[INFO] Period: {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
    print(f"[INFO] Days: {days}")
    print()

    # Track volumes by symbol and by day
    symbol_volumes = {}
    daily_volumes = {}  # day_key -> {quote_volume, trade_count, buy_volume, sell_volume}
    total_quote_volume = 0.0
    total_trades = 0

    async with client:
        try:
            if symbol:
                # Get trades for specific symbol with pagination
                all_trades = []
                batch = 0

                # Pagination loop - keep fetching until we get all trades
                while True:
                    batch += 1

                    # Fetch trade history using Pacifica API
                    result = await client.get_trade_history(
                        symbol=symbol,
                        start_time=start_time if batch == 1 else None,
                        end_time=end_time if batch == 1 else None,
                        limit=1000
                    )

                    trades = result.get('trades', [])

                    if not trades:
                        break

                    # Filter trades by time range
                    filtered_trades = [t for t in trades if start_time <= int(t['timestamp']) <= end_time]
                    all_trades.extend(filtered_trades)

                    print(f"[INFO] Batch {batch}: Fetched {len(trades)} trades ({len(filtered_trades)} in time range)")

                    # If we got less than 1000, we're done
                    if len(trades) < 1000:
                        break

                    # Check if last trade is beyond our end time
                    if int(trades[-1]['timestamp']) > end_time:
                        break

                    await asyncio.sleep(0.1)

                print(f"[INFO] Total: {len(all_trades)} trades for {symbol}")
                trades = all_trades

                # Process trades
                for trade in trades:
                    qty = float(trade['quantity'])
                    price = float(trade['price'])
                    quote_qty = qty * price
                    trade_time = int(trade['timestamp'])

                    # Get the date for this trade
                    trade_date = datetime.fromtimestamp(trade_time / 1000).strftime('%Y-%m-%d')

                    if symbol not in symbol_volumes:
                        symbol_volumes[symbol] = {
                            'base_volume': 0.0,
                            'quote_volume': 0.0,
                            'trade_count': 0,
                            'buy_volume': 0.0,
                            'sell_volume': 0.0,
                            'buy_count': 0,
                            'sell_count': 0
                        }

                    symbol_volumes[symbol]['base_volume'] += qty
                    symbol_volumes[symbol]['quote_volume'] += quote_qty
                    symbol_volumes[symbol]['trade_count'] += 1
                    total_quote_volume += quote_qty
                    total_trades += 1

                    # Track by day
                    if trade_date not in daily_volumes:
                        daily_volumes[trade_date] = {
                            'quote_volume': 0.0,
                            'trade_count': 0,
                            'buy_volume': 0.0,
                            'sell_volume': 0.0,
                            'buy_count': 0,
                            'sell_count': 0
                        }

                    daily_volumes[trade_date]['quote_volume'] += quote_qty
                    daily_volumes[trade_date]['trade_count'] += 1

                    # Track buy vs sell
                    if trade['side'] == 'bid':
                        symbol_volumes[symbol]['buy_volume'] += quote_qty
                        symbol_volumes[symbol]['buy_count'] += 1
                        daily_volumes[trade_date]['buy_volume'] += quote_qty
                        daily_volumes[trade_date]['buy_count'] += 1
                    else:
                        symbol_volumes[symbol]['sell_volume'] += quote_qty
                        symbol_volumes[symbol]['sell_count'] += 1
                        daily_volumes[trade_date]['sell_volume'] += quote_qty
                        daily_volumes[trade_date]['sell_count'] += 1

            else:
                # Get trades for all symbols
                # Get markets to find available symbols
                print(f"[INFO] Fetching available markets...")

                markets_response = await client.get_markets()
                markets = markets_response.get('markets', [])

                # Extract symbols and sort by volume
                all_symbols = [m['symbol'] for m in markets if m.get('symbol')]

                # Take top 40 symbols (or all if less than 40)
                top_symbols = all_symbols[:40]
                print(f"[INFO] Top symbols: {', '.join(top_symbols[:10])}...")

                print(f"[INFO] Checking {len(top_symbols)} top symbols for your trades...")

                for idx, sym in enumerate(top_symbols, 1):
                    if idx % 10 == 0:
                        print(f"[PROGRESS] Checked {idx}/{len(top_symbols)} symbols...")
                    try:
                        # Pagination for each symbol
                        all_trades_for_symbol = []
                        batch = 0

                        while True:
                            batch += 1

                            # Fetch trade history
                            result = await client.get_trade_history(
                                symbol=sym,
                                start_time=start_time if batch == 1 else None,
                                end_time=end_time if batch == 1 else None,
                                limit=1000
                            )

                            trades = result.get('trades', [])

                            if not trades:
                                break

                            # Filter by time range
                            filtered_trades = [t for t in trades if start_time <= int(t['timestamp']) <= end_time]
                            all_trades_for_symbol.extend(filtered_trades)

                            # If we got less than 1000, we're done
                            if len(trades) < 1000:
                                break

                            # Check if last trade is beyond our end time
                            if int(trades[-1]['timestamp']) > end_time:
                                break

                            await asyncio.sleep(0.05)  # Shorter delay for all-symbols scan

                        trades = all_trades_for_symbol

                        if trades:
                            print(f"[INFO] Found {len(trades)} trades for {sym}")

                            for trade in trades:
                                qty = float(trade['quantity'])
                                price = float(trade['price'])
                                quote_qty = qty * price
                                trade_time = int(trade['timestamp'])

                                # Get the date for this trade
                                trade_date = datetime.fromtimestamp(trade_time / 1000).strftime('%Y-%m-%d')

                                if sym not in symbol_volumes:
                                    symbol_volumes[sym] = {
                                        'base_volume': 0.0,
                                        'quote_volume': 0.0,
                                        'trade_count': 0,
                                        'buy_volume': 0.0,
                                        'sell_volume': 0.0,
                                        'buy_count': 0,
                                        'sell_count': 0
                                    }

                                symbol_volumes[sym]['base_volume'] += qty
                                symbol_volumes[sym]['quote_volume'] += quote_qty
                                symbol_volumes[sym]['trade_count'] += 1
                                total_quote_volume += quote_qty
                                total_trades += 1

                                # Track by day
                                if trade_date not in daily_volumes:
                                    daily_volumes[trade_date] = {
                                        'quote_volume': 0.0,
                                        'trade_count': 0,
                                        'buy_volume': 0.0,
                                        'sell_volume': 0.0,
                                        'buy_count': 0,
                                        'sell_count': 0
                                    }

                                daily_volumes[trade_date]['quote_volume'] += quote_qty
                                daily_volumes[trade_date]['trade_count'] += 1

                                # Track buy vs sell
                                if trade['side'] == 'bid':
                                    symbol_volumes[sym]['buy_volume'] += quote_qty
                                    symbol_volumes[sym]['buy_count'] += 1
                                    daily_volumes[trade_date]['buy_volume'] += quote_qty
                                    daily_volumes[trade_date]['buy_count'] += 1
                                else:
                                    symbol_volumes[sym]['sell_volume'] += quote_qty
                                    symbol_volumes[sym]['sell_count'] += 1
                                    daily_volumes[trade_date]['sell_volume'] += quote_qty
                                    daily_volumes[trade_date]['sell_count'] += 1

                    except Exception as e:
                        # Silently skip symbols with no trades or errors
                        continue

        except Exception as e:
            print(f"[ERROR] Error fetching trades: {e}")
            import traceback
            traceback.print_exc()
            return None

    # Calculate averages
    avg_daily_quote_volume = total_quote_volume / days if days > 0 else 0
    avg_daily_trades = total_trades / days if days > 0 else 0

    # Display results
    print()
    print("=" * 70)
    print(f"YOUR TRADING VOLUME REPORT")
    print("=" * 70)
    print(f"Period: {days} days")
    print(f"From:   {datetime.fromtimestamp(start_time/1000).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"To:     {datetime.fromtimestamp(end_time/1000).strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not symbol_volumes:
        print("[INFO] No trades found in the specified period")
        print("=" * 70)
        return None

    # Display daily breakdown table
    print("DAILY BREAKDOWN:")
    print("=" * 70)
    print(f"{'Date':<12} {'Volume ($)':>15} {'Trades':>10} {'Buy ($)':>15} {'Sell ($)':>15}")
    print("-" * 70)

    # Sort dates chronologically
    sorted_dates = sorted(daily_volumes.keys())

    for date in sorted_dates:
        vol = daily_volumes[date]
        print(f"{date:<12} ${vol['quote_volume']:>14,.2f} {vol['trade_count']:>10,} "
              f"${vol['buy_volume']:>14,.2f} ${vol['sell_volume']:>14,.2f}")

    print("-" * 70)
    print(f"{'TOTAL':<12} ${total_quote_volume:>14,.2f} {total_trades:>10,} "
          f"${sum(v['buy_volume'] for v in daily_volumes.values()):>14,.2f} "
          f"${sum(v['sell_volume'] for v in daily_volumes.values()):>14,.2f}")
    print("=" * 70)
    print()

    # Display per-symbol breakdown
    print("BREAKDOWN BY SYMBOL:")
    print("-" * 70)
    for sym, vol in sorted(symbol_volumes.items(), key=lambda x: x[1]['quote_volume'], reverse=True):
        print(f"\n{sym}:")
        print(f"  Base Volume:   {vol['base_volume']:,.4f} {sym}")
        print(f"  Quote Volume:  ${vol['quote_volume']:,.2f}")
        print(f"  Trade Count:   {vol['trade_count']:,}")
        print(f"  Buy Volume:    ${vol['buy_volume']:,.2f} ({vol['buy_count']} trades)")
        print(f"  Sell Volume:   ${vol['sell_volume']:,.2f} ({vol['sell_count']} trades)")

    print()
    print("-" * 70)
    print("SUMMARY:")
    print(f"  Total Quote Volume: ${total_quote_volume:,.2f}")
    print(f"  Total Trades:       {total_trades:,}")
    print(f"  Daily Average:      ${avg_daily_quote_volume:,.2f}/day ({avg_daily_trades:,.0f} trades/day)")
    print("=" * 70)

    return {
        'symbol_volumes': symbol_volumes,
        'total_quote_volume': total_quote_volume,
        'total_trades': total_trades,
        'avg_daily_quote_volume': avg_daily_quote_volume,
        'avg_daily_trades': avg_daily_trades,
        'days': days
    }


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Get YOUR perpetual futures trading volume for the last N days'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        default=None,
        help='Trading pair symbol (default: all symbols)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to look back (default: 7)'
    )

    args = parser.parse_args()

    # Validate inputs
    if args.days <= 0:
        print("[ERROR] days must be greater than 0")
        return

    if args.days > 365:
        print("[WARN] Fetching more than 365 days of data may take a long time")

    try:
        symbol = args.symbol.upper() if args.symbol else None
        await get_my_trading_volume(symbol, args.days)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())