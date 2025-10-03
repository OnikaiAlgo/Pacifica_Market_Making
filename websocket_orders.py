#!/usr/bin/env python3
"""
WebSocket Order and Account Monitor for Pacifica Finance
Monitors real-time order updates, trade executions, and account changes
"""

import asyncio
import json
import os
import time
import websockets
from datetime import datetime
from dotenv import load_dotenv
from api_client import ApiClient

load_dotenv()


class OrderStreamMonitor:
    """Monitor and display order and account updates with detailed information."""

    def __init__(self):
        self.order_count = 0
        self.trade_count = 0
        self.account_updates = 0
        self.start_time = datetime.now()

    def format_timestamp(self, timestamp_ms):
        """Convert timestamp to readable format."""
        if timestamp_ms > 10**12:  # If in microseconds
            timestamp_ms = timestamp_ms / 1000
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S.%f')[:-3]

    def print_detailed_order(self, order_data):
        """Print detailed order information."""
        # Extract order fields (Pacifica format)
        symbol = order_data.get('symbol', 'N/A')
        client_order_id = order_data.get('client_order_id', 'N/A')
        side = order_data.get('side', 'N/A')  # bid/ask
        order_type = order_data.get('order_type', order_data.get('type', 'N/A'))
        tif = order_data.get('tif', 'N/A')
        quantity = order_data.get('amount', order_data.get('quantity', '0'))
        price = order_data.get('price', '0')
        avg_price = order_data.get('avg_price', '0')
        status = order_data.get('status', 'N/A')
        order_id = order_data.get('order_id', order_data.get('id', 'N/A'))
        filled_qty = order_data.get('filled_amount', order_data.get('filled', '0'))
        remaining_qty = order_data.get('remaining_amount', order_data.get('remaining', '0'))
        reduce_only = order_data.get('reduce_only', False)
        created_at = order_data.get('created_at', order_data.get('timestamp', 0))
        updated_at = order_data.get('updated_at', created_at)

        # Last trade information if available
        last_trade = order_data.get('last_trade', {})
        last_filled_qty = last_trade.get('quantity', '0') if last_trade else '0'
        last_filled_price = last_trade.get('price', '0') if last_trade else '0'
        trade_id = last_trade.get('id', 0) if last_trade else 0

        print("\n" + "="*80)
        print(f"ORDER UPDATE #{self.order_count + 1} - {symbol}")
        print("="*80)
        print(f"Time: {self.format_timestamp(updated_at)}")
        print(f"Order ID: {order_id}")
        print(f"Client Order ID: {client_order_id}")
        print(f"Side: {side.upper()}")
        print(f"Type: {order_type} | Time in Force: {tif}")
        print(f"Order Status: {status}")

        print(f"\nOrder Details:")
        print(f"  Original Quantity: {quantity}")
        print(f"  Original Price: ${price}")
        print(f"  Filled Quantity: {filled_qty}")
        print(f"  Remaining Quantity: {remaining_qty}")

        if status == 'PARTIALLY_FILLED' or status == 'partial':
            fill_percentage = (float(filled_qty) / float(quantity) * 100) if float(quantity) > 0 else 0
            print(f"  [PARTIALLY FILLED - {fill_percentage:.1f}% complete: {filled_qty} / {quantity}]")

        if float(avg_price) > 0:
            print(f"  Average Fill Price: ${avg_price}")

        if last_trade and float(last_filled_qty) > 0:
            print(f"\nLast Fill:")
            print(f"  Quantity: {last_filled_qty}")
            print(f"  Price: ${last_filled_price}")
            print(f"  Trade ID: {trade_id}")

        if reduce_only:
            print(f"  [REDUCE ONLY ORDER]")

        print("="*80)

        # Count trades
        if status in ['FILLED', 'filled', 'PARTIALLY_FILLED', 'partial'] and last_trade:
            self.trade_count += 1
            print(f"*** TRADE EXECUTION #{self.trade_count} ***")

        self.order_count += 1

    def print_account_update(self, account_data):
        """Print detailed account update information."""
        reason = account_data.get('reason', account_data.get('type', 'N/A'))

        print("\n" + "="*80)
        print(f"ACCOUNT UPDATE #{self.account_updates + 1} - {reason}")
        print("="*80)

        # Balance updates
        balances = account_data.get('balances', [])
        if balances:
            print("Balance Changes:")
            for balance in balances:
                currency = balance.get('currency', balance.get('asset', 'N/A'))
                available = balance.get('available', '0')
                total = balance.get('total', '0')
                locked = balance.get('locked', '0')

                print(f"  {currency}:")
                print(f"    Total Balance: {total}")
                print(f"    Available: {available}")
                if float(locked) > 0:
                    print(f"    Locked: {locked}")

        # Position updates
        positions = account_data.get('positions', [])
        if positions:
            print("\nPosition Updates:")
            for position in positions:
                symbol = position.get('symbol', 'N/A')
                size = position.get('size', position.get('amount', '0'))
                entry_price = position.get('entry_price', '0')
                unrealized_pnl = position.get('unrealized_pnl', '0')
                realized_pnl = position.get('realized_pnl', '0')
                margin = position.get('margin', '0')
                leverage = position.get('leverage', '1')
                side = position.get('side', 'N/A')

                if float(size) != 0:
                    print(f"  {symbol} ({side}):")
                    print(f"    Position Size: {size}")
                    print(f"    Entry Price: ${entry_price}")
                    print(f"    Leverage: {leverage}x")
                    print(f"    Unrealized PnL: {unrealized_pnl}")
                    if float(realized_pnl) != 0:
                        pnl_sign = "+" if float(realized_pnl) > 0 else ""
                        print(f"    Realized PnL: {pnl_sign}{realized_pnl}")
                    print(f"    Margin: {margin}")

        print("="*80)
        self.account_updates += 1

    def print_statistics(self):
        """Print session statistics."""
        duration = datetime.now() - self.start_time
        duration_seconds = duration.total_seconds()

        print("\n" + "="*80)
        print("SESSION STATISTICS")
        print("="*80)
        print(f"Session Duration: {int(duration_seconds // 60)}m {int(duration_seconds % 60)}s")
        print(f"Order Updates: {self.order_count}")
        print(f"Trade Executions: {self.trade_count}")
        print(f"Account Updates: {self.account_updates}")
        print(f"Total Events: {self.order_count + self.account_updates}")

        if duration_seconds > 0:
            events_per_minute = (self.order_count + self.account_updates) * 60 / duration_seconds
            print(f"Events per minute: {events_per_minute:.1f}")

        print("="*80)


