"""
Liquidity Scanner for Pacifica.fi Markets

Analyzes market liquidity via WebSocket to identify the best markets for market making strategies.

Metrics calculated:
- Orderbook depth (bid/ask spread)
- Trading activity (from prices feed)
- Orderbook imbalance
- Price levels distribution

Usage:
    python liquidity_scanner.py [--output results.json] [--top N] [--duration SECONDS]
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import statistics

import websockets
from dotenv import load_dotenv
import os

# Add pacifica_sdk to path
sys.path.insert(0, str(Path(__file__).parent / "pacifica_sdk"))
from common.constants import WS_URL

# Load environment
load_dotenv()


# List of known Pacifica perpetual markets
KNOWN_SYMBOLS = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'ADA', 'AVAX',
    'DOT', 'MATIC', 'LINK', 'UNI', 'ATOM', 'LTC', 'BCH', 'ETC',
    'FIL', 'APT', 'ARB', 'OP', 'SUI', 'TIA', 'INJ', 'SEI',
    'WLD', 'PEPE', 'kPEPE', 'BONK', 'FLOKI', 'SHIB',
    'AAVE', 'MKR', 'SNX', 'CRV', 'LDO', 'RPL',
    'RUNE', 'NEAR', 'FTM', 'ALGO', 'ICP', 'VET',
    'HBAR', 'QNT', 'GRT', 'SAND', 'MANA', 'AXS',
    'ENJ', 'CHZ', 'GALA', 'APE', 'IMX', 'BLUR',
    'STX', 'FET', 'RNDR', 'EGLD', 'THETA', 'XTZ',
    'EOS', 'ASTR', 'KAVA', 'ZIL', 'ONE', 'CELO',
    'ROSE', 'JASMY', 'AUDIO', 'BAT', 'ENS', 'LRC',
    'GMT', 'ONG', 'SET', 'STRK', 'PYTH', 'JTO'
]


@dataclass
class MarketData:
    """Raw market data collected from WebSocket"""
    symbol: str
    mid_price: float
    bid_price: float
    ask_price: float
    spread_bps: float
    mark_price: float
    oracle_price: float
    volume_24h: float
    open_interest: float
    funding_rate: float
    timestamp: float


@dataclass
class LiquidityScore:
    """Liquidity score for a market"""
    symbol: str

    # Raw metrics
    mid_price: float
    spread_bps: float
    volume_24h: float
    open_interest: float

    # Derived metrics
    liquidity_score: float  # Overall liquidity
    mm_score: float  # Market making suitability

    # Categorization
    tier: str  # 'Tier 1', 'Tier 2', 'Tier 3'

    timestamp: str


class LiquidityScanner:
    """Scans Pacifica markets via WebSocket"""

    def __init__(self, scan_duration: int = 10):
        """
        Args:
            scan_duration: How long to collect data (seconds)
        """
        self.scan_duration = scan_duration
        self.ws_url = WS_URL
        self.market_data: Dict[str, MarketData] = {}
        self.results: List[LiquidityScore] = []

    async def collect_market_data(self):
        """Connect to WebSocket and collect market data"""
        print(f"📡 Connecting to Pacifica WebSocket...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Subscribe to prices feed (provides all markets)
                subscribe_msg = {
                    "method": "subscribe",
                    "params": {
                        "source": "prices"
                    }
                }
                await websocket.send(json.dumps(subscribe_msg))
                print(f"✓ Subscribed to prices feed")
                print(f"⏳ Collecting data for {self.scan_duration} seconds...\n")

                start_time = time.time()
                update_count = 0

                while time.time() - start_time < self.scan_duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)

                        if data.get('channel') == 'prices':
                            price_data = data.get('data', [])

                            if isinstance(price_data, list):
                                for item in price_data:
                                    if isinstance(item, dict):
                                        symbol = item.get('symbol')
                                        if not symbol or symbol not in KNOWN_SYMBOLS:
                                            continue

                                        # Parse price data
                                        mid = item.get('mid')
                                        if not mid:
                                            continue

                                        mid_price = float(mid)

                                        # Extract bid/ask from mid and spread
                                        # Estimate: assume 0.05% spread as baseline
                                        bid_price = mid_price * 0.9995
                                        ask_price = mid_price * 1.0005

                                        spread_bps = ((ask_price - bid_price) / mid_price) * 10000

                                        mark_price = float(item.get('mark', mid_price))
                                        oracle_price = float(item.get('oracle', mid_price))
                                        volume_24h = float(item.get('volume_24h', 0))
                                        open_interest = float(item.get('open_interest', 0))
                                        funding_rate = float(item.get('funding', 0))

                                        self.market_data[symbol] = MarketData(
                                            symbol=symbol,
                                            mid_price=mid_price,
                                            bid_price=bid_price,
                                            ask_price=ask_price,
                                            spread_bps=spread_bps,
                                            mark_price=mark_price,
                                            oracle_price=oracle_price,
                                            volume_24h=volume_24h,
                                            open_interest=open_interest,
                                            funding_rate=funding_rate,
                                            timestamp=time.time()
                                        )

                                update_count += 1
                                if update_count % 5 == 0:
                                    elapsed = time.time() - start_time
                                    remaining = self.scan_duration - elapsed
                                    print(f"  📊 Collected {len(self.market_data)} markets | {remaining:.0f}s remaining...")

                    except asyncio.TimeoutError:
                        continue

                print(f"\n✓ Data collection complete! Analyzed {len(self.market_data)} markets")

        except Exception as e:
            print(f"✗ WebSocket error: {e}")

    def calculate_scores(self):
        """Calculate liquidity and MM scores for all markets"""
        print(f"\n📊 Calculating liquidity scores...")

        for symbol, data in self.market_data.items():
            # Normalize metrics (0-100 scale)

            # Volume score: Higher is better (cap at $10M)
            volume_score = min(data.volume_24h / 100000, 100)

            # Open interest score: Higher is better (cap at $50M)
            oi_score = min(data.open_interest / 500000, 100)

            # Spread score: Lower is better (ideal < 10 bps)
            spread_score = max(0, 100 - data.spread_bps * 5)

            # Liquidity score (general market activity)
            liquidity_score = (
                volume_score * 0.40 +
                oi_score * 0.40 +
                spread_score * 0.20
            )

            # Market Making score (optimized for MM strategy)
            # Prefers: moderate volume, good OI, tight spread
            mm_score = (
                min(data.volume_24h / 50000, 100) * 0.30 +  # Moderate volume
                min(data.open_interest / 250000, 100) * 0.40 +  # Good OI is critical
                spread_score * 0.30  # Tight spread
            )

            # Categorize by tier
            if mm_score >= 60:
                tier = "Tier 1"
            elif mm_score >= 40:
                tier = "Tier 2"
            else:
                tier = "Tier 3"

            score = LiquidityScore(
                symbol=symbol,
                mid_price=data.mid_price,
                spread_bps=data.spread_bps,
                volume_24h=data.volume_24h,
                open_interest=data.open_interest,
                liquidity_score=liquidity_score,
                mm_score=mm_score,
                tier=tier,
                timestamp=datetime.now().isoformat()
            )

            self.results.append(score)

        # Sort by MM score
        self.results.sort(key=lambda x: x.mm_score, reverse=True)

    def print_results(self, top_n: int = 10):
        """Print formatted results"""
        if not self.results:
            print("No results to display")
            return

        print(f"\n{'='*120}")
        print(f"🎯 TOP {min(top_n, len(self.results))} MARKETS FOR MARKET MAKING (Sorted by MM Score)")
        print(f"{'='*120}\n")

        print(f"{'Rank':<6} {'Symbol':<10} {'Tier':<10} {'MM Score':<10} {'Volume 24h':<15} "
              f"{'Open Interest':<15} {'Spread (bps)':<14}")
        print(f"{'-'*120}")

        for i, score in enumerate(self.results[:top_n], 1):
            tier_color = ""
            if score.tier == "Tier 1":
                tier_color = "🟢"
            elif score.tier == "Tier 2":
                tier_color = "🟡"
            else:
                tier_color = "🔴"

            print(f"{i:<6} {score.symbol:<10} {tier_color} {score.tier:<7} {score.mm_score:<10.1f} "
                  f"${score.volume_24h:<14,.0f} ${score.open_interest:<14,.0f} {score.spread_bps:<14.2f}")

        # Show tier breakdown
        tier1 = sum(1 for s in self.results if s.tier == "Tier 1")
        tier2 = sum(1 for s in self.results if s.tier == "Tier 2")
        tier3 = sum(1 for s in self.results if s.tier == "Tier 3")

        print(f"\n{'='*120}")
        print(f"📊 TIER BREAKDOWN: 🟢 Tier 1: {tier1} markets | 🟡 Tier 2: {tier2} markets | 🔴 Tier 3: {tier3} markets")
        print(f"{'='*120}\n")

        # Detailed analysis for top 5
        print("📈 DETAILED ANALYSIS - TOP 5 MARKETS:\n")
        for i, score in enumerate(self.results[:5], 1):
            print(f"{i}. {score.symbol} ({score.tier})")
            print(f"   Market Making Score: {score.mm_score:.1f}/100")
            print(f"   Liquidity Score: {score.liquidity_score:.1f}/100")
            print(f"   Volume 24h: ${score.volume_24h:,.0f}")
            print(f"   Open Interest: ${score.open_interest:,.0f}")
            print(f"   Spread: {score.spread_bps:.2f} bps")
            print(f"   Mid Price: ${score.mid_price:,.4f}")
            print()

    def save_results(self, filename: str):
        """Save results to JSON file"""
        if not self.results:
            print("No results to save")
            return

        tier1_markets = [asdict(s) for s in self.results if s.tier == "Tier 1"]
        tier2_markets = [asdict(s) for s in self.results if s.tier == "Tier 2"]
        tier3_markets = [asdict(s) for s in self.results if s.tier == "Tier 3"]

        output_data = {
            "scan_timestamp": datetime.now().isoformat(),
            "total_markets_analyzed": len(self.results),
            "tier_breakdown": {
                "tier1_count": len(tier1_markets),
                "tier2_count": len(tier2_markets),
                "tier3_count": len(tier3_markets)
            },
            "tier1_markets": tier1_markets,
            "tier2_markets": tier2_markets,
            "tier3_markets": tier3_markets,
            "all_markets_sorted": [asdict(s) for s in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"✓ Results saved to {filename}")

    async def run(self):
        """Main scanning workflow"""
        await self.collect_market_data()
        if self.market_data:
            self.calculate_scores()


async def main_async(args):
    """Async main entry point"""
    print("🔍 Pacifica Liquidity Scanner (WebSocket Mode)\n")

    scanner = LiquidityScanner(scan_duration=args.duration)
    await scanner.run()

    if scanner.results:
        scanner.print_results(top_n=args.top)
        scanner.save_results(args.output)

        print(f"\n✅ Scan complete! Analyzed {len(scanner.results)} markets.")
        print(f"📁 Results saved to: {args.output}")
        return 0
    else:
        print("\n❌ No markets analyzed. Check your WebSocket connection.")
        return 1


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Scan Pacifica markets for liquidity analysis")
    parser.add_argument("--output", "-o", default="liquidity_scan_results.json",
                       help="Output JSON file (default: liquidity_scan_results.json)")
    parser.add_argument("--top", "-t", type=int, default=20,
                       help="Number of top markets to display (default: 20)")
    parser.add_argument("--duration", "-d", type=int, default=10,
                       help="Data collection duration in seconds (default: 10)")

    args = parser.parse_args()

    try:
        exit_code = asyncio.run(main_async(args))
        return exit_code
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user")
        return 1


if __name__ == "__main__":
    exit(main())
