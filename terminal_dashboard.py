#!/usr/bin/env python3
"""Unified terminal dashboard for balances, positions, orders, and mark prices for Pacifica."""

import argparse
import asyncio
import json
import logging
import os
import sys
import signal
import time
import shutil
from contextlib import suppress
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional
from urllib.parse import urlencode

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosedOK
from dotenv import load_dotenv

from api_client import ApiClient

STABLE_ASSETS = ("USDC", "USDT")
MAX_ORDER_EVENTS = 4
REST_REFRESH_INTERVAL = 15
MARK_STREAM_RETRY = 3
REALIZED_PNL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "realized_pnl.json")
REALIZED_PNL_HISTORY_LIMIT = 2

ACTIVE_ORDER_STATUSES = {"NEW", "PARTIALLY_FILLED", "PENDING_NEW", "ACCEPTED", "PENDING_CANCEL", "WORKING", "OPEN"}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"

USE_COLOR = os.getenv("NO_COLOR") is None

def enable_ansi_windows():
    """Enables ANSI escape sequences in the Windows terminal."""
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Set console mode to include ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except (ctypes.ArgumentError, OSError, AttributeError):
            pass

def get_terminal_size():
    """Get terminal size, with fallback defaults."""
    try:
        size = shutil.get_terminal_size(fallback=(120, 40))
        return size.columns, size.lines
    except Exception:
        return 120, 40

def colorize(text: str, color: str) -> str:
    return f"{color}{text}{RESET}" if USE_COLOR else text


def to_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _decimal(value: Optional[str]) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _format_decimal(value: Optional[Decimal], precision: int = 4) -> str:
    if value is None:
        return "--"
    try:
        normalized = float(value)
    except (ValueError, TypeError):
        return "--"
    return f"{normalized:,.{precision}f}"