class PacificaWebSocketClient:
    """WebSocket client for Pacifica Finance with authentication and reconnection."""

    def __init__(self, private_key: str, monitor: OrderStreamMonitor,
                 auto_reconnect: bool = True, reconnect_delay: int = 5):
        """
        Initialize Pacifica WebSocket client.

        Args:
            private_key: Solana private key in base58 format
            monitor: OrderStreamMonitor instance for displaying updates
            auto_reconnect: Whether to automatically reconnect on disconnection
            reconnect_delay: Seconds to wait before reconnecting
        """
        self.private_key = private_key
        self.monitor = monitor
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay

        # WebSocket configuration
        self.ws_url = "wss://ws.pacifica.fi/ws"
        self.ws = None
        self.is_connected = False
        self.should_stop = False

        # Create API client for authentication
        self.api_client = ApiClient(private_key, release_mode=True)
        self.public_key = self.api_client.public_key

        print(f"Initialized Pacifica WebSocket client for account: {self.public_key}")

    async def authenticate(self):
        """
        Authenticate the WebSocket connection using Solana signature.

        Returns:
            bool: True if authentication successful
        """
        try:
            timestamp = int(time.time() * 1000)

            # Create authentication message
            auth_header = {
                "timestamp": timestamp,
                "expiry_window": 60000,  # 60 seconds
                "type": "authenticate"
            }

            auth_payload = {
                "account": self.public_key
            }

            # Sign the authentication request
            _, signature = self.api_client._sign_message(auth_header, auth_payload)

            # Send authentication message
            auth_message = {
                "method": "authenticate",
                "params": {
                    "account": self.public_key,
                    "signature": signature,
                    "timestamp": timestamp,
                    "expiry_window": 60000
                }
            }

            await self.ws.send(json.dumps(auth_message))
            print("Authentication message sent")

            # Wait for authentication response
            response = await asyncio.wait_for(self.ws.recv(), timeout=10)
            data = json.loads(response)

            if data.get('type') == 'authenticated' or data.get('status') == 'authenticated':
                print("Successfully authenticated!")
                return True
            else:
                print(f"Authentication failed: {data}")
                return False

        except asyncio.TimeoutError:
            print("Authentication timeout")
            return False
        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    async def subscribe_to_channels(self):
        """Subscribe to account and order update channels."""
        try:
            # Subscribe to account updates
            account_sub = {
                "method": "subscribe",
                "params": {
                    "source": "account",
                    "account": self.public_key
                }
            }
            await self.ws.send(json.dumps(account_sub))
            print("Subscribed to account updates")

            # Subscribe to order updates
            order_sub = {
                "method": "subscribe",
                "params": {
                    "source": "orders",
                    "account": self.public_key
                }
            }
            await self.ws.send(json.dumps(order_sub))
            print("Subscribed to order updates")

            # Subscribe to trade updates
            trade_sub = {
                "method": "subscribe",
                "params": {
                    "source": "trades",
                    "account": self.public_key
                }
            }
            await self.ws.send(json.dumps(trade_sub))
            print("Subscribed to trade updates")

            # Wait a moment for subscription confirmations
            await asyncio.sleep(1)

        except Exception as e:
            print(f"Error subscribing to channels: {e}")
            raise

    async def handle_message(self, message: str):
        """
        Handle incoming WebSocket messages.

        Args:
            message: JSON string message from WebSocket
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type', data.get('e', ''))

            # Handle subscription confirmations
            if msg_type == 'subscribed':
                source = data.get('source', '')
                print(f"Subscription confirmed: {source}")
                return

            # Handle authentication status
            if msg_type == 'authenticated':
                print("Authentication confirmed")
                return

            # Handle order updates
            if msg_type in ['order_update', 'ORDER_TRADE_UPDATE']:
                order_data = data.get('data', data.get('o', data))
                self.monitor.print_detailed_order(order_data)

            # Handle account updates
            elif msg_type in ['account_update', 'ACCOUNT_UPDATE']:
                account_data = data.get('data', data.get('a', data))
                self.monitor.print_account_update(account_data)

            # Handle margin calls
            elif msg_type == 'MARGIN_CALL':
                print(f"\n{'='*80}")
                print("*** MARGIN CALL ALERT ***")
                print(f"{'='*80}")
                print(f"Cross Wallet Balance: {data.get('cw', 'N/A')}")
                positions = data.get('positions', data.get('p', []))
                for pos in positions:
                    symbol = pos.get('symbol', pos.get('s', 'N/A'))
                    side = pos.get('side', pos.get('ps', 'N/A'))
                    amount = pos.get('size', pos.get('pa', '0'))
                    unrealized_pnl = pos.get('unrealized_pnl', pos.get('up', '0'))
                    print(f"Position at risk: {symbol} {side} {amount} (PnL: {unrealized_pnl})")
                print(f"{'='*80}")

            # Handle connection status
            elif msg_type == 'ping':
                # Respond to ping with pong
                pong_message = {"method": "pong"}
                await self.ws.send(json.dumps(pong_message))

            elif msg_type == 'pong':
                # Pong received
                pass

            # Handle errors
            elif msg_type == 'error':
                error_msg = data.get('message', data.get('msg', 'Unknown error'))
                print(f"\nWebSocket Error: {error_msg}")

            # Handle unknown message types
            else:
                if msg_type and msg_type not in ['pong', 'heartbeat']:
                    print(f"\nUnknown message type: {msg_type}")
                    print(f"Data: {json.dumps(data, indent=2)}")

        except json.JSONDecodeError:
            print(f"Failed to parse message: {message}")
        except Exception as e:
            print(f"Error handling message: {e}")

    async def connect_and_run(self):
        """Connect to WebSocket and run the message loop with reconnection logic."""
        retry_count = 0
        max_retries = 10 if self.auto_reconnect else 1

        while not self.should_stop and retry_count < max_retries:
            try:
                print(f"\nConnecting to {self.ws_url}...")

                async with websockets.connect(
                    self.ws_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10
                ) as websocket:
                    self.ws = websocket
                    self.is_connected = True
                    retry_count = 0  # Reset retry count on successful connection

                    print("WebSocket connected!")

                    # Authenticate
                    if not await self.authenticate():
                        print("Failed to authenticate, reconnecting...")
                        self.is_connected = False
                        await asyncio.sleep(self.reconnect_delay)
                        continue

                    # Subscribe to channels
                    await self.subscribe_to_channels()

                    print("\n" + "="*80)
                    print("MONITORING STARTED - Listening for order and account updates...")
                    print("Press Ctrl+C to stop")
                    print("="*80 + "\n")

                    # Message receive loop
                    while not self.should_stop:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=60)
                            await self.handle_message(message)

                        except asyncio.TimeoutError:
                            # No message received in timeout period - send ping
                            try:
                                ping_msg = {"method": "ping"}
                                await websocket.send(json.dumps(ping_msg))
                            except Exception:
                                print("Failed to send ping, connection may be lost")
                                break
                            continue

                        except websockets.exceptions.ConnectionClosed:
                            print("\nWebSocket connection closed")
                            break

            except websockets.exceptions.WebSocketException as e:
                print(f"\nWebSocket error: {e}")

            except Exception as e:
                print(f"\nUnexpected error: {e}")

            finally:
                self.is_connected = False
                self.ws = None

            # Reconnection logic
            if not self.should_stop and self.auto_reconnect:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"\nReconnecting in {self.reconnect_delay} seconds... (Attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    print(f"\nMax reconnection attempts ({max_retries}) reached")
                    break
            else:
                break

        print("\nWebSocket connection terminated")

    async def stop(self):
        """Stop the WebSocket client."""
        self.should_stop = True
        if self.ws and self.is_connected:
            await self.ws.close()


async def monitor_orders(duration: int = 0):
    """
    Monitor orders and account updates for a specified duration.

    Args:
        duration: Duration in seconds (0 = indefinite)
    """
    print("=== PACIFICA FINANCE ORDER MONITOR ===")

    # Get private key from environment
    private_key = os.getenv('PRIVATE_KEY')

    if not private_key:
        print("ERROR: Missing PRIVATE_KEY environment variable")
        print("Please set PRIVATE_KEY in your .env file")
        return

    monitor = OrderStreamMonitor()
    ws_client = PacificaWebSocketClient(
        private_key=private_key,
        monitor=monitor,
        auto_reconnect=True,
        reconnect_delay=5
    )

    if duration > 0:
        print(f"\nMonitoring for {duration} seconds...")
    else:
        print("\nMonitoring indefinitely (press Ctrl+C to stop)...")

    try:
        # Run WebSocket client with optional timeout
        if duration > 0:
            await asyncio.wait_for(
                ws_client.connect_and_run(),
                timeout=duration
            )
        else:
            await ws_client.connect_and_run()

    except asyncio.TimeoutError:
        print(f"\n\nMonitoring duration ({duration}s) completed")

    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user")

    finally:
        await ws_client.stop()

        # Show final statistics
        monitor.print_statistics()

        print("\n=== MONITORING COMPLETED ===")
        print("\nNext steps:")
        print("- Integrate with your trading bot for real-time order tracking")
        print("- Set up alerts for specific order states or PnL thresholds")
        print("- Use this for monitoring market maker order fills")


async def extended_demo():
    """Extended demo with detailed monitoring (2 minutes)."""
    await monitor_orders(duration=120)


async def continuous_monitor():
    """Continuous monitoring until interrupted."""
    await monitor_orders(duration=0)


if __name__ == "__main__":
    import sys

    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--continuous':
            print("Starting continuous monitoring mode...")
            asyncio.run(continuous_monitor())
        elif sys.argv[1] == '--demo':
            print("Starting 2-minute demo mode...")
            asyncio.run(extended_demo())
        elif sys.argv[1].isdigit():
            duration = int(sys.argv[1])
            print(f"Starting monitoring for {duration} seconds...")
            asyncio.run(monitor_orders(duration=duration))
        else:
            print("Usage:")
            print("  python websocket_orders.py              # 2-minute demo")
            print("  python websocket_orders.py --continuous # Monitor until stopped")
            print("  python websocket_orders.py --demo       # 2-minute demo")
            print("  python websocket_orders.py <seconds>    # Monitor for N seconds")
    else:
        # Default: 2-minute demo
        asyncio.run(extended_demo())