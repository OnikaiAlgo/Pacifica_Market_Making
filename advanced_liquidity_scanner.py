"""
Advanced Liquidity Scanner for Pacifica.fi Markets

Deep analysis of market microstructure for optimal market making:
- Real orderbook depth & spread analysis
- Trade frequency & fill probability
- Adverse selection risk
- Competition detection
- Inventory turnover estimation

Usage:
    python advanced_liquidity_scanner.py [--duration MINUTES] [--markets SYMBOLS]
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import deque, defaultdict
import statistics

import websockets
from dotenv import load_dotenv
import os

# Add pacifica_sdk to path
sys.path.insert(0, str(Path(__file__).parent / "pacifica_sdk"))
from common.constants import WS_URL

# Load environment
load_dotenv()

# Rich terminal output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.layout import Layout
    from rich.live import Live
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for beautiful output: pip install rich")


# Priority markets to analyze
PRIORITY_MARKETS = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'AVAX',
    'LINK', 'UNI', 'AAVE', 'kPEPE', 'PEPE', 'BONK',
    'ARB', 'OP', 'SUI', 'APT', 'INJ', 'TIA', 'SEI'
]


@dataclass
class OrderbookSnapshot:
    """Single orderbook snapshot"""
    timestamp: float
    bids: List[Tuple[float, float]]  # (price, size)
    asks: List[Tuple[float, float]]
    mid_price: float
    spread_bps: float


@dataclass
class TradeEvent:
    """Single trade event"""
    timestamp: float
    price: float
    size: float
    side: str  # 'buy' or 'sell'


@dataclass
class MarketMicrostructure:
    """Detailed market microstructure analysis"""
    symbol: str

    # Orderbook metrics
    avg_spread_bps: float
    min_spread_bps: float
    max_spread_bps: float
    spread_volatility: float

    bid_depth_1pct: float  # Total liquidity within 1%
    ask_depth_1pct: float
    avg_imbalance: float  # Bid/ask imbalance ratio

    # Trade metrics
    trades_per_hour: float
    avg_trade_size: float
    median_trade_size: float
    buy_pressure: float  # % of buy trades

    # Fill probability (estimated)
    fill_prob_5bps: float  # Probability to fill at 5bps from mid
    fill_prob_10bps: float
    fill_prob_20bps: float

    # Volatility
    price_volatility_pct: float  # Hourly volatility
    quote_stability: float  # How stable are quotes

    # Competition
    quote_updates_per_min: float  # High = lots of bot activity
    competition_score: float  # 0-100, higher = more competition

    # Risk metrics
    adverse_selection_risk: float  # 0-100, higher = worse
    inventory_half_life_min: float  # Time to exit 50% of position

    # Overall scores
    liquidity_score: float
    mm_score: float
    profitability_score: float

    # Recommendations
    recommended_spread_bps: Tuple[float, float]  # (min, max)
    max_position_size_usd: float
    estimated_daily_fills: int
    estimated_daily_pnl_usd: float

    # Warnings
    warnings: List[str] = field(default_factory=list)

    # Raw data
    data_points: int = 0
    collection_duration_sec: float = 0


class AdvancedMarketAnalyzer:
    """Analyzes a single market in depth"""

    def __init__(self, symbol: str):
        self.symbol = symbol

        # Data buffers
        self.orderbook_snapshots: deque = deque(maxlen=1000)
        self.trades: deque = deque(maxlen=1000)
        self.price_updates: deque = deque(maxlen=500)

        # Timestamps
        self.start_time = time.time()
        self.last_orderbook_update = 0
        self.orderbook_update_count = 0

    def process_orderbook(self, orderbook_data: dict):
        """Process orderbook update"""
        try:
            bids = [(float(b['price']), float(b['size'])) for b in orderbook_data.get('bids', [])[:20]]
            asks = [(float(a['price']), float(a['size'])) for a in orderbook_data.get('asks', [])[:20]]

            if not bids or not asks:
                return

            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2
            spread_bps = ((best_ask - best_bid) / mid_price) * 10000

            snapshot = OrderbookSnapshot(
                timestamp=time.time(),
                bids=bids,
                asks=asks,
                mid_price=mid_price,
                spread_bps=spread_bps
            )

            self.orderbook_snapshots.append(snapshot)
            self.orderbook_update_count += 1
            self.last_orderbook_update = time.time()

        except Exception as e:
            pass

    def process_trade(self, trade_data: dict):
        """Process trade event"""
        try:
            trade = TradeEvent(
                timestamp=time.time(),
                price=float(trade_data.get('price', 0)),
                size=float(trade_data.get('size', 0)),
                side=trade_data.get('side', 'buy')
            )
            self.trades.append(trade)
        except Exception as e:
            pass

    def process_price_update(self, price_data: dict):
        """Process price update"""
        try:
            mid = price_data.get('mid')
            if mid:
                self.price_updates.append((time.time(), float(mid)))
        except Exception as e:
            pass

    def calculate_orderbook_depth(self, snapshot: OrderbookSnapshot, pct: float) -> Tuple[float, float]:
        """Calculate bid/ask depth within pct% of mid"""
        threshold_low = snapshot.mid_price * (1 - pct / 100)
        threshold_high = snapshot.mid_price * (1 + pct / 100)

        bid_depth = sum(size * price for price, size in snapshot.bids if price >= threshold_low)
        ask_depth = sum(size * price for price, size in snapshot.asks if price <= threshold_high)

        return bid_depth, ask_depth

    def analyze(self) -> MarketMicrostructure:
        """Perform deep analysis"""
        duration = time.time() - self.start_time

        if not self.orderbook_snapshots or len(self.orderbook_snapshots) < 10:
            # Not enough data
            return self._create_empty_result(duration)

        # Orderbook analysis
        spreads = [s.spread_bps for s in self.orderbook_snapshots]
        avg_spread = statistics.mean(spreads)
        min_spread = min(spreads)
        max_spread = max(spreads)
        spread_volatility = statistics.stdev(spreads) if len(spreads) > 1 else 0

        # Depth analysis
        bid_depths = []
        ask_depths = []
        imbalances = []

        for snapshot in self.orderbook_snapshots:
            bid_depth, ask_depth = self.calculate_orderbook_depth(snapshot, 1.0)
            bid_depths.append(bid_depth)
            ask_depths.append(ask_depth)

            if bid_depth + ask_depth > 0:
                imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
                imbalances.append(imbalance)

        avg_bid_depth = statistics.mean(bid_depths) if bid_depths else 0
        avg_ask_depth = statistics.mean(ask_depths) if ask_depths else 0
        avg_imbalance = statistics.mean(imbalances) if imbalances else 0

        # Trade analysis
        if self.trades and duration > 0:
            trades_per_hour = len(self.trades) / (duration / 3600)
            trade_sizes = [t.size for t in self.trades]
            avg_trade_size = statistics.mean(trade_sizes)
            median_trade_size = statistics.median(trade_sizes)

            buy_trades = sum(1 for t in self.trades if t.side == 'buy')
            buy_pressure = buy_trades / len(self.trades) if self.trades else 0.5
        else:
            trades_per_hour = 0
            avg_trade_size = 0
            median_trade_size = 0
            buy_pressure = 0.5

        # Fill probability estimation
        # Based on trades hitting bid/ask levels
        fill_prob_5bps = min(0.95, trades_per_hour / 60 * 0.8)  # Rough estimate
        fill_prob_10bps = min(0.99, trades_per_hour / 30 * 0.9)
        fill_prob_20bps = min(1.0, trades_per_hour / 15)

        # Volatility
        if len(self.price_updates) > 1:
            prices = [p for _, p in self.price_updates]
            price_returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            hourly_volatility = statistics.stdev(price_returns) * 100 * (60 / (duration / 60)) ** 0.5 if price_returns else 0
        else:
            hourly_volatility = 0

        # Quote stability
        quote_stability = 100 - min(100, spread_volatility * 2)

        # Competition detection
        if duration > 0:
            quote_updates_per_min = self.orderbook_update_count / (duration / 60)
            # High update frequency = high competition
            competition_score = min(100, quote_updates_per_min / 2)
        else:
            quote_updates_per_min = 0
            competition_score = 0

        # Adverse selection risk
        # Higher volatility + lower volume = higher risk
        if trades_per_hour > 0 and hourly_volatility > 0:
            adverse_selection = min(100, (hourly_volatility / (trades_per_hour / 10)) * 50)
        else:
            adverse_selection = 50

        # Inventory half-life (time to exit position)
        # Based on trade frequency and depth
        if trades_per_hour > 5 and avg_bid_depth > 100:
            inventory_half_life = max(5, 60 / trades_per_hour)
        else:
            inventory_half_life = 999  # Very illiquid

        # Overall scores
        liquidity_score = (
            min(100, (avg_bid_depth + avg_ask_depth) / 5000 * 100) * 0.4 +
            min(100, trades_per_hour / 20 * 100) * 0.4 +
            (100 - min(100, avg_spread)) * 0.2
        )

        # MM score (profitability potential)
        mm_score = (
            (100 - min(100, avg_spread * 3)) * 0.25 +  # Tight spreads
            min(100, trades_per_hour / 10 * 100) * 0.20 +  # Good activity
            quote_stability * 0.15 +  # Stable quotes
            (100 - competition_score) * 0.15 +  # Low competition
            (100 - adverse_selection) * 0.15 +  # Low adverse selection
            min(100, (avg_bid_depth + avg_ask_depth) / 2000 * 100) * 0.10  # Good depth
        )

        # Profitability score
        expected_spread_capture = avg_spread * 0.3  # Capture 30% of spread
        profitability_score = (
            expected_spread_capture * fill_prob_10bps * trades_per_hour / 24 * 100
        )

        # Recommendations
        recommended_spread_min = max(5, avg_spread * 0.6)
        recommended_spread_max = max(10, avg_spread * 1.2)

        # Max position based on depth
        max_position = min(10000, (avg_bid_depth + avg_ask_depth) * 0.1)

        # Daily fills estimation
        estimated_fills = int(fill_prob_10bps * trades_per_hour * 24)

        # Daily PnL estimation (very rough)
        estimated_pnl = estimated_fills * expected_spread_capture * 0.01 * max_position * 0.5

        # Warnings
        warnings = []
        if avg_spread > 50:
            warnings.append(f"⚠️  Very wide spread ({avg_spread:.1f} bps)")
        if spread_volatility > 20:
            warnings.append(f"⚠️  Unstable spread (σ={spread_volatility:.1f} bps)")
        if trades_per_hour < 5:
            warnings.append(f"⚠️  Low activity ({trades_per_hour:.1f} trades/h)")
        if competition_score > 70:
            warnings.append(f"⚠️  High competition detected ({quote_updates_per_min:.0f} updates/min)")
        if adverse_selection > 70:
            warnings.append(f"⚠️  High adverse selection risk")
        if inventory_half_life > 120:
            warnings.append(f"⚠️  Illiquid - hard to exit positions")
        if abs(avg_imbalance) > 0.3:
            warnings.append(f"⚠️  Imbalanced orderbook ({'bid' if avg_imbalance > 0 else 'ask'} heavy)")

        return MarketMicrostructure(
            symbol=self.symbol,
            avg_spread_bps=avg_spread,
            min_spread_bps=min_spread,
            max_spread_bps=max_spread,
            spread_volatility=spread_volatility,
            bid_depth_1pct=avg_bid_depth,
            ask_depth_1pct=avg_ask_depth,
            avg_imbalance=avg_imbalance,
            trades_per_hour=trades_per_hour,
            avg_trade_size=avg_trade_size,
            median_trade_size=median_trade_size,
            buy_pressure=buy_pressure,
            fill_prob_5bps=fill_prob_5bps,
            fill_prob_10bps=fill_prob_10bps,
            fill_prob_20bps=fill_prob_20bps,
            price_volatility_pct=hourly_volatility,
            quote_stability=quote_stability,
            quote_updates_per_min=quote_updates_per_min,
            competition_score=competition_score,
            adverse_selection_risk=adverse_selection,
            inventory_half_life_min=inventory_half_life,
            liquidity_score=liquidity_score,
            mm_score=mm_score,
            profitability_score=profitability_score,
            recommended_spread_bps=(recommended_spread_min, recommended_spread_max),
            max_position_size_usd=max_position,
            estimated_daily_fills=estimated_fills,
            estimated_daily_pnl_usd=estimated_pnl,
            warnings=warnings,
            data_points=len(self.orderbook_snapshots) + len(self.trades),
            collection_duration_sec=duration
        )

    def _create_empty_result(self, duration: float) -> MarketMicrostructure:
        """Create empty result for markets with insufficient data"""
        return MarketMicrostructure(
            symbol=self.symbol,
            avg_spread_bps=0,
            min_spread_bps=0,
            max_spread_bps=0,
            spread_volatility=0,
            bid_depth_1pct=0,
            ask_depth_1pct=0,
            avg_imbalance=0,
            trades_per_hour=0,
            avg_trade_size=0,
            median_trade_size=0,
            buy_pressure=0,
            fill_prob_5bps=0,
            fill_prob_10bps=0,
            fill_prob_20bps=0,
            price_volatility_pct=0,
            quote_stability=0,
            quote_updates_per_min=0,
            competition_score=0,
            adverse_selection_risk=100,
            inventory_half_life_min=999,
            liquidity_score=0,
            mm_score=0,
            profitability_score=0,
            recommended_spread_bps=(0, 0),
            max_position_size_usd=0,
            estimated_daily_fills=0,
            estimated_daily_pnl_usd=0,
            warnings=["❌ Insufficient data collected"],
            data_points=0,
            collection_duration_sec=duration
        )


class AdvancedLiquidityScanner:
    """Main scanner coordinating multiple market analyses"""

    def __init__(self, duration_minutes: int = 5, markets: List[str] = None):
        self.duration_minutes = duration_minutes
        self.markets = markets or PRIORITY_MARKETS
        self.analyzers: Dict[str, AdvancedMarketAnalyzer] = {}
        self.results: List[MarketMicrostructure] = []
        self.console = Console() if RICH_AVAILABLE else None

        # Initialize analyzers
        for symbol in self.markets:
            self.analyzers[symbol] = AdvancedMarketAnalyzer(symbol)

    async def collect_data(self):
        """Collect market data via WebSocket"""
        duration_seconds = self.duration_minutes * 60

        if self.console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Collecting data for {len(self.markets)} markets...",
                    total=None
                )

                await self._websocket_collection(duration_seconds, progress, task)
        else:
            print(f"📡 Collecting data for {self.duration_minutes} minutes...")
            await self._websocket_collection(duration_seconds)

    async def _websocket_collection(self, duration_seconds: float, progress=None, task=None):
        """Internal WebSocket data collection"""
        try:
            async with websockets.connect(WS_URL) as websocket:
                # Subscribe to all channels
                await websocket.send(json.dumps({
                    "method": "subscribe",
                    "params": {"source": "prices"}
                }))

                for symbol in self.markets:
                    await websocket.send(json.dumps({
                        "method": "subscribe",
                        "params": {"source": "orderbook", "symbol": symbol}
                    }))
                    await websocket.send(json.dumps({
                        "method": "subscribe",
                        "params": {"source": "trades", "symbol": symbol}
                    }))

                start_time = time.time()
                message_count = 0

                while time.time() - start_time < duration_seconds:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        message_count += 1

                        channel = data.get('channel')

                        if channel == 'orderbook':
                            symbol = data.get('symbol')
                            if symbol in self.analyzers:
                                self.analyzers[symbol].process_orderbook(data.get('data', {}))

                        elif channel == 'trades':
                            symbol = data.get('symbol')
                            trades_data = data.get('data', [])
                            if symbol in self.analyzers and isinstance(trades_data, list):
                                for trade in trades_data:
                                    self.analyzers[symbol].process_trade(trade)

                        elif channel == 'prices':
                            price_data = data.get('data', [])
                            if isinstance(price_data, list):
                                for item in price_data:
                                    symbol = item.get('symbol')
                                    if symbol in self.analyzers:
                                        self.analyzers[symbol].process_price_update(item)

                        # Update progress
                        if progress and task and message_count % 50 == 0:
                            elapsed = time.time() - start_time
                            remaining = duration_seconds - elapsed
                            progress.update(task, description=
                                f"[cyan]Collecting data... {remaining:.0f}s remaining ({message_count} messages)")

                    except asyncio.TimeoutError:
                        continue

                if progress and task:
                    progress.update(task, description=f"[green]✓ Collection complete ({message_count} messages)")

        except Exception as e:
            if self.console:
                self.console.print(f"[red]✗ WebSocket error: {e}")
            else:
                print(f"✗ WebSocket error: {e}")

    def analyze_all(self):
        """Analyze all collected data"""
        if self.console:
            self.console.print("\n[cyan]📊 Analyzing market microstructure...")
        else:
            print("\n📊 Analyzing market microstructure...")

        for symbol, analyzer in self.analyzers.items():
            result = analyzer.analyze()
            self.results.append(result)

        # Sort by MM score
        self.results.sort(key=lambda x: x.mm_score, reverse=True)

    def render_dashboard(self):
        """Render beautiful terminal dashboard"""
        if not RICH_AVAILABLE:
            self._render_simple()
            return

        # Create summary table
        summary_table = Table(title="🎯 MARKET MAKING OPPORTUNITIES - RANKED BY MM SCORE",
                             box=box.DOUBLE_EDGE, show_header=True, header_style="bold magenta")

        summary_table.add_column("Rank", style="cyan", width=6)
        summary_table.add_column("Symbol", style="bold yellow", width=8)
        summary_table.add_column("MM Score", justify="right", width=10)
        summary_table.add_column("Spread", justify="right", width=12)
        summary_table.add_column("Trades/h", justify="right", width=10)
        summary_table.add_column("Fill Prob", justify="right", width=10)
        summary_table.add_column("Daily PnL", justify="right", width=12)
        summary_table.add_column("Status", width=10)

        for i, result in enumerate(self.results[:15], 1):
            # Score color
            if result.mm_score >= 60:
                score_style = "bold green"
                status = "🟢 Tier 1"
            elif result.mm_score >= 40:
                score_style = "yellow"
                status = "🟡 Tier 2"
            else:
                score_style = "red"
                status = "🔴 Tier 3"

            summary_table.add_row(
                str(i),
                result.symbol,
                f"[{score_style}]{result.mm_score:.1f}/100[/{score_style}]",
                f"{result.avg_spread_bps:.1f} bps",
                f"{result.trades_per_hour:.1f}",
                f"{result.fill_prob_10bps*100:.0f}%",
                f"${result.estimated_daily_pnl_usd:.2f}" if result.estimated_daily_pnl_usd > 0 else "N/A",
                status
            )

        self.console.print("\n")
        self.console.print(summary_table)

        # Detailed analysis for top 5
        self.console.print("\n")
        self.console.print(Panel("[bold cyan]📈 DETAILED ANALYSIS - TOP 5 MARKETS[/bold cyan]",
                                 box=box.DOUBLE))

        for i, result in enumerate(self.results[:5], 1):
            self._render_detailed_market(result, i)

    def _render_detailed_market(self, result: MarketMicrostructure, rank: int):
        """Render detailed analysis for one market"""
        # Create detail table
        detail_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
        detail_table.add_column("Metric", style="cyan", width=30)
        detail_table.add_column("Value", width=60)

        # Score styling
        mm_color = "green" if result.mm_score >= 60 else "yellow" if result.mm_score >= 40 else "red"

        detail_table.add_row("Market Making Score", f"[bold {mm_color}]{result.mm_score:.1f}/100[/bold {mm_color}]")
        detail_table.add_row("Liquidity Score", f"{result.liquidity_score:.1f}/100")
        detail_table.add_row("Profitability Score", f"{result.profitability_score:.1f}/100")
        detail_table.add_row("", "")

        # Spread metrics
        detail_table.add_row("[bold]Spread Analysis[/bold]", "")
        detail_table.add_row("  Average Spread", f"{result.avg_spread_bps:.2f} bps")
        detail_table.add_row("  Spread Range", f"{result.min_spread_bps:.1f} - {result.max_spread_bps:.1f} bps")
        detail_table.add_row("  Spread Volatility", f"±{result.spread_volatility:.2f} bps")
        detail_table.add_row("  Quote Stability", f"{result.quote_stability:.1f}/100")
        detail_table.add_row("", "")

        # Activity metrics
        detail_table.add_row("[bold]Trading Activity[/bold]", "")
        detail_table.add_row("  Trades per Hour", f"{result.trades_per_hour:.1f}")
        detail_table.add_row("  Avg Trade Size", f"${result.avg_trade_size:.2f}")
        detail_table.add_row("  Buy Pressure", f"{result.buy_pressure*100:.1f}%")
        detail_table.add_row("", "")

        # Fill probability
        detail_table.add_row("[bold]Fill Probability[/bold]", "")
        detail_table.add_row("  @ 5 bps from mid", f"[green]{result.fill_prob_5bps*100:.1f}%[/green]")
        detail_table.add_row("  @ 10 bps from mid", f"[green]{result.fill_prob_10bps*100:.1f}%[/green]")
        detail_table.add_row("  @ 20 bps from mid", f"[green]{result.fill_prob_20bps*100:.1f}%[/green]")
        detail_table.add_row("", "")

        # Risk metrics
        detail_table.add_row("[bold]Risk Assessment[/bold]", "")
        detail_table.add_row("  Competition Level", f"{result.competition_score:.0f}/100 ({result.quote_updates_per_min:.0f} updates/min)")
        detail_table.add_row("  Adverse Selection", f"{result.adverse_selection_risk:.0f}/100")
        detail_table.add_row("  Inventory Half-Life", f"{result.inventory_half_life_min:.0f} minutes")
        detail_table.add_row("  Price Volatility", f"{result.price_volatility_pct:.2f}%/hour")
        detail_table.add_row("", "")

        # Recommendations
        rec_color = "green" if result.mm_score >= 60 else "yellow"
        detail_table.add_row("[bold]Recommendations[/bold]", "")
        detail_table.add_row("  Optimal Spread", f"[{rec_color}]{result.recommended_spread_bps[0]:.1f} - {result.recommended_spread_bps[1]:.1f} bps[/{rec_color}]")
        detail_table.add_row("  Max Position Size", f"[{rec_color}]${result.max_position_size_usd:,.0f}[/{rec_color}]")
        detail_table.add_row("  Expected Daily Fills", f"[{rec_color}]{result.estimated_daily_fills} fills[/{rec_color}]")
        detail_table.add_row("  Estimated Daily PnL", f"[bold {rec_color}]${result.estimated_daily_pnl_usd:.2f}[/bold {rec_color}]")

        # Warnings
        if result.warnings:
            detail_table.add_row("", "")
            detail_table.add_row("[bold red]⚠️  Warnings[/bold red]", "")
            for warning in result.warnings:
                detail_table.add_row("", f"[red]{warning}[/red]")

        # Panel with rank and symbol
        panel_title = f"#{rank} - {result.symbol}"
        self.console.print(Panel(detail_table, title=panel_title, border_style="cyan"))
        self.console.print()

    def _render_simple(self):
        """Fallback rendering without rich"""
        print("\n" + "="*100)
        print("🎯 MARKET MAKING OPPORTUNITIES - RANKED BY MM SCORE")
        print("="*100)
        print(f"{'Rank':<6} {'Symbol':<10} {'MM Score':<12} {'Spread':<15} {'Trades/h':<12} {'Daily PnL':<15}")
        print("-"*100)

        for i, result in enumerate(self.results[:15], 1):
            status = "🟢" if result.mm_score >= 60 else "🟡" if result.mm_score >= 40 else "🔴"
            print(f"{i:<6} {result.symbol:<10} {status} {result.mm_score:>7.1f}/100 {result.avg_spread_bps:>10.1f} bps {result.trades_per_hour:>10.1f} ${result.estimated_daily_pnl_usd:>12.2f}")

    def save_results(self, filename: str):
        """Save detailed results to JSON"""
        output = {
            "scan_timestamp": datetime.now().isoformat(),
            "collection_duration_minutes": self.duration_minutes,
            "markets_analyzed": len(self.results),
            "results": [asdict(r) for r in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        if self.console:
            self.console.print(f"\n[green]✓ Detailed results saved to {filename}")
        else:
            print(f"\n✓ Detailed results saved to {filename}")


async def main_async(args):
    """Async main"""
    print("🔬 Pacifica Advanced Liquidity Scanner\n")

    markets = args.markets.split(',') if args.markets else PRIORITY_MARKETS

    scanner = AdvancedLiquidityScanner(
        duration_minutes=args.duration,
        markets=markets
    )

    await scanner.collect_data()
    scanner.analyze_all()
    scanner.render_dashboard()
    scanner.save_results(args.output)

    return 0


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Advanced market liquidity scanner for Pacifica")
    parser.add_argument("--duration", "-d", type=int, default=5,
                       help="Data collection duration in minutes (default: 5)")
    parser.add_argument("--markets", "-m", type=str, default=None,
                       help="Comma-separated list of markets to analyze (default: top 20)")
    parser.add_argument("--output", "-o", default="advanced_scan_results.json",
                       help="Output JSON file (default: advanced_scan_results.json)")

    args = parser.parse_args()

    try:
        exit_code = asyncio.run(main_async(args))
        return exit_code
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user")
        return 1


if __name__ == "__main__":
    exit(main())