class TerminalDashboard:
    """Maintains shared state for the combined account/order/price dashboard."""

    def __init__(
        self,
        private_key: str,
        stop_event: asyncio.Event,
        refresh_interval: int = REST_REFRESH_INTERVAL,
    ) -> None:
        self.private_key = private_key
        self.stop_event = stop_event
        self.refresh_interval = refresh_interval

        self.balances: Dict[str, Dict[str, str]] = {
            asset: {"wallet_balance": "0", "available_balance": "0"}
            for asset in STABLE_ASSETS
        }
        self.positions: Dict[str, Dict[str, float]] = {}
        self.active_orders: Dict[str, Dict[str, object]] = {}
        self.order_mid_snapshots: Dict[str, Dict[str, object]] = {}
        self.order_events = []
        self.mark_prices: Dict[str, Dict[str, float]] = {}
        self.realized_pnl_total = 0.0
        self.realized_pnl_history: list[Dict[str, object]] = []
        self._last_persisted_pnl = 0.0

        self.account_update_count = 0
        self.order_update_count = 0
        self.trade_count = 0
        self.last_reason = "INIT"
        self.last_event_time = "--"
        self.margin_alerts = []

        self.start_time = datetime.now()
        self.latest_snapshot_time: Optional[datetime] = None

        self.mark_symbols = set()
        self.mark_stream_event = asyncio.Event()
        self.mark_stream_event.set()
        self._first_render = True
        self._last_book_render = 0.0
        self._book_render_interval = 0.3

        self._load_realized_pnl()

    def _track_symbol(self, symbol: str) -> None:
        symbol = symbol.upper()
        if symbol and symbol not in self.mark_symbols:
            self.mark_symbols.add(symbol)
            self.mark_stream_event.set()

    @staticmethod
    def _summarize_exception(exc: Exception) -> str:
        if isinstance(exc, aiohttp.ClientResponseError):
            status = exc.status
            message = exc.message or exc.__class__.__name__
            return f"HTTP {status} {message}" if status else message
        if isinstance(exc, aiohttp.ClientConnectionError):
            return "Connection error"
        if isinstance(exc, asyncio.TimeoutError):
            return "Timeout"
        return exc.__class__.__name__

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------
    def ensure_stable(self) -> None:
        for asset in STABLE_ASSETS:
            self.balances.setdefault(
                asset,
                {"wallet_balance": "0", "available_balance": "0"},
            )

    def _refresh_mark_symbols(self) -> None:
        position_symbols = {
            symbol for symbol, pos in self.positions.items()
            if isinstance(pos, dict) and pos.get("amount")
        }
        active_symbols = {
            info.get("symbol", "").upper()
            for info in self.active_orders.values()
            if isinstance(info, dict) and info.get("symbol")
        }
        snapshot_symbols = {sym.upper() for sym in self.order_mid_snapshots.keys() if sym}
        symbols = (
            {sym for sym in position_symbols if sym}
            | {sym for sym in active_symbols if sym}
            | snapshot_symbols
        )
        if symbols != self.mark_symbols:
            self.mark_symbols = symbols
            self.mark_stream_event.set()
        self._first_render = True

    @staticmethod
    def _order_keys(order: Dict[str, object]) -> list[str]:
        keys: list[str] = []
        order_id = order.get("order_id") or order.get("orderId")
        client_id = order.get("client_order_id") or order.get("clientOrderId")
        if order_id not in (None, ""):
            keys.append(f"id:{order_id}")
        if client_id not in (None, ""):
            keys.append(f"client:{client_id}")
        return keys

    def _record_order_mid_snapshot(self, data: Dict[str, object]) -> None:
        symbol = (data.get("symbol") or "").upper()
        if not symbol:
            return
        recorded_at = time.monotonic()
        snapshot = self.order_mid_snapshots.get(symbol, {}).copy()
        snapshot.update(
            {
                "symbol": symbol,
                "time": data.get("time") or snapshot.get("time") or datetime.now().strftime("%H:%M:%S"),
                "status": data.get("status") or snapshot.get("status"),
                "recorded_at": recorded_at,
            }
        )
        self.order_mid_snapshots[symbol] = snapshot
        self._track_symbol(symbol)

    def _load_realized_pnl(self) -> None:
        if not os.path.isfile(REALIZED_PNL_FILE):
            self._last_persisted_pnl = self.realized_pnl_total
            return
        try:
            with open(REALIZED_PNL_FILE, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            total_value = payload.get("total", 0.0)
            try:
                parsed_total = float(total_value)
            except (TypeError, ValueError):
                parsed_total = 0.0
            if abs(parsed_total) > 1e-9:
                self.realized_pnl_total = parsed_total
        except (OSError, json.JSONDecodeError) as exc:
            logging.getLogger("TerminalDashboard").warning(f"Failed to load realized PnL file: {exc}")
        finally:
            self._last_persisted_pnl = self.realized_pnl_total

    def _persist_realized_pnl(self) -> None:
        if abs(self.realized_pnl_total - self._last_persisted_pnl) < 1e-9:
            return
        payload = {"total": round(self.realized_pnl_total, 10)}
        try:
            with open(REALIZED_PNL_FILE, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            self._last_persisted_pnl = self.realized_pnl_total
        except OSError as exc:
            logging.getLogger("TerminalDashboard").warning(f"Failed to persist realized PnL: {exc}")

    def _record_realized_pnl(self, entry: Dict[str, object]) -> None:
        pnl_delta = to_float(entry.get("realized_pnl"))
        if abs(pnl_delta) < 1e-9:
            return
        self.realized_pnl_total += pnl_delta
        record = {
            "time": entry.get("time", "--"),
            "symbol": entry.get("symbol", "N/A"),
            "side": entry.get("side", "N/A"),
            "pnl": pnl_delta,
        }
        self.realized_pnl_history.insert(0, record)
        del self.realized_pnl_history[REALIZED_PNL_HISTORY_LIMIT:]
        self._persist_realized_pnl()

    def _update_active_orders(self, order: Dict[str, object], data: Dict[str, object]) -> None:
        status = data.get("status")
        self._record_order_mid_snapshot(data)
        keys = set(self._order_keys(order))
        if not keys:
            return

        if status in ACTIVE_ORDER_STATUSES:
            existing = None
            for key in keys:
                existing = self.active_orders.get(key)
                if existing:
                    break
            if existing is None:
                existing = {"keys": set()}
            existing_keys = set(existing.get("keys", set()))
            merged_keys = existing_keys | keys
            existing.update(data)
            existing["keys"] = merged_keys
            for key in merged_keys:
                self.active_orders[key] = existing
            return

        # Order no longer active; remove any aliases for it.
        existing = None
        for key in keys:
            existing = self.active_orders.get(key)
            if existing:
                break
        if not existing:
            return
        aliases = set(existing.get("keys", set())) or keys
        for key in aliases:
            self.active_orders.pop(key, None)

    def _recalc_unrealized(self, symbol: str) -> None:
        symbol = symbol.upper()
        pos = self.positions.get(symbol)
        if not pos:
            return
        mark_info = self.mark_prices.get(symbol)
        mark_price = mark_info.get("mark") if mark_info else None
        if mark_price is None:
            return
        entry_price = pos.get("entry")
        if entry_price is None:
            return
        amount = pos.get("amount", 0.0)
        pos["unrealized"] = (mark_price - entry_price) * amount

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------
    def update_from_snapshot(self, data: Dict[str, object]) -> None:
        # Update balances from account info
        account_data = data.get("account", {})

        # Handle balance info
        balance_info = account_data.get("balance", {})
        for asset in STABLE_ASSETS:
            asset_balance = balance_info.get(asset, {})
            if isinstance(asset_balance, dict):
                self.balances[asset] = {
                    "wallet_balance": str(asset_balance.get("total", "0")),
                    "available_balance": str(asset_balance.get("available", "0")),
                }
            else:
                # Handle case where balance might be a simple value
                self.balances[asset] = {
                    "wallet_balance": str(asset_balance),
                    "available_balance": str(asset_balance),
                }

        # Update positions
        self.positions.clear()
        positions_data = data.get("positions", [])
        if isinstance(positions_data, list):
            for position in positions_data:
                amount = to_float(position.get("amount") or position.get("size"))
                if amount == 0:
                    continue
                symbol = position.get("symbol", "N/A").upper()
                unrealized = to_float(position.get("unrealized_pnl") or position.get("pnl"))
                self.positions[symbol] = {
                    "amount": amount,
                    "entry": to_float(position.get("entry_price") or position.get("average_price")),
                    "unrealized": unrealized,
                    "side": "LONG" if amount > 0 else "SHORT",
                }
                self._recalc_unrealized(symbol)

        self.ensure_stable()
        self.latest_snapshot_time = datetime.now()
        self.margin_alerts.clear()
        self.last_reason = "REST SNAPSHOT"
        self._refresh_mark_symbols()

    def handle_account_update(self, payload: Dict[str, object], event_time: int = 0) -> None:
        self.last_reason = "ACCOUNT_UPDATE"
        self.account_update_count += 1
        timestamp = (
            datetime.fromtimestamp(event_time / 1000).strftime("%H:%M:%S.%f")[:-3] if event_time else "--"
        )
        self.last_event_time = timestamp

        # Update balances from websocket event
        balances = payload.get("balances", {})
        for asset in STABLE_ASSETS:
            if asset in balances:
                balance_data = balances[asset]
                if isinstance(balance_data, dict):
                    self.balances[asset] = {
                        "wallet_balance": str(balance_data.get("total", "0")),
                        "available_balance": str(balance_data.get("available", "0")),
                    }

        # Update positions from websocket event
        positions = payload.get("positions", [])
        if isinstance(positions, list):
            for position in positions:
                symbol = position.get("symbol", "N/A").upper()
                amount = to_float(position.get("amount") or position.get("size"))
                if amount == 0:
                    self.positions.pop(symbol, None)
                    continue
                unrealized = to_float(position.get("unrealized_pnl") or position.get("pnl"))
                self.positions[symbol] = {
                    "amount": amount,
                    "entry": to_float(position.get("entry_price") or position.get("average_price")),
                    "unrealized": unrealized,
                    "side": "LONG" if amount > 0 else "SHORT",
                }
                self._recalc_unrealized(symbol)

        self.ensure_stable()
        self.latest_snapshot_time = datetime.now()
        self._refresh_mark_symbols()

    def handle_order_update(self, order: Dict[str, object]) -> None:
        event_time = order.get("timestamp") or order.get("update_time") or 0
        timestamp = (
            datetime.fromtimestamp(event_time / 1000).strftime("%H:%M:%S.%f")[:-3] if event_time else "--"
        )
        symbol = order.get("symbol", "N/A").upper()

        # Determine execution type
        exec_type = "NEW"
        if order.get("filled_amount", 0) > 0:
            exec_type = "TRADE"
        status = order.get("status", "N/A").upper()

        entry = {
            "time": timestamp,
            "symbol": symbol,
            "side": order.get("side", "N/A").upper(),
            "status": status,
            "exec": exec_type,
            "qty": to_float(order.get("amount") or order.get("quantity")),
            "filled": to_float(order.get("filled_amount") or order.get("filled")),
            "price": to_float(order.get("price")),
            "avg": to_float(order.get("average_price") or order.get("avg_price")),
            "last_fill_qty": to_float(order.get("last_fill_quantity", 0)),
            "last_fill_price": to_float(order.get("last_fill_price", 0)),
            "realized_pnl": to_float(order.get("realized_pnl", 0)),
            "order_id": order.get("order_id") or order.get("id"),
            "client_id": order.get("client_order_id"),
        }
        self._track_symbol(symbol)
        self.order_events.insert(0, entry)
        del self.order_events[MAX_ORDER_EVENTS:]
        self._record_realized_pnl(entry)

        active_payload = {
            "symbol": symbol,
            "side": entry["side"],
            "status": entry["status"],
            "qty": entry["qty"],
            "filled": entry["filled"],
            "price": entry["price"],
            "avg": entry["avg"],
            "type": order.get("type", "LIMIT"),
            "time": timestamp,
            "client_order_id": order.get("client_order_id"),
            "order_id": order.get("order_id") or order.get("id"),
        }
        self._update_active_orders(order, active_payload)

        self.order_update_count += 1
        if exec_type == "TRADE":
            self.trade_count += 1
        self.last_event_time = timestamp
        self._refresh_mark_symbols()

    def handle_margin_call(self, payload: Dict[str, object], event_time: int = 0) -> None:
        timestamp = (
            datetime.fromtimestamp(event_time / 1000).strftime("%H:%M:%S.%f")[:-3] if event_time else "--"
        )
        self.last_event_time = timestamp
        alerts = []
        positions = payload.get("positions", [])
        for pos in positions:
            symbol = pos.get("symbol", "N/A")
            side = pos.get("side", "N/A")
            amount = pos.get("amount", "0")
            pnl = pos.get("unrealized_pnl", "0")
            alerts.append(f"{symbol} {side} {amount} (PnL {pnl})")
        self.margin_alerts = alerts or ["Margin call event received"]
        self.last_reason = "MARGIN_CALL"

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def render(self, status: str = "WAITING") -> None:
        now = datetime.now()
        uptime = now - self.start_time
        stable_total = 0.0
        stable_lines = []
        for asset in STABLE_ASSETS:
            bal = to_float(self.balances.get(asset, {}).get("wallet_balance"))
            stable_total += bal
            stable_lines.append(f"  {asset}: {bal:,.4f} {asset}")
        other_balances = []
        for asset, info in sorted(self.balances.items()):
            if asset in STABLE_ASSETS:
                continue
            amount = to_float(info.get("wallet_balance"))
            if abs(amount) < 0.01:
                continue
            other_balances.append(f"  {asset}: {amount:,.4f} {asset}")
        total_unrealized = sum(pos.get("unrealized", 0.0) for pos in self.positions.values())
        total_equity = stable_total + total_unrealized
        snapshot = (
            self.latest_snapshot_time.strftime("%Y-%m-%d %H:%M:%S")
            if self.latest_snapshot_time
            else "--"
        )

        header = colorize("=== PACIFICA TERMINAL DASHBOARD ===", CYAN + BOLD if USE_COLOR else CYAN)
        lines: list[str] = []

        lines.append(header)
        lines.append(
            f"Snapshot: {snapshot} | Rendered: {now.strftime('%Y-%m-%d %H:%M:%S')} | Status: "
            f"{colorize(status, YELLOW if status not in {'CONNECTED', 'IDLE'} else GREEN)}"
        )
        lines.append(
            f"Uptime: {int(uptime.total_seconds() // 60)}m {int(uptime.total_seconds() % 60)}s | "
            f"Last reason: {self.last_reason}"
        )
        lines.append("")

        lines.append(colorize("Account Summary", BOLD))
        lines.append(f"  Total Stablecoins: {stable_total:,.4f} USD")
        lines.append(f"  Total Unrealized PnL: {total_unrealized:,.4f} USD")
        lines.append(f"  Total Equity: {total_equity:,.4f} USD")
        lines.append("")

        lines.append(colorize("Stablecoin Breakdown:", BOLD))
        lines.extend(stable_lines)
        lines.append(f"  Total Stablecoins: {stable_total:,.4f} USD")
        if other_balances:
            lines.append("")
            lines.append(colorize("Other Balances:", BOLD))
            lines.extend(other_balances)

        lines.append("")
        lines.append(colorize("Open Positions:", BOLD))
        if self.positions:
            header_row = (
                f"{'Symbol':<10}{'Side':<6}{'Amount':>12}{'Entry':>12}{'Mark':>12}{'Mid':>12}{'Quote':>14}{'Unreal PnL':>14}{'Funding%':>10}"
            )
            lines.append(header_row)
            for symbol, pos in sorted(self.positions.items()):
                amount = pos['amount']
                side = "LONG" if amount > 0 else "SHORT"
                mark_info = self.mark_prices.get(symbol)
                mark_display = "--"
                mid_display = '--'.rjust(12)
                funding_display = '--'.rjust(10)
                mark_val = None
                mid_val = None
                if mark_info:
                    mark_val = mark_info.get('mark')
                    if mark_val is not None:
                        mark_display = f"{mark_val:,.3f}"
                    mid_val = mark_info.get('mid')
                    if mid_val is not None:
                        mid_display = f"{mid_val:>12.3f}"
                    funding_val = mark_info.get('funding')
                    if funding_val is not None:
                        funding_plain = f"{funding_val:.4f}%".rjust(10)
                        if USE_COLOR:
                            funding_color = GREEN if funding_val >= 0 else RED
                            funding_display = colorize(funding_plain, funding_color)
                        else:
                            funding_display = funding_plain
                amount_plain = f"{amount:>12.4f}"
                pnl_value = pos.get('unrealized', 0.0)
                pnl_plain = f"{pnl_value:>14.2f}"
                entry_price = pos.get('entry')
                entry_display = f"{entry_price:>12.3f}" if entry_price is not None else '--'.rjust(12)
                quote_ref = mid_val if mid_val is not None else mark_val if mark_val is not None else entry_price
                quote_value = None
                quote_plain = '--'.rjust(14)
                if quote_ref is not None:
                    quote_value = amount * quote_ref
                    quote_plain = f"{quote_value:>14.3f}"
                if USE_COLOR:
                    amount_color = GREEN if amount >= 0 else RED
                    amount_text = colorize(amount_plain, amount_color)
                    side_color = GREEN if amount > 0 else RED
                    side_cell = colorize(f"{side:<6}", side_color)
                    quote_text = colorize(quote_plain, GREEN if quote_value is not None and quote_value >= 0 else RED) if quote_value is not None else quote_plain
                    pnl_color = GREEN if pnl_value >= 0 else RED
                    pnl_text = colorize(pnl_plain, pnl_color)
                else:
                    amount_text = amount_plain
                    side_cell = f"{side:<6}"
                    quote_text = quote_plain
                    pnl_text = pnl_plain
                mark_cell = f"{mark_display:>12}"
                lines.append(
                    f"{symbol:<10}{side_cell}{amount_text}{entry_display}"
                    f"{mark_cell}{mid_display}{quote_text}{pnl_text} {funding_display}"
                )
        else:
            lines.append(colorize('  None', DIM))

        lines.append("")
        lines.append(colorize("Active Order Mid Prices:", BOLD))
        mid_entries = list(self.order_mid_snapshots.values())
        if mid_entries:
            mid_entries.sort(key=lambda item: item.get("recorded_at", 0), reverse=True)
            for snapshot in mid_entries:
                symbol = snapshot.get("symbol", "N/A")
                mark_info = self.mark_prices.get(symbol, {})
                mid_value = None
                if isinstance(mark_info, dict):
                    mid_value = mark_info.get("mid")
                    if mid_value in (None, 0):
                        mid_value = mark_info.get("mark")
                mid_display = "--"
                if mid_value not in (None, 0):
                    mid_display = f"{mid_value:.3f}"
                lines.append(f"  {symbol:<10} mid {mid_display:>10}")
        else:
            lines.append(colorize("  None", DIM))

        lines.append("")
        lines.append(colorize("Realized Trade PnL:", BOLD))
        total_line = f"  Total: {self.realized_pnl_total:+.4f} USD"
        if USE_COLOR:
            total_color = GREEN if self.realized_pnl_total >= 0 else RED
            total_line = colorize(total_line, total_color)
        lines.append(total_line)
        if self.realized_pnl_history:
            for record in self.realized_pnl_history:
                pnl_value = record.get("pnl", 0.0)
                line = f"  {record.get('time', '--'):<8} {record.get('symbol', 'N/A'):<10} {pnl_value:+.4f} USD"
                if USE_COLOR:
                    pnl_color = GREEN if pnl_value >= 0 else RED
                    line = colorize(line, pnl_color)
                lines.append(line)
        else:
            lines.append(colorize("  No realized trades yet.", DIM))

        lines.append("")
        lines.append(colorize("Recent Orders:", BOLD))
        display_events = list(self.order_events[:MAX_ORDER_EVENTS])
        while len(display_events) < MAX_ORDER_EVENTS:
            display_events.append(None)
        for entry in display_events:
            if entry:
                qty = entry["qty"]
                filled = entry["filled"]
                progress = f"{filled:.4f}/{qty:.4f}" if qty else f"{filled:.4f}"
                avg_price = f"{entry['avg']:.3f}" if entry["avg"] else '0.000'
                realized = entry["realized_pnl"]
                if abs(realized) < 1e-9:
                    pnl_label = "0.00 USD"
                else:
                    pnl_label = f"{realized:+.4f} USD"
                    if USE_COLOR:
                        pnl_color = GREEN if realized >= 0 else RED
                        pnl_label = colorize(pnl_label, pnl_color)
                time_str = entry['time']
                symbol = entry['symbol']
                side_str = entry['side']
                status_str = entry['status']
                exec_type = entry['exec']
                progress_str = progress
                avg_str = avg_price
                price_value = entry['price']
                price_str = f"{price_value:.3f}" if price_value else '0.000'
                pct_str = '--'
                mark_info = self.mark_prices.get(symbol)
                ref_price = None
                mark_str = '--'
                if isinstance(mark_info, dict):
                    mark_val = mark_info.get('mark')
                    if mark_val not in (None, 0):
                        ref_price = mark_val
                        mark_str = f"{mark_val:.3f}"
                if price_value and ref_price and ref_price != 0:
                    pct = (price_value - ref_price) / ref_price * 100
                    pct_str = f"{pct:+.2f}%"
                    if USE_COLOR:
                        pct_color = GREEN if pct <= 0 else RED
                        pct_str = colorize(pct_str, pct_color)
                pnl_str = pnl_label
                order_id = entry.get("order_id")
                client_id = entry.get("client_id")
                order_label = str(order_id) if order_id not in (None, "") else "--"
                client_label = str(client_id) if client_id not in (None, "") else "--"
                if order_label != "--":
                    order_label = f"#{order_label}"
                lines.append(
                    f"  {time_str:<8} {symbol:<10} {order_label:<13} {side_str:<5} {status_str:<13} ({exec_type:<8}) "
                    f"qty {progress_str:<18} avg {avg_str:>7} limit {price_str:>8} mark {mark_str:>8} dev {pct_str:<9} pnl {pnl_str:<12} cid {client_label:<12}"
                )
            else:
                lines.append(colorize("  -- waiting for order activity --", DIM))

        lines.append("")
        lines.append(colorize("Alerts:", BOLD))
        if self.margin_alerts:
            for note in self.margin_alerts[-3:]:
                lines.append(colorize(f"  ! {note}", RED))
        else:
            lines.append(colorize("  None", DIM))

        lines.append("")
        lines.append(colorize("Stats:", BOLD))
        lines.append(
            f"  Account updates: {self.account_update_count} | Order updates: {self.order_update_count} | Trades: {self.trade_count}"
        )
        lines.append(f"  Last event time: {self.last_event_time}")
        lines.append("")
        lines.append(colorize("Press Ctrl+C to exit.", DIM))

        # Use an alternate screen buffer to completely prevent scrolling
        buffer = []

        # Hide cursor before any writes
        buffer.append("\033[?25l")

        if self._first_render:
            # Switch to alternate screen buffer and clear it
            buffer.append("\033[?1049h")  # Enable alternate screen
            buffer.append("\033[2J")      # Clear screen
            buffer.append("\033[H")       # Move to home
            self._first_render = False
        else:
            # Just move to home position
            buffer.append("\033[H")

        # Write the content line by line
        for line in lines:
            buffer.append(line)
            buffer.append("\033[K")  # Clear to end of line
            buffer.append("\n")

        # Clear from cursor to end of screen
        buffer.append("\033[J")

        # Show cursor after rendering
        buffer.append("\033[?25h")

        # Single atomic write to stdout
        sys.stdout.write("".join(buffer))
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Background tasks
    # ------------------------------------------------------------------
    async def periodic_refresh(self) -> None:
        while not self.stop_event.is_set():
            try:
                async with ApiClient(self.private_key, release_mode=True) as client:
                    # Get account info with positions
                    account_info = await client.get_account_info()
                    # Get positions
                    positions = await client.get_positions()

                    snapshot = {
                        "account": account_info,
                        "positions": positions.get("positions", [])
                    }
                self.update_from_snapshot(snapshot)
                self.render("REST REFRESH")
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as exc:
                summary = self._summarize_exception(exc)
                logging.getLogger("TerminalDashboard").warning("Refresh error: %s", exc)
                self.last_reason = f"Refresh error ({summary})"
                self.render("REFRESH ERROR")
            except Exception as exc:
                logging.getLogger("TerminalDashboard").error("Unexpected refresh error: %s", exc, exc_info=True)
                self.last_reason = f"Refresh error ({self._summarize_exception(exc)})"
                self.render("REFRESH ERROR")
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.refresh_interval)
            except asyncio.TimeoutError:
                continue
        self.last_reason = "Refresh stopped"

    async def mark_price_listener(self) -> None:
        """Listen to mark prices and funding rates via WebSocket."""
        while not self.stop_event.is_set():
            await self.mark_stream_event.wait()
            self.mark_stream_event.clear()
            if self.stop_event.is_set():
                break
            symbols = sorted(self.mark_symbols)
            if not symbols:
                self.mark_prices.clear()
                continue

            # Connect to Pacifica WebSocket for price updates
            ws_url = "wss://ws.pacifica.fi/ws"
            try:
                async with websockets.connect(ws_url) as ws:
                    # Subscribe to mark prices and book tickers for all symbols
                    subscribe_msg = {
                        "type": "subscribe",
                        "channels": []
                    }
                    for symbol in symbols:
                        subscribe_msg["channels"].append(f"ticker.{symbol}")
                        subscribe_msg["channels"].append(f"orderbook.{symbol}")

                    await ws.send(json.dumps(subscribe_msg))

                    self.last_reason = "MARK STREAM"
                    self.render("MARK STREAM")

                    while not self.stop_event.is_set():
                        recv_task = asyncio.create_task(ws.recv())
                        change_task = asyncio.create_task(self.mark_stream_event.wait())
                        stop_task = asyncio.create_task(self.stop_event.wait())
                        done, pending = await asyncio.wait(
                            {recv_task, change_task, stop_task},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for task in pending:
                            if not task.done():
                                task.cancel()
                            with suppress(asyncio.CancelledError):
                                await task
                        if stop_task in done:
                            with suppress(Exception):
                                stop_task.result()
                            break
                        if change_task in done:
                            with suppress(Exception):
                                change_task.result()
                            break
                        message = recv_task.result()
                        data = json.loads(message)

                        # Handle ticker updates
                        if data.get("channel", "").startswith("ticker."):
                            symbol = data.get("symbol", "").upper()
                            if not symbol:
                                continue
                            ticker_data = data.get("data", {})
                            info = self.mark_prices.setdefault(symbol, {})
                            info.update({
                                "mark": to_float(ticker_data.get("mark_price") or ticker_data.get("last_price")),
                                "index": to_float(ticker_data.get("index_price")),
                                "funding": to_float(ticker_data.get("funding_rate")) * 100,
                                "time": ticker_data.get("timestamp"),
                            })
                            self._recalc_unrealized(symbol)
                            self.render("MARK PRICE")
                            continue

                        # Handle orderbook updates
                        if data.get("channel", "").startswith("orderbook."):
                            symbol = data.get("symbol", "").upper()
                            if not symbol:
                                continue
                            book_data = data.get("data", {})
                            bids = book_data.get("bids", [])
                            asks = book_data.get("asks", [])

                            info = self.mark_prices.setdefault(symbol, {})
                            updated = False

                            if bids and len(bids) > 0:
                                bid = to_float(bids[0][0]) if isinstance(bids[0], list) else to_float(bids[0].get("price"))
                                if bid > 0:
                                    info["bid"] = bid
                                    updated = True

                            if asks and len(asks) > 0:
                                ask = to_float(asks[0][0]) if isinstance(asks[0], list) else to_float(asks[0].get("price"))
                                if ask > 0:
                                    info["ask"] = ask
                                    updated = True

                            bid = info.get("bid", 0)
                            ask = info.get("ask", 0)
                            mid = None
                            if bid > 0 and ask > 0:
                                mid = (bid + ask) / 2
                            elif ask > 0:
                                mid = ask
                            elif bid > 0:
                                mid = bid
                            if mid is not None:
                                info["mid"] = mid
                                updated = True

                            if updated:
                                info["book_time"] = book_data.get("timestamp")
                                now = time.monotonic()
                                if now - self._last_book_render >= self._book_render_interval:
                                    self._last_book_render = now
                                    self.render("BOOK TICKER")
            except ConnectionClosedOK:
                self.last_reason = "Mark stream closed"
                self.render("MARK STREAM CLOSED")
                await asyncio.sleep(MARK_STREAM_RETRY)
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, json.JSONDecodeError, websockets.WebSocketException) as exc:
                summary = self._summarize_exception(exc)
                logging.getLogger("TerminalDashboard").warning("Mark stream error: %s", exc)
                self.last_reason = f"Mark stream error ({summary})"
                self.render("MARK STREAM ERROR")
                await asyncio.sleep(MARK_STREAM_RETRY)
            except Exception as exc:
                logging.getLogger("TerminalDashboard").error("Unexpected mark stream error: %s", exc, exc_info=True)
                self.last_reason = f"Mark stream error ({self._summarize_exception(exc)})"
                self.render("MARK STREAM ERROR")
                await asyncio.sleep(MARK_STREAM_RETRY)
        self.last_reason = "Mark stream stopped"

    async def stream(self, ws_url: str) -> None:
        """Stream account and order updates via WebSocket."""
        try:
            async with websockets.connect(ws_url) as ws:
                self.render("CONNECTED")
                while not self.stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=3)
                    except asyncio.TimeoutError:
                        self.render("IDLE")
                        continue
                    except ConnectionClosedOK:
                        self.last_reason = "User stream closed"
                        self.render("CONNECTION CLOSED")
                        break
                    data = json.loads(message)
                    event_type = data.get("type", "unknown")

                    if event_type == "account":
                        self.handle_account_update(data.get("data", {}), data.get("timestamp", 0))
                        self.render("ACCOUNT UPDATE")
                    elif event_type == "order":
                        self.handle_order_update(data.get("data", {}))
                        self.render("ORDER EVENT")
                    elif event_type == "position":
                        # Handle position updates
                        position_data = data.get("data", {})
                        self.handle_account_update({"positions": [position_data]}, data.get("timestamp", 0))
                        self.render("POSITION UPDATE")
                    elif event_type == "margin_call":
                        self.handle_margin_call(data.get("data", {}), data.get("timestamp", 0))
                        self.render("MARGIN CALL")
                    else:
                        self.last_reason = f"Unhandled {event_type}"
                        self.render("UNHANDLED EVENT")
        except ConnectionClosedOK:
            self.last_reason = "Stream closed"
            self.render("CONNECTION CLOSED")
        except asyncio.CancelledError:
            raise
        except (aiohttp.ClientError, json.JSONDecodeError, websockets.WebSocketException) as exc:
            if not self.stop_event.is_set():
                summary = self._summarize_exception(exc)
                logging.getLogger("TerminalDashboard").warning("Stream error: %s", exc)
                self.last_reason = f"Stream error ({summary})"
                self.render("STREAM ERROR")
        except Exception as exc:
            if not self.stop_event.is_set():
                logging.getLogger("TerminalDashboard").error("Unexpected stream error: %s", exc, exc_info=True)
                self.last_reason = f"Stream error ({self._summarize_exception(exc)})"
                self.render("STREAM ERROR")


