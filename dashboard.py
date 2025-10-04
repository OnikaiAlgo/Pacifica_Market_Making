"""
Real-time dashboard to monitor Pacifica account: orders, positions, balance, and activity.

Usage:
    python dashboard.py
"""
import asyncio
import json
import time
import sys
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import logging

import requests
import websockets
from dotenv import load_dotenv
import os

# Setup logging (file only, no console output to avoid interfering with dashboard display)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log')
    ]
)
logger = logging.getLogger(__name__)

# Add pacifica_sdk to path
sys.path.insert(0, str(Path(__file__).parent / "pacifica_sdk"))
from common.constants import REST_URL, WS_URL

# Load environment variables
load_dotenv()
SOL_WALLET = os.getenv("SOL_WALLET")

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def move_cursor_home():
    """Move cursor to home position and clear screen"""
    print('\033[H\033[J', end='')  # Move to home and clear from cursor to end of screen


def hide_cursor():
    """Hide terminal cursor"""
    print('\033[?25l', end='')


def show_cursor():
    """Show terminal cursor"""
    print('\033[?25h', end='')


def get_initial_data():
    """Get initial data via REST API (only called once at startup)"""
    logger.info("Fetching initial data from REST API...")
    account_info = {}
    open_orders = []
    positions = []

    # Get account info
    try:
        api_url = f"{REST_URL}/account"
        params = {"account": SOL_WALLET}
        logger.debug(f"GET {api_url} params={params}")
        response = requests.get(api_url, params=params, timeout=5)
        logger.debug(f"Account info response: status={response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                account_info = data.get("data", {})
                logger.info(f"Account info loaded: balance={account_info.get('balance')}, available={account_info.get('available_to_spend')}")
            else:
                logger.warning(f"Account info API returned success=false: {data}")
    except Exception as e:
        logger.error(f"Failed to fetch account info: {e}")

    # Get open orders
    try:
        api_url = f"{REST_URL}/orders"
        params = {"account": SOL_WALLET}
        logger.debug(f"GET {api_url} params={params}")
        response = requests.get(api_url, params=params, timeout=5)
        logger.debug(f"Orders response: status={response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                open_orders = data.get("data", [])
                logger.info(f"Loaded {len(open_orders)} open orders")
            else:
                logger.warning(f"Orders API returned success=false: {data}")
    except Exception as e:
        logger.error(f"Failed to fetch open orders: {e}")

    # Get positions
    try:
        api_url = f"{REST_URL}/positions"
        params = {"account": SOL_WALLET}
        logger.debug(f"GET {api_url} params={params}")
        response = requests.get(api_url, params=params, timeout=5)
        logger.debug(f"Positions response: status={response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                positions = data.get("data", [])
                logger.info(f"Loaded {len(positions)} positions")
            else:
                logger.warning(f"Positions API returned success=false: {data}")
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")

    return account_info, open_orders, positions


def format_timestamp(ts_ms):
    """Format timestamp to readable string with millisecond precision"""
    if ts_ms:
        dt = datetime.fromtimestamp(ts_ms / 1000)
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Remove last 3 digits to show milliseconds
    return "N/A"


def render_dashboard(account_info, open_orders, positions, recent_events, mid_prices, first_render=False):
    """Render the dashboard"""
    if first_render:
        clear_screen()
        hide_cursor()
    else:
        move_cursor_home()

    # Build output buffer to reduce flicker
    output = []

    # Header
    output.append(f"{Colors.BOLD}{Colors.CYAN}{'=' * 100}{Colors.RESET}")
    output.append(f"{Colors.BOLD}{Colors.CYAN}                          PACIFICA TRADING DASHBOARD{Colors.RESET}")
    output.append(f"{Colors.BOLD}{Colors.CYAN}{'=' * 100}{Colors.RESET}")
    output.append(f"{Colors.GRAY}Account: {SOL_WALLET[:8]}...{SOL_WALLET[-8:]}                     {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}{Colors.RESET}")
    output.append("")

    # Account Balance Section
    output.append(f"{Colors.BOLD}{Colors.YELLOW}┌─ ACCOUNT BALANCE ─────────────────────────────────────────────────────────────────────────────┐{Colors.RESET}")

    if account_info:
        # Handle both REST API format (full names) and WebSocket format (abbreviated)
        balance = float(account_info.get('balance') or account_info.get('b', 0))
        available = float(account_info.get('available_to_spend') or account_info.get('as', 0))
        margin_used = float(account_info.get('total_margin_used') or account_info.get('mu', 0))
        # Unrealized PnL is calculated from positions, not directly in account_info
        unrealized_pnl = 0.0  # Will be calculated from positions if needed

        pnl_color = Colors.GREEN if unrealized_pnl >= 0 else Colors.RED
        pnl_sign = '+' if unrealized_pnl >= 0 else ''

        output.append(f"│ Balance: {Colors.BOLD}${balance:,.2f}{Colors.RESET}     "
              f"Available: {Colors.BOLD}${available:,.2f}{Colors.RESET}     "
              f"Margin Used: {Colors.BOLD}${margin_used:,.2f}{Colors.RESET}     "
              f"Unrealized PnL: {pnl_color}{Colors.BOLD}{pnl_sign}${unrealized_pnl:,.2f}{Colors.RESET} │")
    else:
        output.append(f"│ {Colors.GRAY}Loading account data...{Colors.RESET}                                                                │")

    output.append(f"{Colors.BOLD}{Colors.YELLOW}└───────────────────────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
    output.append("")

    # Positions Section
    output.append(f"{Colors.BOLD}{Colors.MAGENTA}┌─ POSITIONS ({len(positions)}) ──────────────────────────────────────────────────────────────────────────────────┐{Colors.RESET}")
    output.append(f"│ {Colors.BOLD}Symbol    Side      Size         Entry Price    Current Price   Unrealized PnL      Margin{Colors.RESET}      │")
    output.append(f"│ {Colors.GRAY}{'─' * 93}{Colors.RESET} │")

    # Always show exactly 4 position rows to prevent expanding render
    for i in range(4):
        if i < len(positions):
            pos = positions[i]
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            size = float(pos.get('size', 0))
            entry_price = float(pos.get('entry_price', 0))
            mark_price = float(pos.get('mark_price', 0))
            unrealized_pnl = float(pos.get('unrealized_pnl', 0))
            margin = float(pos.get('margin', 0))

            side_color = Colors.GREEN if side.lower() == 'long' else Colors.RED
            pnl_color = Colors.GREEN if unrealized_pnl >= 0 else Colors.RED
            pnl_sign = '+' if unrealized_pnl >= 0 else ''

            output.append(f"│ {symbol:<8}  {side_color}{side:<6}{Colors.RESET}    {size:>10.4f}   ${entry_price:>10.4f}   ${mark_price:>10.4f}   "
                  f"{pnl_color}{pnl_sign}${unrealized_pnl:>9.2f}{Colors.RESET}     ${margin:>9.2f}   │")
        else:
            # Empty row
            output.append(f"│{' ' * 95}│")

    output.append(f"{Colors.BOLD}{Colors.MAGENTA}└───────────────────────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
    output.append("")

    # Open Orders Section
    output.append(f"{Colors.BOLD}{Colors.BLUE}┌─ OPEN ORDERS ({len(open_orders)}) ────────────────────────────────────────────────────────────────────┐{Colors.RESET}")
    output.append(f"│ {Colors.BOLD}ID        Symbol  Side  Price     % Mid   Amt    Fill   Status   Created{Colors.RESET}                   │")
    output.append(f"│ {Colors.GRAY}{'─' * 93}{Colors.RESET} │")

    # Always show exactly 4 order rows to prevent expanding render
    for i in range(4):
        if i < len(open_orders):
            order = open_orders[i]
            order_id = str(order.get('order_id', 'N/A'))[:9]  # Truncate ID
            symbol = order.get('symbol', 'N/A')
            side = order.get('side', 'N/A')
            price = float(order.get('price', 0))
            initial_amount = float(order.get('initial_amount', 0))
            filled_amount = float(order.get('filled_amount', 0))
            order_type = order.get('order_type', 'N/A')
            created_at = format_timestamp(order.get('created_at'))

            side_color = Colors.GREEN if side.lower() == 'bid' else Colors.RED

            # Calculate % difference from mid price
            mid_price = mid_prices.get(symbol)
            if mid_price and mid_price > 0:
                pct_diff = ((price - mid_price) / mid_price) * 100
                pct_str = f"{pct_diff:>+6.2f}%"
                # Color based on whether order is above/below mid
                pct_color = Colors.RED if pct_diff > 0 else Colors.GREEN
                pct_display = f"{pct_color}{pct_str}{Colors.RESET}"
            else:
                pct_display = f"{Colors.GRAY}  N/A  {Colors.RESET}"

            output.append(f"│ {order_id:<9} {symbol:<7} {side_color}{side:<4}{Colors.RESET}  ${price:>6.3f} {pct_display} {initial_amount:>6.1f} {filled_amount:>6.1f}  {order_type[:6]:<6} {created_at} │")
        else:
            # Empty row
            output.append(f"│{' ' * 95}│")

    output.append(f"{Colors.BOLD}{Colors.BLUE}└───────────────────────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
    output.append("")

    # Recent Events Section
    output.append(f"{Colors.BOLD}{Colors.WHITE}┌─ RECENT EVENTS (last 5) ──────────────────────────────────────────────────────────────────────┐{Colors.RESET}")

    # Always show exactly 5 event rows to prevent expanding render
    events_to_show = list(recent_events)[-5:]
    for event in events_to_show:
        # Strip ANSI color codes for length calculation
        event_plain = re.sub(r'\033\[[0-9;]+m', '', event) if event else ""
        # Pad to 94 chars, keeping original event (with color codes)
        padding = 94 - len(event_plain)
        output.append(f"│ {event}{' ' * padding} │")

    output.append(f"{Colors.BOLD}{Colors.WHITE}└───────────────────────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
    output.append("")

    output.append(f"{Colors.GRAY}Press Ctrl+C to exit                                        Updates: Real-time via WebSocket{Colors.RESET}")

    # Print entire output buffer at once to reduce flicker
    print('\n'.join(output), flush=True)


async def listen_to_account_updates(recent_events, account_info, open_orders_dict, positions_dict, mid_prices):
    """Listen to WebSocket for account updates and maintain state"""
    uri = WS_URL
    logger.info(f"Starting WebSocket listener, connecting to {uri}")

    while True:
        try:
            logger.debug("Attempting WebSocket connection...")
            async with websockets.connect(uri) as websocket:
                logger.info("WebSocket connected successfully")

                # Subscribe to all account channels
                subscribe_orders = {
                    "method": "subscribe",
                    "params": {
                        "source": "account_orders",
                        "account": SOL_WALLET
                    }
                }

                subscribe_positions = {
                    "method": "subscribe",
                    "params": {
                        "source": "account_positions",
                        "account": SOL_WALLET
                    }
                }

                subscribe_info = {
                    "method": "subscribe",
                    "params": {
                        "source": "account_info",
                        "account": SOL_WALLET
                    }
                }

                subscribe_prices = {
                    "method": "subscribe",
                    "params": {
                        "source": "prices"
                    }
                }

                await websocket.send(json.dumps(subscribe_orders))
                await websocket.send(json.dumps(subscribe_positions))
                await websocket.send(json.dumps(subscribe_info))
                await websocket.send(json.dumps(subscribe_prices))
                logger.info("Sent all WebSocket subscriptions (account_orders, account_positions, account_info, prices)")

                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                recent_events.append(f"{Colors.CYAN}[{timestamp}] WebSocket connected - subscribed to account updates{Colors.RESET}")

                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)

                        channel = data.get('channel')
                        logger.debug(f"WS message: channel={channel}, data_type={type(data.get('data')).__name__}")

                        if channel == 'account_orders':
                            orders_data = data.get('data', [])

                            # account_orders sends data as a list of orders
                            if isinstance(orders_data, list):
                                logger.debug(f"account_orders: received list with {len(orders_data)} orders")

                                # Update the open_orders_dict to match the current state
                                # Clear existing orders and replace with the new list
                                current_order_ids = set()

                                for order_data in orders_data:
                                    if not isinstance(order_data, dict):
                                        continue

                                    # Log the full order data to understand field names
                                    logger.debug(f"Order data fields: {list(order_data.keys())}")
                                    logger.debug(f"Full order data: {order_data}")

                                    # Map abbreviated field names to full names
                                    # Field mapping: i=order_id, I=client_order_id, s=symbol, d=direction/side,
                                    # p=price, a=amount, f=filled, c=cancelled, t=timestamp, ot=order_type, ro=reduce_only
                                    order_id = str(order_data.get('i', order_data.get('order_id', 'N/A')))
                                    symbol = order_data.get('s', order_data.get('symbol', 'N/A'))
                                    side = order_data.get('d', order_data.get('side', 'N/A'))  # 'd' = direction
                                    price = order_data.get('p', order_data.get('price', 0))
                                    amount = order_data.get('a', order_data.get('initial_amount', 0))

                                    current_order_ids.add(order_id)

                                    # Check if this is a new order
                                    if order_id not in open_orders_dict:
                                        # Convert abbreviated format to full format for display
                                        full_order_data = {
                                            'order_id': order_id,
                                            'symbol': symbol,
                                            'side': side,
                                            'price': price,
                                            'initial_amount': amount,
                                            'filled_amount': order_data.get('f', order_data.get('filled_amount', 0)),
                                            'order_type': order_data.get('ot', order_data.get('order_type', 'limit')),
                                            'created_at': order_data.get('t', order_data.get('created_at', 0)),
                                            'client_order_id': order_data.get('I', order_data.get('client_order_id', ''))  # 'I' (capital i) = client_order_id
                                        }
                                        open_orders_dict[order_id] = full_order_data

                                        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                                        event_msg = f"{Colors.GREEN}[{timestamp}] ORDER CREATED: {symbol} {side} #{order_id}{Colors.RESET}"
                                        recent_events.append(event_msg)
                                        logger.info(f"ORDER CREATED: symbol={symbol}, side={side}, order_id={order_id}, price={price}, amount={amount}")
                                    else:
                                        # Update existing order
                                        open_orders_dict[order_id].update({
                                            'filled_amount': order_data.get('f', order_data.get('filled_amount', 0))
                                        })

                                # Remove orders that are no longer in the list (cancelled/filled)
                                removed_order_ids = set(open_orders_dict.keys()) - current_order_ids
                                for removed_id in removed_order_ids:
                                    removed_order = open_orders_dict[removed_id]
                                    symbol = removed_order.get('symbol', 'N/A')
                                    side = removed_order.get('side', 'N/A')

                                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                                    event_msg = f"{Colors.YELLOW}[{timestamp}] ORDER REMOVED: {symbol} {side} #{removed_id}{Colors.RESET}"
                                    recent_events.append(event_msg)
                                    logger.info(f"ORDER REMOVED (cancelled or filled): order_id={removed_id}")

                                    del open_orders_dict[removed_id]
                            else:
                                logger.warning(f"account_orders data is not a list: {type(orders_data).__name__}")

                        elif channel == 'account_positions':
                            pos_data = data.get('data', {})
                            # Skip if data is not a dict
                            if not isinstance(pos_data, dict):
                                logger.warning(f"account_positions data is not a dict: {type(pos_data).__name__}")
                                continue

                            symbol = pos_data.get('symbol', 'N/A')
                            side = pos_data.get('side', 'N/A')
                            size = float(pos_data.get('size', 0))

                            logger.info(f"POSITION UPDATE: symbol={symbol}, side={side}, size={size}")

                            # Update positions dict
                            pos_key = f"{symbol}_{side}"
                            if size > 0:
                                positions_dict[pos_key] = pos_data
                            elif pos_key in positions_dict:
                                del positions_dict[pos_key]

                            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                            event_msg = f"{Colors.MAGENTA}[{timestamp}] POSITION UPDATE: {symbol} {side} size={size}{Colors.RESET}"
                            recent_events.append(event_msg)

                        elif channel == 'account_info':
                            info_data = data.get('data', {})
                            # Skip if data is not a dict
                            if not isinstance(info_data, dict):
                                logger.warning(f"account_info data is not a dict: {type(info_data).__name__}, data={data.get('data')}")
                                continue

                            # Log the raw data to understand the field names
                            logger.debug(f"account_info data: {info_data}")
                            account_info.update(info_data)

                            balance = info_data.get('b', info_data.get('balance', 'N/A'))
                            available = info_data.get('as', info_data.get('available_to_spend', 'N/A'))
                            logger.info(f"ACCOUNT INFO UPDATE: balance={balance}, available={available}")

                            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                            recent_events.append(f"{Colors.BLUE}[{timestamp}] ACCOUNT INFO UPDATED{Colors.RESET}")

                        elif channel == 'prices':
                            price_data = data.get('data', [])
                            # prices channel sends an array of all symbols
                            if isinstance(price_data, list):
                                for item in price_data:
                                    if isinstance(item, dict):
                                        symbol = item.get('symbol', 'N/A')
                                        mid = item.get('mid')

                                        if mid and symbol != 'N/A':
                                            mid_prices[symbol] = float(mid)
                                            logger.debug(f"PRICE UPDATE: {symbol} mid={mid}")
                            else:
                                logger.warning(f"prices data is not a list: {type(price_data).__name__}")

                    except asyncio.TimeoutError:
                        continue

        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            recent_events.append(f"{Colors.RED}[{timestamp}] WebSocket error: {str(e)[:50]}{Colors.RESET}")
            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)  # Reconnect after 5 seconds


async def refresh_dashboard():
    """Main dashboard refresh loop"""
    # Pre-populate recent_events with 5 empty slots to prevent expanding render
    recent_events = [""] * 5
    mid_prices = {}  # Dict to store current mid prices by symbol

    # Get initial data from REST API (only once at startup)
    print(f"{Colors.CYAN}Fetching initial data...{Colors.RESET}")
    initial_account, initial_orders, initial_positions = get_initial_data()

    # Convert to dict for WebSocket updates
    account_info = initial_account
    open_orders_dict = {str(order.get('order_id')): order for order in initial_orders}
    positions_dict = {f"{pos.get('symbol')}_{pos.get('side')}": pos for pos in initial_positions}

    # Start WebSocket listener in background
    asyncio.create_task(listen_to_account_updates(recent_events, account_info, open_orders_dict, positions_dict, mid_prices))

    await asyncio.sleep(1)  # Give WebSocket time to connect

    first_render = True
    while True:
        try:
            # Convert dicts back to lists for rendering
            open_orders = list(open_orders_dict.values())
            positions = list(positions_dict.values())

            # Render dashboard
            render_dashboard(account_info, open_orders, positions, recent_events, mid_prices, first_render)
            first_render = False

            # Refresh display every 1 second (data updated in real-time via WebSocket)
            await asyncio.sleep(1)

        except KeyboardInterrupt:
            show_cursor()
            print(f"\n\n{Colors.YELLOW}Dashboard stopped.{Colors.RESET}")
            break
        except Exception as e:
            show_cursor()
            print(f"\n\n{Colors.RED}Error: {e}{Colors.RESET}")
            await asyncio.sleep(2)


async def main():
    """Main entry point"""
    logger.info("=== Pacifica Trading Dashboard Starting ===")

    if not SOL_WALLET:
        logger.error("SOL_WALLET not found in .env file")
        print(f"{Colors.RED}Error: SOL_WALLET not found in .env file{Colors.RESET}")
        return

    logger.info(f"Account: {SOL_WALLET[:8]}...{SOL_WALLET[-8:]}")
    print(f"{Colors.CYAN}Starting Pacifica Trading Dashboard...{Colors.RESET}")
    await asyncio.sleep(1)

    await refresh_dashboard()


if __name__ == "__main__":
    try:
        logger.info("Dashboard application started")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user (KeyboardInterrupt)")
        show_cursor()
        print(f"\n{Colors.YELLOW}Dashboard stopped by user.{Colors.RESET}")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        raise
    finally:
        show_cursor()
        logger.info("Dashboard application exited")
