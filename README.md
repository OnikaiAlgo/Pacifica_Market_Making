# Pacifica Finance DEX Market Making Strategy with Python

A Python market making bot for the Pacifica Finance DEX platform on the Solana blockchain, using WebSocket and REST API calls.

**How it works**: The bot performs "ping-pong" trading by placing Open (Long or Short depending on market trend) and Close limit orders around the current market mid-price using a fraction of your available capital. When one order fills (with a significant amount), it immediately places a new order on the opposite side to capture the spread.

**Advanced Features**:
- **Dynamic Spreads**: Avellaneda-Stoikov model for optimal spread calculation
- **Trend Analysis**: SuperTrend indicator for directional bias
- **Real-time Data**: WebSocket-based market data and balance monitoring
- **Solana-Based**: Fully integrated with the Solana blockchain ecosystem

## Getting Started with Pacifica Finance

### Step 1: Create Your Account

Before using this bot, you need a Pacifica Finance account:

1. **Visit [https://app.pacifica.fi/](https://app.pacifica.fi/)**
2. **Use referral code: `18SRTGXDJWCVSY75`** for trading fee discounts
3. Connect your Solana wallet (Phantom, Solflare, etc.)
4. Deposit USDC to start trading

> **💡 Important**: Using the referral code `18SRTGXDJWCVSY75` gives you reduced trading fees, which is crucial for market making profitability.

### Step 2: Prepare Your Wallet

This bot requires a Solana wallet with:
- **USDC** for trading collateral
- **SOL** for transaction fees (~0.01 SOL minimum)

**Recommended**: Use a dedicated wallet for the bot, separate from your main holdings.

## Included Components

This project includes the official Pacifica Finance Python SDK (`pacifica_sdk/`) from [https://github.com/pacifica-fi/python-sdk](https://github.com/pacifica-fi/python-sdk) for seamless integration with the Pacifica DEX.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your .env file (see Configuration section below)
cp .env.example .env
# Edit .env and add your PRIVATE_KEY and SYMBOL

# Run data collector for at least 1 hour
python data_collector.py

# Run calculation of parameters
python calculate_avellaneda_parameters.py --symbol BTC --minutes 5
python find_trend.py --symbol BTC --interval 5m

# Run the market maker
python market_maker.py --symbol BTC
```

Use Docker Compose to run everything at once (see Docker section below).

## How to Get Your Solana Private Key

**IMPORTANT**: Pacifica Finance operates on the **Solana blockchain**, not Ethereum. You need a Solana wallet and private key.

### Option 1: Phantom Wallet (Recommended for Beginners)

1. **Open Phantom Wallet** (browser extension or mobile app)
2. Click on the **Settings** icon (gear icon, usually in the top-right)
3. Navigate to **Security & Privacy**
4. Click on **Export Private Key**
5. Enter your Phantom password to confirm
6. **Copy the private key** - it will be in **base58 format** (a long string starting with numbers/letters, NOT starting with "0x")
7. Save it securely (see Security Best Practices below)

Example format: `2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b`

### Option 2: Solflare Wallet

1. **Open Solflare Wallet** (browser extension or mobile app)
2. Click on your wallet name at the top
3. Navigate to **Settings**
4. Select **Export Private Key** or **Show Private Key**
5. Authenticate (password/biometrics)
6. **Copy the private key** in **base58 format**
7. Store it securely

### Option 3: Solana CLI (For Advanced Users)

If you have the Solana CLI installed:

```bash
# Display your public key
solana-keygen pubkey ~/.config/solana/id.json

# To view the private key, you need to read the keypair file
# The file is a JSON array with your keypair
cat ~/.config/solana/id.json

# To convert to base58 format (recommended):
solana-keygen pubkey --keypair ~/.config/solana/id.json --outfile /dev/stdout | base58
```

**Note**: The default keypair location is `~/.config/solana/id.json` but may vary based on your configuration.

### Option 4: Create a New Wallet for the Bot (Recommended)

For security reasons, it's highly recommended to create a **dedicated wallet** specifically for the bot:

```bash
# Install Solana CLI if not already installed
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"

# Create a new keypair
solana-keygen new --outfile ~/pacifica-bot-keypair.json

# View the public key (your wallet address)
solana-keygen pubkey ~/pacifica-bot-keypair.json

# Extract the private key in base58 format
# The keypair file is a JSON array - use this Python script:
python3 -c "import json; import base58; data = json.load(open('pacifica-bot-keypair.json')); print(base58.b58encode(bytes(data)).decode())"
```

Transfer a small amount of USDC and SOL (for gas fees) to this new wallet address before running the bot.

### Verifying Your Private Key Format

Your Solana private key should be:
- **Base58 encoded** (looks like: `3mKp7rW...` - alphanumeric, ~87-88 characters)
- **NOT** starting with "0x" (that's Ethereum format)
- **NOT** in JSON array format `[1,2,3,...]`

## Dependencies

The project requires the following Python packages (see `requirements.txt`):

### Core Dependencies
- **aiohttp**: Async HTTP client for API calls
- **websockets & websocket-client**: WebSocket connectivity
- **python-dotenv**: Environment variable management
- **requests**: Synchronous HTTP requests

### Solana Blockchain Integration
- **solders**: Solana Python SDK for keypair management and signing
- **base58**: Base58 encoding/decoding for Solana keys

### Data Analysis & Trading
- **pandas & numpy**: Data manipulation and numerical computing
- **scipy**: Scientific computing for mathematical models
- **arch**: GARCH modeling for volatility estimation
- **pandas-ta**: Technical analysis indicators

### User Interface
- **colorama**: Terminal color output for better readability

## Configuration

### Environment Variables (`.env`)

Create a `.env` file in the root directory (use `.env.example` as a template):

```bash
# =============================================================================
# REQUIRED CONFIGURATION
# =============================================================================

# Your Solana private key in base58 format
# See "How to Get Your Solana Private Key" section above
PRIVATE_KEY=your_base58_private_key_here

# Trading symbol (simple format without USDT suffix)
# Valid examples: BTC, ETH, SOL
# Do NOT use: BTCUSDT, ETHUSDT (use simple format instead)
SYMBOL=BTC

# =============================================================================
# OPTIONAL PARAMETERS
# =============================================================================

# Timeframe for SuperTrend analysis
# Options: 1m, 5m, 15m, 30m, 1h, 4h, 1d
TREND_INTERVAL=5m

# Avellaneda parameters refresh interval (minutes)
PARAM_REFRESH_MINUTES=10

# Trend analysis refresh interval (minutes)
TREND_REFRESH_MINUTES=5

# Restart interval on error (minutes)
RESTART_MINUTES=2
```

### Main Parameters (`market_maker.py`)

These parameters can be configured at the top of the `market_maker.py` file:

```python
# Strategy Settings
DEFAULT_SYMBOL = "BTC"                  # Default trading pair
FLIP_MODE = False                       # True for short-biased, False for long-biased
DEFAULT_BUY_SPREAD = 0.006              # 0.6% below mid-price (fallback)
DEFAULT_SELL_SPREAD = 0.006             # 0.6% above mid-price (fallback)
USE_AVELLANEDA_SPREADS = True           # Use dynamic spreads from Avellaneda model
DEFAULT_BALANCE_FRACTION = 0.2          # Use 20% of balance per order
POSITION_THRESHOLD_USD = 15.0           # Position size threshold in USD

# Timing Settings
ORDER_REFRESH_INTERVAL = 30             # Seconds before canceling unfilled orders
PRICE_REPORT_INTERVAL = 60              # Price reporting frequency (seconds)
BALANCE_REPORT_INTERVAL = 60            # Balance reporting frequency (seconds)

# SuperTrend Integration
USE_SUPERTREND_SIGNAL = True            # Use SuperTrend for dynamic flip_mode
SUPERTREND_CHECK_INTERVAL = 600         # Check SuperTrend signal every 10 minutes

# Order Management
DEFAULT_PRICE_CHANGE_THRESHOLD = 0.001  # Min price change to replace order (0.1%)
CANCEL_SPECIFIC_ORDER = True            # Cancel specific orders vs all orders

# Logging
RELEASE_MODE = True                     # True = errors only, False = detailed logs
```

### Important Parameter Explanations

- **`DEFAULT_BALANCE_FRACTION`**: Controls order sizing. With 0.2 (20%), each order uses 20% of your available balance. Lower values = smaller orders (safer), higher values = larger orders (more risk, more potential profit).

- **`POSITION_THRESHOLD_USD`**: When your net position exceeds this USD value ($15 default), the bot will only place orders to reduce the position (no new position building). This acts as a safety mechanism.

- **`FLIP_MODE`**:
  - `False` = Long-biased (places buy orders first, then sells to close)
  - `True` = Short-biased (places sell orders first, then buys to close)
  - When `USE_SUPERTREND_SIGNAL = True`, this is dynamically adjusted based on market trend

- **`USE_AVELLANEDA_SPREADS`**: When enabled, the bot uses the Avellaneda-Stoikov model for optimal spread calculation based on market volatility. Falls back to `DEFAULT_BUY_SPREAD` and `DEFAULT_SELL_SPREAD` if calculation fails.

- **`ORDER_REFRESH_INTERVAL`**: How long to wait before canceling an unfilled order. Lower values (e.g., 10-15s) = more aggressive trading with higher exchange fees. Higher values (e.g., 60s) = less aggressive but fewer fees.

- **`RELEASE_MODE`**:
  - `True` = Production mode, only errors are logged (recommended for live trading)
  - `False` = Debug mode, detailed logs for troubleshooting

**Account Recommendation**: Use a **dedicated Solana wallet** for the bot to avoid conflicts with manual trading and ensure accurate balance calculations.

## Available Scripts

### Core Trading Components

```bash
# Main trading bot
python market_maker.py                          # Start with default symbol from .env
python market_maker.py --symbol BTC             # Start with specific symbol

# Data collection and analysis
python data_collector.py                        # Collect real-time market data
python calculate_avellaneda_parameters.py --symbol BTC --minutes 5  # Calculate dynamic spreads
python find_trend.py --symbol BTC --interval 5m                     # Trend analysis with SuperTrend

# Monitoring and utilities
python terminal_dashboard.py                                        # Real-time account dashboard
python get_my_trading_volume.py --symbol BTC --days 7              # Get trading volume for BTC (last 7 days)
python get_my_trading_volume.py --days 30                          # Get total volume across all symbols (last 30 days)
python websocket_orders.py                                          # Monitor orders via WebSocket
```

### Script Descriptions

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `market_maker.py` | Main market making bot | Run 24/7 for automated trading |
| `data_collector.py` | Collects real-time order book and trade data | Run before starting market maker (needs 1+ hours of data) |
| `calculate_avellaneda_parameters.py` | Calculates optimal spreads using Avellaneda-Stoikov model | Runs automatically in Docker, or manually for testing |
| `find_trend.py` | Determines market trend using SuperTrend indicator | Runs automatically in Docker, or manually for analysis |
| `terminal_dashboard.py` | Real-time overview of balances, positions, orders | Use for monitoring bot performance |
| `get_my_trading_volume.py` | Calculates your trading volume and fees | Use for performance analysis |
| `websocket_orders.py` | Real-time order updates via WebSocket | Use for debugging order flow |

## Terminal Dashboard

For a comprehensive, real-time overview of your account, use the `terminal_dashboard.py` script. It provides:
- Account balances (USDC and other assets)
- Open positions with unrealized PnL
- Recent order activity
- Real-time market data

```bash
python terminal_dashboard.py
```

This is extremely useful for monitoring the bot's performance without needing to check the exchange directly.

## Docker Deployment

The system includes multiple containerized services that work together for a complete market making solution.

### Services Available

- **data-collector**: Real-time market data collection via WebSocket
- **avellaneda-params**: Dynamic spread calculation using Avellaneda-Stoikov model
- **trend-finder**: SuperTrend analysis for directional bias
- **market-maker**: Main trading bot with market making strategy

### Docker Commands

```bash
# Build all services
docker-compose build

# Run all services (detached mode)
docker-compose up -d

# Run specific service
docker-compose up -d data-collector
docker-compose up -d market-maker

# View logs (follow mode)
docker-compose logs -f market-maker
docker-compose logs -f data-collector

# View logs for all services
docker-compose logs -f

# Stop all services
docker-compose down

# Stop specific service
docker-compose stop market-maker

# Restart a service
docker-compose restart market-maker

# View service status
docker-compose ps
```

### Configuration

**Trading pair configuration**: Set `SYMBOL=BTC` (or your desired symbol) in your `.env` file. All services will automatically use this symbol.

**Service timing**: Configure refresh intervals in `docker-compose.yml`:

```yaml
services:
  data-collector:
    environment:
      - RESTART_MINUTES=2        # Data collection restart interval (if fails)

  avellaneda-params:
    environment:
      - PARAM_REFRESH_MINUTES=10 # Parameter calculation interval

  trend-finder:
    environment:
      - TREND_REFRESH_MINUTES=5  # Trend analysis interval
      - TREND_INTERVAL=5m        # Candlestick timeframe
```

### First-Time Docker Setup

1. **Create your `.env` file**:
   ```bash
   cp .env.example .env
   # Edit .env and add your PRIVATE_KEY and SYMBOL
   ```

2. **Build the Docker images**:
   ```bash
   docker-compose build
   ```

3. **Start the data collector first** (let it run for at least 1 hour):
   ```bash
   docker-compose up -d data-collector
   docker-compose logs -f data-collector
   ```

4. **Start all services**:
   ```bash
   docker-compose up -d
   ```

5. **Monitor the logs**:
   ```bash
   docker-compose logs -f market-maker
   ```

## Manual Usage (Without Docker)

If you prefer to run the bot manually without Docker:

### Step 1: Install Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor

# Add your PRIVATE_KEY and SYMBOL
```

### Step 3: Collect Initial Data

Before running the market maker, you need to collect market data:

```bash
# Run data collector for at least 1 hour
# This collects order book snapshots and trade data
python data_collector.py

# You can run this in the background using screen or tmux:
screen -S data-collector
python data_collector.py
# Press Ctrl+A then D to detach
```

### Step 4: Run Analysis Scripts

In separate terminals (or background):

```bash
# Terminal 1: Calculate Avellaneda parameters (refresh every 10 minutes)
while true; do
    python calculate_avellaneda_parameters.py --symbol BTC --minutes 10
    sleep 600  # 10 minutes
done

# Terminal 2: Calculate SuperTrend (refresh every 5 minutes)
while true; do
    python find_trend.py --symbol BTC --interval 5m
    sleep 300  # 5 minutes
done
```

### Step 5: Run Market Maker

```bash
# In a new terminal
python market_maker.py --symbol BTC
```

### Step 6: Monitor with Dashboard

```bash
# In yet another terminal
python terminal_dashboard.py
```

### Using Screen or Tmux for Background Processes

**Using screen:**
```bash
# Start data collector
screen -S data-collector
python data_collector.py
# Ctrl+A, D to detach

# Start avellaneda calculator
screen -S avellaneda
while true; do python calculate_avellaneda_parameters.py --symbol BTC --minutes 10; sleep 600; done
# Ctrl+A, D to detach

# Start trend finder
screen -S trend
while true; do python find_trend.py --symbol BTC --interval 5m; sleep 300; done
# Ctrl+A, D to detach

# Start market maker
screen -S market-maker
python market_maker.py --symbol BTC
# Ctrl+A, D to detach

# List all screens
screen -ls

# Reattach to a screen
screen -r market-maker
```

**Using tmux:**
```bash
# Create a new session with multiple windows
tmux new -s pacifica-bot

# Window 0: data collector
python data_collector.py
# Ctrl+B, C to create new window

# Window 1: avellaneda
while true; do python calculate_avellaneda_parameters.py --symbol BTC --minutes 10; sleep 600; done
# Ctrl+B, C to create new window

# Window 2: trend
while true; do python find_trend.py --symbol BTC --interval 5m; sleep 300; done
# Ctrl+B, C to create new window

# Window 3: market maker
python market_maker.py --symbol BTC

# Ctrl+B, D to detach
# tmux attach -t pacifica-bot to reattach
```

## Security Warnings and Best Practices

### Private Key Security

1. **Never share your private key** with anyone
2. **Never commit your `.env` file** to version control
3. **Use a dedicated wallet** for the bot (separate from your main holdings)
4. **Keep backups** of your private key in a secure location (password manager, hardware wallet, etc.)
5. **Rotate keys periodically** if you suspect any compromise

### Trading Security

1. **Start with small amounts** - Test with $50-100 initially
2. **Use dedicated funds** - Only allocate funds you can afford to lose
3. **Set appropriate `DEFAULT_BALANCE_FRACTION`** - Start with 0.1 (10%) or lower
4. **Monitor actively for the first 24-48 hours**
5. **Set up alerts** for unusual activity

### API Security

1. **Check API endpoints** - Ensure you're connecting to official Pacifica API
2. **Monitor WebSocket connections** - The bot will log connection issues
3. **Rate limiting** - The bot has built-in rate limiting, but monitor for errors

### Server Security (If Hosting)

1. **Use a VPS with SSH key authentication** (disable password login)
2. **Enable a firewall** (ufw on Ubuntu)
3. **Keep system updated**: `sudo apt update && sudo apt upgrade`
4. **Use Docker** for isolation
5. **Set up log rotation** to prevent disk space issues

## Risk Warnings

**IMPORTANT: READ CAREFULLY BEFORE USING THIS BOT**

### Financial Risks

1. **Loss of Capital**: This trading bot can and likely will lose money. Market making is a competitive activity dominated by professional firms with significant resources.

2. **Market Volatility**: Cryptocurrency markets are highly volatile. Rapid price movements can result in significant losses.

3. **Impermanent Loss**: Market making strategies can result in holding inventory at unfavorable prices during trending markets.

4. **Liquidation Risk**: Although this bot uses low leverage (1x default), any leverage trading carries liquidation risk.

5. **Smart Contract Risk**: Pacifica Finance is built on smart contracts. While audited, smart contracts can have bugs or vulnerabilities.

### Technical Risks

1. **Connection Failures**: WebSocket or API disconnections can result in missed opportunities or unintended positions.

2. **Exchange Downtime**: If Pacifica experiences downtime, you may be unable to manage positions.

3. **Bug Risk**: This is open-source software. While tested, bugs may exist that could result in unexpected behavior.

4. **Solana Network Congestion**: During high network activity, transactions may fail or be delayed.

### Operational Risks

1. **Insufficient Monitoring**: Leaving the bot unattended without proper monitoring can result in unforeseen issues.

2. **Configuration Errors**: Incorrect parameter settings can lead to excessive trading or large positions.

3. **Slippage**: Actual fill prices may differ from expected prices, especially in volatile markets.

### Best Practices to Mitigate Risks

- Start with **very small amounts** ($50-100 USD)
- Use a **dedicated account** separate from your main holdings
- Set conservative parameters:
  - `DEFAULT_BALANCE_FRACTION = 0.1` (10% per order)
  - `POSITION_THRESHOLD_USD = 15.0` or lower
  - `ORDER_REFRESH_INTERVAL = 30` or higher
- **Monitor actively** for the first 24-48 hours
- Use the `terminal_dashboard.py` to track performance
- Check logs regularly for errors
- Have a **stop-loss plan** (manual intervention if losses exceed X%)
- **Never use funds you cannot afford to lose**

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Invalid Solana private key"

**Solution**:
- Verify your private key is in **base58 format** (not Ethereum hex format)
- Check that there are no extra spaces or newlines in your `.env` file
- Ensure you're using a Solana wallet private key, not Ethereum

```bash
# Test your private key
python3 -c "from solders.keypair import Keypair; import os; from dotenv import load_dotenv; load_dotenv(); Keypair.from_base58_string(os.getenv('PRIVATE_KEY')); print('✅ Private key is valid')"
```

#### Issue: "No price data available"

**Solution**:
- Check that `data_collector.py` is running
- Verify WebSocket connection is working
- Check network connectivity to Pacifica API
- Ensure the symbol you're trading exists on Pacifica

```bash
# Test WebSocket connection
python3 -c "import asyncio; import websockets; asyncio.run(websockets.connect('wss://ws.pacifica.fi/ws')).__enter__(); print('✅ WebSocket connection successful')"
```

#### Issue: "Insufficient balance"

**Solution**:
- Check your USDC balance on Pacifica
- Ensure you have enough SOL for transaction fees (~0.01 SOL minimum)
- Reduce `DEFAULT_BALANCE_FRACTION` to use less capital per trade
- Check that your funds are on the correct Solana network (mainnet-beta)

#### Issue: "Order placement failed"

**Solution**:
- Check Pacifica API status
- Verify your private key has trading permissions
- Ensure order size meets minimum notional requirements
- Check if you have any open positions that need to be closed first
- Review market maker logs for specific error messages

#### Issue: "WebSocket disconnecting frequently"

**Solution**:
- Check network stability
- Verify firewall settings allow WebSocket connections
- Consider using a VPS in a region closer to Pacifica servers (US-based recommended)
- Check for ISP throttling of WebSocket connections

#### Issue: "Avellaneda parameters not loading"

**Solution**:
- Ensure `calculate_avellaneda_parameters.py` has run at least once
- Check that the `params/` directory exists and has write permissions
- Verify sufficient historical data has been collected (minimum 1 hour)
- Check logs for calculation errors

```bash
# Manually calculate parameters
python calculate_avellaneda_parameters.py --symbol BTC --minutes 5

# Check if parameter files exist
ls -la params/
```

#### Issue: "Docker container keeps restarting"

**Solution**:
- Check container logs: `docker-compose logs -f market-maker`
- Verify `.env` file is properly configured
- Ensure directories have correct permissions: `chmod -R 755 PACIFICA_data params`
- Check Docker resource limits (RAM, CPU)

#### Issue: "Position not closing"

**Solution**:
- Check `POSITION_THRESHOLD_USD` setting
- Verify the bot is in closing mode (check logs)
- Manually close position if needed using terminal_dashboard.py
- Ensure `reduceOnly` orders are being accepted by the exchange

### Getting Help

If you encounter issues not covered here:

1. **Check the logs**:
   - Docker: `docker-compose logs -f market-maker`
   - Manual: Check `market_maker.log` file

2. **Enable debug mode**: Set `RELEASE_MODE = False` in `market_maker.py`

3. **Test connection**:
   ```bash
   python terminal_dashboard.py
   ```

4. **Verify API status**: Check Pacifica's official channels for any service disruptions

## Performance Recommendations

**Latency is critical** for market making success, especially with fast order refresh rates (low `ORDER_REFRESH_INTERVAL`).

### Recommended Hosting

- **Recommended**: AWS, Google Cloud, or Azure in **US East** regions (closest to Pacifica servers)
- **Instance type**:
  - AWS: t3.small or t3.medium (2 vCPU, 2-4 GB RAM)
  - Google Cloud: e2-small or e2-medium
  - Azure: B2s or B2ms
- **Why**: Proximity to Pacifica Finance infrastructure reduces order placement latency (typically sub-100ms vs 200-500ms from home connections)
- **Alternative regions**: US West, EU West for reasonable latency
- **Avoid**: Shared/burstable instances during active trading; Asia-Pacific regions (unless Pacifica expands there)

### Network Requirements

- Stable internet connection (minimum 10 Mbps upload/download)
- Low latency (<100ms to Pacifica API preferred)
- Reliable WebSocket connectivity (no corporate proxies that block WS)

### Hardware Requirements

**Minimum**:
- 1 CPU core
- 1 GB RAM
- 5 GB disk space

**Recommended**:
- 2 CPU cores
- 2-4 GB RAM
- 20 GB disk space (for historical data storage)

### Testing Latency

```bash
# Test API latency
curl -w "@-" -o /dev/null -s "https://api.pacifica.fi/api/v1/markets" <<'EOF'
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_appconnect:  %{time_appconnect}\n
time_pretransfer:  %{time_pretransfer}\n
time_redirect:  %{time_redirect}\n
time_starttransfer:  %{time_starttransfer}\n
----------\n
time_total:  %{time_total}\n
EOF
```

## Useful Links

### Pacifica Finance Documentation

- **Official Website**: [https://pacifica.fi](https://pacifica.fi)
- **Trading Platform**: [https://app.pacifica.fi](https://app.pacifica.fi)
- **API Documentation**: Check Pacifica's official documentation for API reference
- **Discord/Telegram**: Join Pacifica's community channels for support

### Solana Resources

- **Solana Documentation**: [https://docs.solana.com](https://docs.solana.com)
- **Solana Explorer**: [https://explorer.solana.com](https://explorer.solana.com)
- **Solana CLI Guide**: [https://docs.solana.com/cli](https://docs.solana.com/cli)

### Wallet Resources

- **Phantom Wallet**: [https://phantom.app](https://phantom.app)
- **Solflare Wallet**: [https://solflare.com](https://solflare.com)

### Trading Resources

- **Avellaneda-Stoikov Paper**: "High-frequency trading in a limit order book"
- **Market Making Strategies**: Research optimal inventory management
- **SuperTrend Indicator**: Technical analysis for trend following

## Advanced Configuration

### Custom Strategy Parameters

You can modify the strategy behavior by editing parameters in `market_maker.py`:

```python
# Example: More conservative strategy
DEFAULT_BALANCE_FRACTION = 0.1      # Use only 10% per order
POSITION_THRESHOLD_USD = 10.0       # Smaller position threshold
ORDER_REFRESH_INTERVAL = 60         # Less aggressive order replacement
DEFAULT_BUY_SPREAD = 0.01           # 1% spread (wider)
DEFAULT_SELL_SPREAD = 0.01          # 1% spread (wider)
```

```python
# Example: More aggressive strategy (RISKY)
DEFAULT_BALANCE_FRACTION = 0.3      # Use 30% per order
ORDER_REFRESH_INTERVAL = 15         # More frequent order updates
DEFAULT_BUY_SPREAD = 0.003          # 0.3% spread (tighter)
DEFAULT_SELL_SPREAD = 0.003         # 0.3% spread (tighter)
```

### Multiple Symbol Trading

To run the bot on multiple symbols simultaneously, use separate Docker instances:

```yaml
# In docker-compose.yml, create additional services
services:
  market-maker-btc:
    extends: market-maker
    container_name: pacifica_market_maker_btc
    environment:
      - SYMBOL=BTC

  market-maker-eth:
    extends: market-maker
    container_name: pacifica_market_maker_eth
    environment:
      - SYMBOL=ETH
```

Or run multiple Python processes manually:
```bash
python market_maker.py --symbol BTC &
python market_maker.py --symbol ETH &
python market_maker.py --symbol SOL &
```

## Contributing

This is an open-source project. Contributions, bug reports, and feature requests are welcome!

## License

This project is provided as-is without warranties. Use at your own risk.

---

**Final Warning**: This trading software will likely lose money, even if it generates significant volume, because it isn't competitive with professional firms. Always start with small amounts and make sure you understand the risks of automated cryptocurrency trading on the Solana blockchain.

**Stay safe, trade responsibly, and may the markets be in your favor!**