async def run_dashboard(args: argparse.Namespace) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _handle_signal(signum, frame):  # noqa: ARG001
        if not stop_event.is_set():
            loop.call_soon_threadsafe(stop_event.set)

    for sig in (signal.SIGINT, getattr(signal, "SIGTERM", signal.SIGINT)):
        try:
            signal.signal(sig, _handle_signal)
        except (ValueError, OSError):
            pass

    load_dotenv()

    private_key = os.getenv("PRIVATE_KEY")

    if not private_key:
        print("ERROR: Missing required environment variable")
        print("Required: PRIVATE_KEY")
        return

    dashboard = TerminalDashboard(
        private_key,
        stop_event,
        refresh_interval=args.refresh_interval,
    )

    # Get initial snapshot
    async with ApiClient(private_key, release_mode=True) as client:
        account_info = await client.get_account_info()
        positions = await client.get_positions()
        snapshot = {
            "account": account_info,
            "positions": positions.get("positions", [])
        }
        dashboard.update_from_snapshot(snapshot)

    # Set up WebSocket URL for private user stream
    # Note: Pacifica may require authentication for private streams
    ws_url = "wss://ws.pacifica.fi/ws"

    refresh_task = asyncio.create_task(dashboard.periodic_refresh())
    mark_task = asyncio.create_task(dashboard.mark_price_listener())
    stream_task = asyncio.create_task(dashboard.stream(ws_url))

    tasks = {refresh_task, mark_task, stream_task}
    if args.duration > 0:
        duration_task = asyncio.create_task(asyncio.sleep(args.duration))
        tasks.add(duration_task)
    else:
        duration_task = None

    signal_task = asyncio.create_task(stop_event.wait())
    tasks.add(signal_task)

    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    if duration_task and duration_task in done:
        dashboard.render("TIMEOUT")
        print(f"\nReached duration limit ({args.duration}s); exiting.")

    stop_event.set()
    dashboard.mark_stream_event.set()

    for task in tasks:
        if not task.done():
            task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live account/order dashboard for Pacifica")
    parser.add_argument(
        "--duration",
        type=int,
        default=360000,
        help="Seconds to run before auto exit (<=0 to run until interrupted)",
    )
    parser.add_argument(
        "--refresh-interval",
        type=int,
        default=REST_REFRESH_INTERVAL,
        help="Seconds between REST account refresh calls",
    )
    return parser.parse_args()


def main() -> None:
    enable_ansi_windows()
    args = parse_args()
    try:
        asyncio.run(run_dashboard(args))
    finally:
        # Restore normal screen buffer and show cursor
        sys.stdout.write("\033[?1049l")  # Disable alternate screen
        sys.stdout.write("\033[?25h")    # Show cursor
        sys.stdout.flush()


if __name__ == "__main__":
    main()