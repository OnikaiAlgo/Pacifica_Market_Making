# Pacifica Documentation

> Documentation extracted from https://docs.pacifica.fi on 2025-10-02

---

## Table of Contents

1. [About Pacifica](#about-pacifica)
2. [Trading on Pacifica](#trading-on-pacifica)
   - [Overview](#overview)
   - [Contract Specifications](#contract-specifications)
   - [Oracle Price & Mark Price](#oracle-price--mark-price)
   - [Order Types](#order-types)
   - [Margin & Leverage](#margin--leverage)
   - [Funding Rates](#funding-rates)
   - [Trading Fees](#trading-fees)
   - [Liquidations](#liquidations)
   - [Deposits & Withdrawals](#deposits--withdrawals)
3. [API Documentation](#api-documentation)
4. [Referrals and Affiliations](#referrals-and-affiliations)

---

## About Pacifica

### Company Overview

Pacifica was founded in January 2025 by a team of seasoned founders and builders who recognized the need for a next-generation trading platform that combines exceptional performance with user-first design principles and intelligent automation.

### Team Background

The founding team includes:
- **Crypto Exchange Veterans**: From Binance, FTX, Coinbase, NFTperp
- **Financial Institutions**: Jane Street, Fidelity
- **AI Pioneers**: OpenAI, DeepMind, ByteDance
- **Academic Excellence**: MIT, Stanford, NUS

### Mission

The founders aim to solve industry challenges through:
- Faster execution speeds
- Improved user experience
- Intelligent automation at scale

### Notable Achievements

- ✅ Launched testnet within 3 months
- ✅ Launched mainnet within 6 months
- ✅ Self-funded throughout their journey
- ✅ Committed to transparency and user empowerment

### Core Philosophy

To "reimagine how trading should feel" by building a platform that goes beyond traditional trading infrastructure.

---

## Trading on Pacifica

### Overview

Pacifica offers perpetual asset trading with the following key features:

#### Margin Systems
- **Cross-Margin**: Utilizes entire account balance to support all open positions
- **Isolated-Margin**: Assigns dedicated margin to individual positions

#### Leverage
- Varies by market from **5x to 50x**

#### Current Offerings
- Pacifica mainnet currently supports trading of **twenty perpetual assets**

#### Key Sections
- Contract Specifications
- Oracle Price & Mark Price
- Order Types
- Margin & Leverage
- Funding Rates
- Trading Fees
- Deposits & Withdrawals
- Liquidations

---

### Contract Specifications

#### Contract Type
- **Linear perpetual contracts**
- **No expiration date**
- Continuous trading with **hourly funding payments**

#### Key Specifications

| Specification | Details |
|--------------|---------|
| Contract Size | 1 unit of underlying spot asset |
| Initial Maintenance Margin (IMM) | Dynamically calculated based on user-selected leverage |
| Maintenance Margin | 50% of initial margin fraction |
| Margin Adjustment | Dynamically increased when Open Interest rises sharply |

#### Order and Position Limits

##### Maximum Market Order Value
- **Leverage ≥50**: $4M
- **Leverage 20-50**: $1M
- **Leverage 10-20**: $500k
- **Lower leverage**: $250k

##### Maximum Limit Order Value
- **10x market order value**

##### Position Size Limit
- **No explicit limit per user**

#### Funding Impact

**Notional size impacting funding rates:**
- **BTC, ETH**: $20,000 USDC
- **Other assets**: $6,000 USDC

#### Account Management
- Supports **cross or isolated margin** modes
- **Oracle-based pricing** for liquidation and PnL calculations

---

### Oracle Price & Mark Price

#### Oracle Price Calculation

**Update Frequency**: Every 3 seconds

**Calculation Method**: Weighted average from major exchanges

| Exchange | Weight |
|----------|--------|
| Binance | 2 |
| OKX | 1 |
| Bybit | 1 |
| Hyperliquid | 1 |

#### Mark Price Calculation

The **Mark Price** is the **median** of three components:

1. **Oracle (spot) price**
2. **Median** of best bid, best ask, and last trade on Pacifica
3. **Perpetual price** from major exchanges

#### Key Uses

- ✅ Funding Rate calculations
- ✅ Liquidation determinations
- ✅ Margin requirement calculations
- ✅ Unrealized Profit and Loss (PnL) tracking

**Goal**: Protect traders by reducing manipulation risks and ensuring market stability.

---

### Order Types

Pacifica offers **four order types**:

#### 1. Market Order

**Definition**: An order that executes immediately at the best available market prices

**Use Case**: Immediately enter or exit a position

---

#### 2. Limit Order

**Definition**: An order that specifies the price at which it will be executed

**Characteristics**: Can remain active based on different time-in-force settings

**Use Case**: Execution price matters more than being filled immediately

**Time-in-Force Options**:

| Option | Description |
|--------|-------------|
| **Good-Til-Cancelled (GTC)** | Order remains active until filled or cancelled |
| **Immediate-or-Cancel (IOC)** | Order attempts immediate matching, cancels unfilled portion |
| **Add-Liquidity-Only (ALO)** | Order added to order book only if it won't immediately match |

---

#### 3. Stop Market Order

**Definition**: A market order triggered when a specific price condition is met

**Use Case**: Take profit or limit losses

---

#### 4. Stop Limit Order

**Definition**: A limit order triggered when a specific price condition is met

---

### Margin & Leverage

#### Margin Modes

##### 1. Cross Margin

**Definition**: Utilizes entire account balance to support all open positions

**Account Value Calculation**:
```
account_value = account_cash_balance + pnl
```

**Characteristics**:
- Profit and Loss (PnL) updates continuously
- **Default mode**

##### 2. Isolated Margin

**Definition**: Assigns a dedicated margin amount to each individual position

#### Key Details

- ✅ Margin mode is selected **per trading pair**
- ✅ Cross Margin is the **default mode**
- ⚠️ Margin mode **cannot be changed** if positions are open
- ⚠️ Leverage can be **increased** but **not decreased** while positions exist

#### Initial Margin Calculation

```
initial_margin = (position_size × entry_price / leverage)
```

#### Withdrawable Balance Rules

**Unrealized PnL can be withdrawn if:**

1. `uPnL + account balance ≥ 10%` of total notional position value
2. Meets initial margin requirement

**Calculation**:
```
withdrawable_balance = account_balance + unrealized_pnl
                     - max(initial_margin_required, 0.1 × total_position_value)
```

⚠️ **Important**: Account balance cannot be withdrawn past zero, regardless of unrealized PnL

---

### Funding Rates

#### Overview

**Purpose**: Ensure perpetual contract prices closely track the underlying spot market

**Mechanism**: Periodic payments between long and short position holders

**Update Frequency**: Every hour

---

#### Funding Rate Calculation

```
funding_rate = (premium_index + clamp(interest_rate - premium_index, -0.05%, 0.05%)) / 8

premium_index = impact_price / oracle_price - 1

impact_price = max(impact_bid_price - oracle_price, 0)
             - max(oracle_price - impact_ask_price, 0)
```

#### Key Details

| Parameter | Value |
|-----------|-------|
| Interest Rate (8-hour) | 0.01% (fixed) |
| Funding Payment Cap | ±4% |
| Impact Notional (BTC) | $20,000 |
| Impact Notional (Other) | $6,000 |

---

#### Funding Payment Rules

| Funding Rate | Payment Direction |
|--------------|-------------------|
| **Positive** | Long positions pay short positions |
| **Negative** | Short positions pay long positions |

⚠️ **Important**: Funding payments affect isolated margin positions' liquidation prices

**Goal**: Maintain price alignment between perpetual contracts and spot markets through a dynamic, market-driven mechanism.

---

### Trading Fees

#### Fee Tiers

| Tier | 30-Day Volume (USD) | Maker Fee | Taker Fee |
|------|---------------------|-----------|-----------|
| **Tier 1** | $0 | 0.0075% | 0.0200% |
| **Tier 2** | > $5,000,000 | 0.0060% | 0.0190% |
| **Tier 3** | > $10,000,000 | 0.0045% | 0.0180% |
| **Tier 4** | > $25,000,000 | 0.0030% | 0.0170% |
| **Tier 5** | > $50,000,000 | 0.0015% | 0.0160% |

#### VIP Tiers

| VIP Tier | 30-Day Volume (USD) | Maker Fee | Taker Fee |
|----------|---------------------|-----------|-----------|
| **VIP 1** | > $100,000,000 | 0.0000% | 0.0150% |
| **VIP 2** | > $250,000,000 | 0.0000% | 0.0145% |
| **VIP 3** | > $500,000,000 | 0.0000% | 0.0140% |

#### Important Notes

- Volume thresholds are based on **total executed trading volume** in USD equivalent
- Fees are **settled automatically** for each trade

#### 🎉 Special Promotion

**All trading fees are HALVED from Sept 29th 12:00PM UTC to Oct 6th 12:00PM UTC**

---

### Liquidations

#### Liquidation Price Formula

```
liquidation_price = [price - (side × position_margin) / position_size]
                    / (1 - side / max_leverage / 2)
```

Where:
- `side = 1` for long positions
- `side = -1` for short positions

---

#### Three-Tiered Liquidation Process

##### 1. Market Liquidation

**Trigger**: Account equity falls below maintenance margin

**Process**:
1. All open orders are cancelled
2. Positions broken into chunks based on position size
3. Deduction: `max(0.75%, maintenance_margin_ratio × 0.4)` of position value

---

##### 2. Backstop Liquidation

**Trigger**: Account equity falls below **⅔ of maintenance margin**

**Process**:
- All open positions and remaining collateral transferred to **backstop liquidator**

---

##### 3. Auto-Deleveraging

**Trigger**: Account equity reaches **$0** during previous liquidation stages

**Process**:
- Automatically closes opposing traders' **profitable positions**

---

#### Key Principles

- ✅ Minimize market disruption
- ✅ Protect overall market stability
- ✅ Ensure fair handling of under-collateralized positions

**Goal**: Systematically manage risk while preventing cascading liquidations.

---

### Deposits & Withdrawals

#### Deposits

| Parameter | Value |
|-----------|-------|
| **Maximum Deposit** (Closed Beta) | $50,000 |
| **Gas Fees** | As determined by the network |

---

#### Withdrawals

| Parameter | Value |
|-----------|-------|
| **Maximum Withdrawal** (Closed Beta) | $50,000 per 24 hours |
| **Minimum Withdrawal** | $1 |
| **Withdrawal Fee** | $1 (covers gas fees) |

---

#### Wallet Support

**Compatible DeFi Wallets** with Solana address:
- ✅ Phantom
- ✅ Solflare
- ✅ Backpack
- ✅ Ledger
- ✅ WalletConnect

---

#### Important Notes

- ✅ Unrealized PnL can be withdrawn from isolated or cross-margined accounts
- ⚠️ Platform enforces a **time-based global withdrawal cap** that dynamically scales
- ℹ️ These are **temporary limits** for the Closed Beta phase

---

## API Documentation

### Overview

Pacifica offers comprehensive **REST and WebSocket APIs** for trading purposes.

**Quote**: "We offer complete REST and Websocket APIs to suit your trading needs."

---

### API Components

#### 1. REST API

**Markets Endpoints**:
- Market information
- Prices
- Order book
- Trades

**Account Endpoints**:
- Account information
- Settings
- Positions
- Trade history

**Subaccounts**:
- Subaccount management

**Orders**:
- Create orders
- Cancel orders
- Batch orders

---

#### 2. WebSocket

**Subscriptions**:
- Prices
- Order book
- Trades
- Account information

**Trading Operations**:
- Order creation
- Order cancellation

---

#### 3. Additional Components

- ✅ Signing methods
- ✅ Rate limits
- ✅ Error handling
- ✅ Tick and lot size information

---

### Resources

**Python SDK**: https://github.com/pacifica-fi/python-sdk

**Support/Feedback**: Discord API channel

---

## Referrals and Affiliations

### Referral Program

Available for users to invite others and earn rewards.

### Affiliate Program

Partnership opportunities for content creators and market influencers.

---

## Additional Resources

- **Official Website**: https://pacifica.fi
- **Documentation**: https://docs.pacifica.fi
- **GitHub (Python SDK)**: https://github.com/pacifica-fi/python-sdk
- **Support**: Discord community

---

## Notes

- This documentation is based on the **Closed Beta** phase (as of October 2025)
- Some features and limits are temporary and subject to change
- Always refer to the official documentation for the most up-to-date information

---

*Document generated on 2025-10-02 from https://docs.pacifica.fi*
