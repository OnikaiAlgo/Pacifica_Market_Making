# PACIFICA API DOCUMENTATION - COMPLETE REFERENCE

> Documentation extracted from https://docs.pacifica.fi on 2025-10-02

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication & Signing](#authentication--signing)
3. [REST API](#rest-api)
   - [Markets API](#markets-api)
   - [Account API](#account-api)
   - [Subaccounts API](#subaccounts-api)
   - [Orders API](#orders-api)
4. [WebSocket API](#websocket-api)
   - [Market Data Subscriptions](#market-data-subscriptions)
   - [Account Data Subscriptions](#account-data-subscriptions)
   - [Trading Operations](#websocket-trading-operations)
5. [Rate Limits](#rate-limits)
6. [Additional Resources](#additional-resources)

---

## API Overview

Pacifica is a decentralized perpetual futures exchange built on Solana, offering complete REST and WebSocket APIs for programmatic trading.

- **Official Documentation**: https://docs.pacifica.fi/api-documentation/api
- **Python SDK**: https://github.com/pacifica-fi/python-sdk
- **Support**: Discord API channel

### Base URLs

#### REST API
- **Mainnet**: `https://api.pacifica.fi`
- **Testnet**: `https://test-api.pacifica.fi`

#### WebSocket API
- **Mainnet**: `wss://ws.pacifica.fi/ws`
- **Testnet**: `wss://test-ws.pacifica.fi/ws`

---

## Authentication & Signing

All POST requests require Ed25519 signature authentication.

### Signing Process

1. **Setup and Initialization**
   - Import required libraries (time, base58, requests)
   - Generate keypair from private key
   - Extract public key

2. **Choose Endpoint and Operation Type**
   - Select specific API endpoint
   - Define operation type (e.g., "create_order")
   - Prepare operation data dictionary

3. **Create Signature Header**
   - Generate current timestamp in milliseconds
   - Create header with timestamp, expiry window, and operation type
   - Optional expiry window defaults to 30,000 milliseconds

4. **Combine Header and Payload**
   - Merge signature header with operation data
   - Ensure data is at the same level as headers

5. **Recursively Sort JSON Keys**
   - Implement a recursive sorting function
   - Alphabetically sort all dictionary keys at all levels
   - Ensures consistent message representation

6. **Create Compact JSON**
   - Convert sorted message to compact JSON string
   - Use no whitespace and standardized separators

7. **Generate Signature**
   - Convert message to UTF-8 bytes
   - Sign message using private key
   - Convert signature to Base58 string

8. **Build Final Request**
   - Construct request header with authentication info
   - Combine header with original operation data

### Operation Types

| Operation Type | Endpoint | Description |
|---------------|----------|-------------|
| `create_order` | `/api/v1/orders/create` | Create limit order |
| `create_stop_order` | `/api/v1/orders/stop/create` | Create stop order |
| `cancel_order` | `/api/v1/orders/cancel` | Cancel order |
| `cancel_all_orders` | `/api/v1/orders/cancel_all` | Cancel all orders |
| `cancel_stop_order` | `/api/v1/orders/stop/cancel` | Cancel stop order |
| `create_market_order` | `/api/v1/orders/create_market` | Create market order |
| `update_leverage` | `/api/v1/account/leverage` | Update leverage |
| `update_margin_mode` | `/api/v1/account/margin` | Update margin mode |
| `set_position_tpsl` | `/api/v1/positions/tpsl` | Set position TP/SL |
| `subaccount_initiate` | `/api/v1/account/subaccount/create` | Initiate subaccount |
| `subaccount_confirm` | `/api/v1/account/subaccount/create` | Confirm subaccount |
| `subaccount_transfer` | `/api/v1/account/subaccount/transfer` | Transfer funds |
| `withdraw` | `/api/v1/account/withdraw` | Withdraw funds |
| `bind_agent_wallet` | `/api/v1/agent/bind` | Bind agent wallet |
| `create_api_key` | `/api/v1/account/api_keys/create` | Create API key |
| `revoke_api_key` | `/api/v1/account/api_keys/revoke` | Revoke API key |
| `list_api_keys` | `/api/v1/account/api_keys` | List API keys |

### Agent Wallets

Agent wallets allow programmable trading without exposing the original wallet's private key (similar to API keys on centralized exchanges).

**Generation Methods:**
1. Frontend: https://app.pacifica.fi/apikey
2. Python SDK: Available in pacifica-fi/python-sdk repository

**Usage for POST Requests:**
1. Use original wallet's public key for `account` field
2. Sign message payload with API Agent Private Key
3. Add `"agent_wallet": "[AGENT_WALLET_PUBLIC_KEY]"` to request body

### Error Handling

| Error | Causes |
|-------|--------|
| "Invalid signature" | Invalid signature format, malformed signature bytes |
| "Invalid message" | Message expired, cannot serialize to JSON, malformed structure |
| "Invalid public key" | Invalid Ed25519 public key, malformed public key bytes |
| "Verification failed" | Signature doesn't match message, wrong private key, modified message |

---

## REST API

### Markets API

#### Get Market Info

Get comprehensive market information for all trading pairs.

**Endpoint:** `GET /api/v1/info`

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "symbol": "ETH",
      "tick_size": "0.1",
      "min_tick": "0",
      "max_tick": "1000000",
      "lot_size": "0.0001",
      "max_leverage": 50,
      "isolated_only": false,
      "min_order_size": "10",
      "max_order_size": "5000000",
      "funding_rate": "0.0000125",
      "next_funding_rate": "0.0000125"
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `symbol`: Trading pair symbol
- `tick_size`: Tick size for price increments
- `min_tick`: Minimum allowed price
- `max_tick`: Maximum allowed price
- `lot_size`: Minimum order size increment
- `max_leverage`: Maximum leverage allowed
- `isolated_only`: If market only allows isolated positions
- `min_order_size`: Minimum order size in USD
- `max_order_size`: Maximum order size in USD
- `funding_rate`: Current funding rate
- `next_funding_rate`: Estimated next funding rate

**Status Codes:**
- 200: Success
- 500: Internal server error

---

#### Get Prices

Get real-time price information for all markets.

**Endpoint:** `GET /api/v1/info/prices`

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "funding": "0.00010529",
      "mark": "1.084819",
      "mid": "1.08615",
      "next_funding": "0.00011096",
      "open_interest": "3634796",
      "oracle": "1.084524",
      "symbol": "XPL",
      "timestamp": 1759222967974,
      "volume_24h": "20896698.0672",
      "yesterday_price": "1.3412"
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `funding`: Funding rate paid in past funding epoch
- `mark`: Mark price
- `mid`: Average of best bid and ask price
- `next_funding`: Estimated funding rate for next epoch
- `open_interest`: Current open interest in USD
- `oracle`: Oracle price
- `symbol`: Trading pair symbol
- `timestamp`: Timestamp in milliseconds
- `volume_24h`: 24-hour trading volume in USD
- `yesterday_price`: Oracle price 24 hours ago

**Status Codes:**
- 200: Success
- 404: No prices data available
- 500: Internal server error

---

#### Get Kline (Candle) Data

Get historical candlestick/kline data.

**Endpoint:** `GET /api/v1/kline`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `symbol` | string | Yes | Trading pair symbol | `BTC` |
| `interval` | string | Yes | Candlestick interval | `1m` |
| `start_time` | integer | Yes | Start time in milliseconds | `1716200000000` |
| `end_time` | integer | No | End time in milliseconds (defaults to current time) | `1742243220000` |

**Valid Intervals:**
`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `8h`, `12h`, `1d`

**Request Example:**
```
/api/v1/kline?symbol=BTC&interval=1m&start_time=1742243160000&end_time=1742243220000
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "t": 1748954160000,
      "T": 1748954220000,
      "s": "BTC",
      "i": "1m",
      "o": "105376",
      "c": "105376",
      "h": "105376",
      "l": "105376",
      "v": "0.00022",
      "n": 2
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `t`: Candle start time
- `T`: Candle end time
- `s`: Symbol
- `i`: Time interval
- `o`: Open price
- `c`: Close price
- `h`: High price
- `l`: Low price
- `v`: Volume
- `n`: Number of trades

**Status Codes:**
- 200: Success
- 400: Invalid request parameters

---

#### Get Orderbook

Get current orderbook depth for a market.

**Endpoint:** `GET /api/v1/book`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `symbol` | string | Yes | Trading pair symbol | `BTC` |
| `agg_level` | integer | No | Aggregation level (default: 1) | `1` |

**Request Example:**
```
/api/v1/book?symbol=BTC
```

**Response Example:**
```json
{
  "success": true,
  "data": {
    "s": "BTC",
    "l": [
      [
        {
          "p": "106504",
          "a": "0.26203",
          "n": 1
        },
        {
          "p": "106498",
          "a": "0.29281",
          "n": 1
        }
      ],
      [
        {
          "p": "106559",
          "a": "0.26802",
          "n": 1
        },
        {
          "p": "106564",
          "a": "0.3002",
          "n": 1
        }
      ]
    ],
    "t": 1751370536325
  },
  "error": null,
  "code": null
}
```

**Response Fields:**
- `s`: Symbol
- `l`: Two-dimensional array with bids (index 0) and asks (index 1)
- `t`: Response timestamp in milliseconds
- `p`: Price level
- `a`: Total amount at price level
- `n`: Number of orders at level

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Recent Trades

Get recent trades for a specific market.

**Endpoint:** `GET /api/v1/trades`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `symbol` | string | Yes | Trading pair symbol | `BTC` |

**Request Example:**
```
/api/v1/trades?symbol=BTC
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "event_type": "fulfill_taker",
      "price": "104721",
      "amount": "0.0001",
      "side": "close_long",
      "cause": "normal",
      "created_at": 1749289837752
    }
  ]
}
```

**Response Fields:**
- `event_type`: Trade event type (`fulfill_taker` or `fulfill_maker`)
- `price`: Trade price in USD
- `amount`: Trade amount in token denomination
- `side`: Trade direction (`open_long`, `open_short`, `close_long`, `close_short`)
- `cause`: Trade cause (`normal`, `market_liquidation`, `backstop_liquidation`, `settlement`)
- `created_at`: Timestamp in milliseconds

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Historical Funding

Get historical funding rate data.

**Endpoint:** `GET /api/v1/funding_rate/history`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `symbol` | string | Yes | Market symbol | `BTC` |
| `limit` | integer | No | Number of records (default: 200, max: 4000) | `200` |
| `offset` | integer | No | Pagination offset (default: 0) | `0` |

**Request Example:**
```
/api/v1/funding_rate/history?symbol=BTC&limit=200&offset=0
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "oracle_price": "117170.410304",
      "bid_impact_price": "117126",
      "ask_impact_price": "117142",
      "funding_rate": "0.0000125",
      "next_funding_rate": "0.0000125",
      "created_at": 1753806934249
    }
  ]
}
```

**Response Fields:**
- `oracle_price`: Oracle price
- `bid_impact_price`: Bid impact price
- `ask_impact_price`: Ask impact price
- `funding_rate`: Last settled funding rate
- `next_funding_rate`: Predicted funding rate for next settlement
- `created_at`: Timestamp in milliseconds

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

### Account API

#### Get Account Info

Get comprehensive account information.

**Endpoint:** `GET /api/v1/account`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | Account address | `42trU9A5...` |

**Request Example:**
```
/api/v1/account?account=42trU9A5...
```

**Response Example:**
```json
{
  "success": true,
  "data": [{
    "balance": "2000.000000",
    "fee_level": 0,
    "account_equity": "2150.250000",
    "available_to_spend": "1800.750000",
    "pending_balance": "0.000000",
    "total_margin_used": "349.500000",
    "positions_count": 2,
    "orders_count": 3,
    "stop_orders_count": 1,
    "updated_at": 1716200000000
  }],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `balance`: Current account balance before settlement
- `fee_level`: Current fee tier based on trading volume
- `account_equity`: Account balance + unrealized PnL
- `available_to_spend`: Equity available for margin and orders
- `pending_balance`: Balance awaiting confirmation
- `total_margin_used`: Equity currently used for positions/orders
- `positions_count`: Number of open positions
- `orders_count`: Number of open orders
- `stop_orders_count`: Number of open stop orders
- `updated_at`: Last update timestamp

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Account Settings

Get account settings for leverage and margin mode per market.

**Endpoint:** `GET /api/v1/account/settings`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | Account address | `42trU9A5...` |

**Request Example:**
```
/api/v1/account/settings?account=42trU9A5...
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "symbol": "WLFI",
      "isolated": false,
      "leverage": 5,
      "created_at": 1758085929703,
      "updated_at": 1758086074002
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `symbol`: Trading pair symbol
- `isolated`: Boolean indicating if account uses isolated margining
- `leverage`: Current user-set leverage
- `created_at`: Timestamp when settings were first adjusted from defaults
- `updated_at`: Timestamp of most recent settings update

**Special Notes:**
- Upon account creation, all markets default to cross margin and maximum leverage
- Markets with default settings will return blank in the response

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Update Leverage

Update leverage for a specific market.

**Endpoint:** `POST /api/v1/account/leverage`

**Operation Type:** `update_leverage`

**Request Body Parameters:**
| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `symbol` | string | Yes | Trading pair symbol | `BTC` |
| `leverage` | integer | Yes | New leverage value | `10` |
| `timestamp` | integer | Yes | Current timestamp in milliseconds | `1716200000000` |
| `signature` | string | Yes | Cryptographic signature | `5j1Vy9Uq...` |
| `expiry_window` | integer | No | Signature expiry in milliseconds | `30000` |
| `agent_wallet` | string | No | Agent wallet address | `69trU9A5...` |

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "symbol": "BTC",
  "leverage": 10,
  "timestamp": 1716200000000,
  "expiry_window": 30000,
  "agent_wallet": "69trU9A5...",
  "signature": "5j1Vy9UqY..."
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true
}
```

Error (400):
```json
{
  "error": "Invalid leverage",
  "code": 400
}
```

**Special Notes:**
- For open positions, users can only increase the leverage setting

**Status Codes:**
- 200: Success
- 400: Invalid leverage
- 500: Internal server error

---

#### Update Margin Mode

Update margin mode (isolated/cross) for a specific market.

**Endpoint:** `POST /api/v1/account/margin`

**Operation Type:** `update_margin_mode`

**Request Body Parameters:**
| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `symbol` | string | Yes | Trading pair symbol | `BTC` |
| `is_isolated` | boolean | Yes | Margin mode (true=isolated, false=cross) | `false` |
| `timestamp` | integer | Yes | Current timestamp in milliseconds | `1716200000000` |
| `signature` | string | Yes | Cryptographic signature | `5j1Vy9Uq...` |
| `expiry_window` | integer | No | Signature expiry in milliseconds | `30000` |
| `agent_wallet` | string | No | Agent wallet address | `69trU9A5...` |

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "symbol": "BTC",
  "is_isolated": false,
  "timestamp": 1716200000000,
  "expiry_window": 30000,
  "agent_wallet": "69trU9A5...",
  "signature": "5j1Vy9Uq..."
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true
}
```

Error (400):
```json
{
  "error": "Invalid margin mode",
  "code": 400
}
```

**Special Notes:**
- For open positions, users cannot change the margin mode

**Status Codes:**
- 200: Success
- 400: Invalid margin mode
- 500: Internal server error

---

#### Get Positions

Get all open positions for an account.

**Endpoint:** `GET /api/v1/positions`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | Connected wallet address | `42trU9A5...` |

**Request Example:**
```
/api/v1/positions?account=42trU9A5...
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "symbol": "AAVE",
      "side": "ask",
      "amount": "223.72",
      "entry_price": "279.283134",
      "margin": "0",
      "funding": "13.159593",
      "isolated": false,
      "created_at": 1754928414996,
      "updated_at": 1759223365538
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `symbol`: Trading pair symbol
- `side`: Whether the position is long/short
- `entry_price`: Entry price of the position (VWAP if multiple trades)
- `margin`: Margin allocated to isolated position (only shown when isolated)
- `funding`: Funding paid by this position since open
- `isolated`: If position is in isolated margin mode
- `created_at`: Timestamp when settings were first adjusted
- `updated_at`: Timestamp of last update

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Trade History

Get historical trade data for an account.

**Endpoint:** `GET /api/v1/positions/history`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `symbol` | string | No | Market symbol to filter trades | `BTC` |
| `start_time` | integer | No | Start time in milliseconds | `1625097600000` |
| `end_time` | integer | No | End time in milliseconds | `1625184000000` |
| `limit` | integer | No | Maximum number of records | `100` |
| `offset` | integer | No | Number of records to skip | `0` |

**Request Example:**
```
/api/v1/positions/history?account=42trU9A5...&start_time=1625097600000&end_time=1625184000000&limit=100
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "history_id": 19329801,
      "order_id": 315293920,
      "client_order_id": "acf...",
      "symbol": "LDO",
      "amount": "0.1",
      "price": "1.1904",
      "entry_price": "1.176247",
      "fee": "0",
      "pnl": "-0.001415",
      "event_type": "fulfill_maker",
      "side": "close_short",
      "created_at": 1759215599188,
      "cause": "normal"
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `history_id`: Trade history identifier
- `order_id`: Associated order ID
- `client_order_id`: Client-side order identifier
- `symbol`: Trading pair symbol
- `amount`: Trade amount
- `price`: Trade price
- `entry_price`: Position entry price
- `fee`: Trading fee
- `pnl`: Profit and loss
- `event_type`: Trade event type
- `side`: Trade side
- `created_at`: Timestamp
- `cause`: Trade cause

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Funding History

Get funding payment history for an account.

**Endpoint:** `GET /api/v1/funding/history`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | Trading pair symbol | `42trU9A5...` |
| `limit` | integer | No | Maximum number of records | `100` |
| `offset` | integer | No | Number of records to skip | `0` |

**Request Example:**
```
/api/v1/funding/history?account=42trU9A5...&limit=100&offset=0
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "history_id": 2287920,
      "symbol": "PUMP",
      "side": "ask",
      "amount": "39033804",
      "payout": "2.617479",
      "rate": "0.0000125",
      "created_at": 1759222804122
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `history_id`: Unique identifier for trade history
- `symbol`: Trading pair symbol
- `side`: Position side (long/short)
- `amount`: Position amount in token denomination
- `payout`: Funding paid in USD
- `rate`: Funding rate used for calculation
- `created_at`: Timestamp of funding payment

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Account Equity History

Get historical account equity data.

**Endpoint:** `GET /api/v1/portfolio`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `start_time` | integer | No | Start time in milliseconds | `1625097600000` |
| `end_time` | integer | No | End time in milliseconds | `1625184000000` |
| `granularity_in_minutes` | integer | No | Time granularity in minutes | `60` |
| `limit` | integer | No | Maximum number of records | `100` |
| `offset` | integer | No | Number of records to skip | `0` |

**Request Example:**
```
/api/v1/portfolio?account=42trU9A5...&start_time=1625097600000&end_time=1625184000000&granularity_in_minutes=60&limit=100
```

**Response Example:**
```json
[
  {
    "account_equity": "997.88760080",
    "timestamp": 1748956140000
  },
  {
    "account_equity": "997.98277520",
    "timestamp": 1748956080000
  }
]
```

**Response Fields:**
- `account_equity`: Account equity (balance + unrealized PnL) at last update
- `timestamp`: Timestamp in milliseconds of last account equity update

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Account Balance History

Get historical balance changes for an account.

**Endpoint:** `GET /api/v1/account/balance/history`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `limit` | integer | No | Maximum number of records | `100` |
| `offset` | integer | No | Number of records to skip | `0` |

**Request Example:**
```
/api/v1/account/balance/history?account=42trU9A5...
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "amount": "100.000000",
      "balance": "1200.000000",
      "pending_balance": "0.000000",
      "event_type": "deposit",
      "created_at": 1716200000000
    }
  ]
}
```

**Response Fields:**
- `amount`: Balance change amount
- `balance`: Account balance after event
- `pending_balance`: Pending balance
- `event_type`: Type of balance event
- `created_at`: Timestamp in milliseconds

**Event Types:**
- `deposit`
- `deposit_release`
- `withdraw`
- `trade`
- `market_liquidation`
- `backstop_liquidation`
- `adl_liquidation`
- `subaccount_transfer`
- `funding`
- `payout`

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Request Withdrawal

Request a withdrawal from the account.

**Endpoint:** `POST /api/v1/account/withdraw`

**Operation Type:** `withdraw`

**Request Body Parameters:**
| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `signature` | string | Yes | Cryptographic signature | `5j1Vy9Uq...` |
| `timestamp` | integer | Yes | Current timestamp in milliseconds | `1716200000000` |
| `amount` | string | Yes | Amount to withdraw in USDC | `100.50` |
| `agent_wallet` | string | No | Agent wallet address | `69trU9A5...` |
| `expiry_window` | integer | No | Signature expiry in milliseconds | `30000` |

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "signature": "5j1Vy9Uq...",
  "timestamp": 1716200000000,
  "amount": "100.50",
  "agent_wallet": "69trU9A5...",
  "expiry_window": 30000
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true
}
```

**Special Notes:**
- Pacifica currently limits single account withdrawals up to a maximum of $25,000 every 24 hours for security purposes
- Unrealized PnL can be withdrawn from isolated positions or cross-margined account

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 500: Internal server error

---

### Subaccounts API

#### Create Subaccount

Create a new subaccount.

**Endpoint:** `POST /api/v1/account/subaccount/create`

**Operation Types:** `subaccount_initiate`, `subaccount_confirm`

**Request Body Parameters:**
| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `main_account` | string | Yes | Main account wallet address | `42trU9A5...` |
| `subaccount` | string | Yes | Subaccount wallet address | `69trU9A5...` |
| `timestamp` | integer | Yes | Current timestamp in milliseconds | `1716200000000` |
| `main_signature` | string | Yes | Main account signature | `5j1Vy9Uq...` |
| `sub_signature` | string | Yes | Subaccount signature | `4k2Wx8Zq...` |
| `expiry_window` | integer | No | Signature expiry in milliseconds | `30000` |

**Request Example:**
```json
{
  "main_account": "42trU9A5...",
  "subaccount": "69trU9A5...",
  "main_signature": "5j1Vy9Uq...",
  "sub_signature": "4k2Wx8Zq...",
  "timestamp": 1716200000000,
  "expiry_window": 30000
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true,
  "data": null,
  "error": null,
  "code": null
}
```

Error (400):
```json
{
  "success": false,
  "data": null,
  "error": "Account already exists: CRTxBM...",
  "code": 2
}
```

**Special Notes:**
- Requires signatures from both main account and subaccount

**Status Codes:**
- 200: Success
- 400: Account already exists
- 500: Internal server error

---

#### Subaccount Fund Transfer

Transfer funds between main account and subaccount.

**Endpoint:** `POST /api/v1/account/subaccount/transfer`

**Operation Type:** `subaccount_transfer`

**Request Body Parameters:**
| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `account` | string | Yes | Sender account address | `42trU9A5...` |
| `signature` | string | Yes | Sender account signature | `5j1Vy9Uq...` |
| `timestamp` | integer | Yes | Current timestamp in milliseconds | `1716200000000` |
| `to_account` | string | Yes | Recipient wallet address | `69trU9A5...` |
| `amount` | string | Yes | Transfer amount (in USDC) | `420.69` |
| `expiry_window` | integer | No | Signature expiry in milliseconds | `30000` |

**Request Example:**
```json
{
  "account": "AwX6321...",
  "signature": "65L9qPp...",
  "timestamp": 1749228826313,
  "expiry_window": 5000,
  "to_account": "CRTxBM...",
  "amount": "420.69"
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true,
  "data": {
    "success": true,
    "error": null
  },
  "error": null,
  "code": null
}
```

Error (400):
```json
{
  "success": false,
  "data": null,
  "error": "Insufficient balance for AwX6321: 420.69 (account value: 336.91)",
  "code": 5
}
```

**Status Codes:**
- 200: Success
- 400: Insufficient balance or invalid parameters
- 500: Internal server error

---

### Orders API

#### Create Market Order

Create a new market order with optional take profit and stop loss.

**Endpoint:** `POST /api/v1/orders/create_market`

**Operation Type:** `create_market_order`

**Request Body Parameters:**

**Required:**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `account` | string | User's wallet address | `42trU9A5...` |
| `signature` | string | Cryptographic signature | `5j1Vy9Uq` |
| `timestamp` | integer | Current timestamp in milliseconds | `1716200000000` |
| `symbol` | string | Trading pair symbol | `BTC` |
| `amount` | string | Order amount | `0.1` |
| `side` | string | Order side: "bid" or "ask" | `bid` |
| `slippage_percent` | string | Maximum slippage tolerance (e.g. "0.5" = 0.5%) | `0.5` |
| `reduce_only` | boolean | Whether the order is reduce-only | `false` |

**Optional:**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `client_order_id` | string | Client-defined order ID (Full UUID) | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |
| `take_profit` | object | Take profit stop order configuration | See below |
| `stop_loss` | object | Stop loss order configuration | See below |
| `agent_wallet` | string | Agent wallet address | `69trU9A5...` |
| `expiry_window` | integer | Signature expiry in milliseconds | `30000` |

**Take Profit / Stop Loss Object:**
- `stop_price` (string): Stop trigger price
- `limit_price` (string, optional): Limit price for triggered order
- `client_order_id` (string, optional): Client-defined order ID (Full UUID)

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "signature": "5j1Vy9Uq",
  "timestamp": 1716200000000,
  "symbol": "BTC",
  "amount": "0.1",
  "side": "bid",
  "slippage_percent": "0.5",
  "reduce_only": false,
  "take_profit": {
    "stop_price": "55000",
    "limit_price": "54950"
  },
  "stop_loss": {
    "stop_price": "48000",
    "limit_price": "47950"
  }
}
```

**Response Examples:**

Success (200):
```json
{
  "order_id": 12345
}
```

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 500: Internal server error

---

#### Create Limit Order

Create a new limit order.

**Endpoint:** `POST /api/v1/orders/create`

**Operation Type:** `create_order`

**Request Body Parameters:**

**Required:**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `account` | string | User's wallet address | `42trU9A5...` |
| `signature` | string | Cryptographic signature | `5j1Vy9Uq` |
| `timestamp` | integer | Current timestamp in milliseconds | `1716200000000` |
| `symbol` | string | Trading pair symbol | `BTC` |
| `price` | string | Order price | `50000` |
| `amount` | string | Order amount | `0.1` |
| `side` | string | Order side: "bid" or "ask" | `bid` |
| `tif` | string | Time in force: GTC, IOC, ALO | `GTC` |
| `reduce_only` | boolean | Whether the order is reduce-only | `false` |

**Optional:**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `client_order_id` | string | Client-defined order ID (UUID) | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |
| `take_profit` | object | Take profit stop order configuration | See market order |
| `stop_loss` | object | Stop loss order configuration | See market order |
| `agent_wallet` | string | Agent wallet address | `69trU9A5...` |
| `expiry_window` | integer | Signature expiry in milliseconds | `30000` |

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "signature": "5j1Vy9Uq",
  "timestamp": 1716200000000,
  "symbol": "BTC",
  "price": "50000",
  "amount": "0.1",
  "side": "bid",
  "tif": "GTC",
  "reduce_only": false
}
```

**Response Examples:**

Success (200):
```json
{
  "order_id": 12345
}
```

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 500: Internal server error

---

#### Create Stop Order

Create a new stop order.

**Endpoint:** `POST /api/v1/orders/stop/create`

**Operation Type:** `create_stop_order`

**Request Body Parameters:**

**Required:**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `account` | string | User's wallet address | `42trU9A5...` |
| `signature` | string | Cryptographic signature | `5j1Vy9Uq...` |
| `timestamp` | integer | Current timestamp in milliseconds | `1716200000000` |
| `symbol` | string | Trading pair symbol | `BTC` |
| `side` | string | Order side: "bid" or "ask" | `long` |
| `reduce_only` | boolean | Whether the order is reduce-only | `true` |
| `stop_order` | object | Stop order configuration | See below |

**Stop Order Object (Required fields):**
- `stop_price` (string, required): Stop trigger price
- `amount` (string, required): Order amount

**Stop Order Object (Optional fields):**
- `limit_price` (string): Limit price for triggered order
- `client_order_id` (string): Client-defined order ID (full UUID)

**Optional:**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `agent_wallet` | string | Agent wallet address | `69trU9A5...` |
| `expiry_window` | integer | Signature expiry in milliseconds | `30000` |

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "signature": "5j1Vy9Uq...",
  "timestamp": 1716200000000,
  "symbol": "BTC",
  "side": "long",
  "reduce_only": true,
  "stop_order": {
    "stop_price": "48000",
    "limit_price": "47950",
    "client_order_id": "d25ac10b-58cc-4372-a567-0e02b2c3d479",
    "amount": "0.1"
  }
}
```

**Response Examples:**

Success (200):
```json
{
  "order_id": 12345
}
```

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 500: Internal server error

---

#### Create Position TP/SL

Set or update take profit and stop loss for an existing position.

**Endpoint:** `POST /api/v1/positions/tpsl`

**Operation Type:** `set_position_tpsl`

**Request Body Parameters:**

**Required:**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `account` | string | User's wallet address | `42trU9A5...` |
| `signature` | string | Cryptographic signature | `5j1Vy9Uq...` |
| `timestamp` | integer | Current timestamp in milliseconds | `1716200000000` |
| `symbol` | string | Trading pair symbol | `BTC` |
| `side` | string | Order side: "bid" or "ask" | `bid` |

**Optional (at least one required):**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `take_profit` | object | Take profit configuration | See below |
| `stop_loss` | object | Stop loss configuration | See below |
| `agent_wallet` | string | Agent wallet address | `69trU9A5...` |
| `expiry_window` | integer | Signature expiry in milliseconds | `30000` |

**Take Profit / Stop Loss Object:**
- `stop_price` (string, required if object used): Stop trigger price
- `limit_price` (string, optional): Limit price for triggered order
- `client_order_id` (string, optional): Custom order ID (UUID)

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "signature": "5j1Vy9Uq...",
  "timestamp": 1716200000000,
  "symbol": "BTC",
  "side": "bid",
  "take_profit": {
    "stop_price": "55000",
    "limit_price": "54950"
  },
  "stop_loss": {
    "stop_price": "48000",
    "limit_price": "47950"
  }
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true
}
```

Error (400):
```json
{
  "error": "Position not found",
  "code": 400
}
```

**Special Notes:**
- At least one of `take_profit` or `stop_loss` must be provided
- Prices should be valid and within reasonable market ranges

**Status Codes:**
- 200: Success
- 400: Position not found or invalid parameters
- 500: Internal server error

---

#### Cancel Order

Cancel an existing order by its order ID or client order ID.

**Endpoint:** `POST /api/v1/orders/cancel`

**Operation Type:** `cancel_order`

**Request Body Parameters:**
| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `signature` | string | Yes | Cryptographic signature | `5j1Vy9Uq...` |
| `timestamp` | integer | Yes | Current timestamp in milliseconds | `1716200000000` |
| `symbol` | string | Yes | Trading pair symbol | `BTC` |
| `order_id` | integer | Yes* | Exchange-assigned order ID | `123` |
| `client_order_id` | string | Yes* | Client-defined order ID | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |
| `agent_wallet` | string | No | Agent wallet address | `69trU9A5...` |
| `expiry_window` | integer | No | Signature expiry in milliseconds | `30000` |

*Note: Either `order_id` or `client_order_id` is required

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "signature": "5j1Vy9Uq...",
  "timestamp": 1716200000000,
  "symbol": "BTC",
  "order_id": 123
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true
}
```

Error (400):
```json
{
  "error": "Order not found",
  "code": 400
}
```

**Status Codes:**
- 200: Success
- 400: Order not found
- 500: Internal server error

---

#### Cancel All Orders

Cancel all open orders for a symbol or all symbols.

**Endpoint:** `POST /api/v1/orders/cancel_all`

**Operation Type:** `cancel_all_orders`

**Request Body Parameters:**
| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `signature` | string | Yes | Cryptographic signature | `5j1Vy9Uq...` |
| `timestamp` | integer | Yes | Current timestamp in milliseconds | `1716200000000` |
| `all_symbols` | boolean | Yes | Whether to cancel orders for all symbols | `true` |
| `exclude_reduce_only` | boolean | Yes | Whether to exclude reduce-only orders | `false` |
| `symbol` | string | Conditional | Trading pair symbol (required if `all_symbols` is false) | `BTC` |
| `agent_wallet` | string | No | Agent wallet address | `69trU9A5...` |
| `expiry_window` | integer | No | Signature expiry in milliseconds | `30000` |

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "signature": "5j1Vy9Uq...",
  "timestamp": 1716200000000,
  "all_symbols": true,
  "exclude_reduce_only": false,
  "symbol": "BTC",
  "agent_wallet": "69trU9A5...",
  "expiry_window": 30000
}
```

**Response Examples:**

Success (200):
```json
{
  "cancelled_count": 5
}
```

Error (400):
```json
{
  "error": "Invalid parameters",
  "code": 400
}
```

**Status Codes:**
- 200: Success
- 400: Bad request
- 500: Internal server error

---

#### Cancel Stop Order

Cancel a stop order by its order ID or client order ID.

**Endpoint:** `POST /api/v1/orders/stop/cancel`

**Operation Type:** `cancel_stop_order`

**Request Body Parameters:**
| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `account` | string | Yes | User's wallet address | `42trU9A5...` |
| `signature` | string | Yes | Cryptographic signature | `5j1Vy9Uq...` |
| `timestamp` | integer | Yes | Current timestamp in milliseconds | `1716200000000` |
| `symbol` | string | Yes | Trading pair symbol | `BTC` |
| `order_id` | integer | Yes* | Exchange-assigned order ID | `123` |
| `client_order_id` | string | Yes* | Client-defined order ID (full UUID) | `f47ac10b-58cc-4372-a567-0e02b2c3d479` |
| `agent_wallet` | string | No | Agent wallet address | `69trU9A5...` |
| `expiry_window` | integer | No | Signature expiry in milliseconds | `30000` |

*Note: Either `order_id` or `client_order_id` is required

**Request Example:**
```json
{
  "account": "42trU9A5...",
  "signature": "5j1Vy9Uq...",
  "timestamp": 1716200000000,
  "symbol": "BTC",
  "order_id": 123,
  "agent_wallet": "69trU9A5...",
  "expiry_window": 30000
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true
}
```

Error (400):
```json
{
  "error": "Stop order not found",
  "code": 400
}
```

**Status Codes:**
- 200: Success
- 400: Stop order not found
- 500: Internal server error

---

#### Batch Order

Submit multiple order operations (create/cancel) in a single request.

**Endpoint:** `POST /api/v1/orders/batch`

**Special Note:** The batch order endpoint does not have a corresponding operation type, as individual operations within the batch are signed independently.

**Request Body Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `actions` | array | Yes | Array of order actions |

**Action Object:**
- `type` (string, required): Either "Create" or "Cancel" (case-sensitive)
- `data` (object, required): Signed request payload for individual action

**Request Example:**
```json
{
   "actions":[
      {
         "type":"Create",
         "data":{
            "account":"42trU9A5...",
            "signature":"5UpRZ14Q...",
            "timestamp":1749190500355,
            "expiry_window":5000,
            "symbol":"BTC",
            "price":"100000",
            "reduce_only":false,
            "amount":"0.1",
            "side":"bid",
            "tif":"GTC",
            "client_order_id":"57a5efb1-bb96-49a5-8bfd-f25d5f22bc7e"
         }
      },
      {
         "type":"Cancel",
         "data":{
            "account":"42trU9A5...",
            "signature":"4NDFHyTG...",
            "timestamp":1749190500355,
            "expiry_window":5000,
            "symbol":"BTC",
            "order_id":42069
         }
      }
   ]
}
```

**Response Examples:**

Success (200):
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "success": true,
        "order_id": 470506,
        "error": null
      },
      {
        "success": true
      }
    ]
  },
  "error": null,
  "code": null
}
```

Error (400):
```json
{
  "error": "Invalid batch request",
  "code": 400
}
```

**Special Notes:**
- Batched orders are executed in the order they are batched in
- Will not be split up by other users' orders
- Messages and corresponding fields are identical to create and cancel requests

**Status Codes:**
- 200: Success
- 400: Invalid batch request
- 500: Internal server error

---

#### Get Open Orders

Get all open orders for an account.

**Endpoint:** `GET /api/v1/orders`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | Account address to filter orders | `42trU9A5...` |

**Request Example:**
```
/api/v1/orders?account=42trU9A5...
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "order_id": 315979358,
      "client_order_id": "add9a4b5-c7f7-4124-b57f-86982d86d479",
      "symbol": "ASTER",
      "side": "ask",
      "price": "1.836",
      "initial_amount": "85.33",
      "filled_amount": "0",
      "cancelled_amount": "0",
      "stop_price": null,
      "order_type": "limit",
      "stop_parent_order_id": null,
      "reduce_only": false,
      "created_at": 1759224706737,
      "updated_at": 1759224706737
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `order_id`: Unique order identifier
- `client_order_id`: User-assigned order ID
- `symbol`: Trading pair symbol
- `side`: Order direction (bid/ask)
- `price`: Order price
- `initial_amount`: Total order amount
- `filled_amount`: Amount filled
- `cancelled_amount`: Amount cancelled
- `stop_price`: Optional stop price
- `order_type`: Order type (limit, market, etc.)
- `stop_parent_order_id`: Related stop order ID
- `reduce_only`: Whether order is reduce-only
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Order History

Get historical orders for an account.

**Endpoint:** `GET /api/v1/orders/history`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account` | string | Yes | Account address to filter orders | `42trU9A5...` |
| `limit` | integer | No | Maximum number of records to return | `100` |
| `offset` | integer | No | Number of records to skip | `0` |

**Request Example:**
```
/api/v1/orders/history?account=42trU9A5...&limit=100&offset=0
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "order_id": 315992721,
      "client_order_id": "ade",
      "symbol": "XPL",
      "side": "ask",
      "initial_price": "1.0865",
      "average_filled_price": "0",
      "amount": "984",
      "filled_amount": "0",
      "order_status": "open",
      "order_type": "limit",
      "stop_price": null,
      "stop_parent_order_id": null,
      "reduce_only": false,
      "reason": null,
      "created_at": 1759224893638,
      "updated_at": 1759224893638
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `order_id`: Unique order identifier
- `client_order_id`: User-assigned order ID
- `symbol`: Trading pair symbol
- `side`: Order direction
- `initial_price`: Initial order price
- `average_filled_price`: Average fill price
- `amount`: Order amount
- `filled_amount`: Amount filled
- `order_status`: Current order status
- `order_type`: Order type
- `stop_price`: Optional stop price
- `stop_parent_order_id`: Related stop order ID
- `reduce_only`: Whether reduce-only
- `reason`: Cancellation/rejection reason
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

#### Get Order History by ID

Get detailed history for a specific order.

**Endpoint:** `GET /api/v1/orders/history_by_id`

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `order_id` | integer | Yes | Order ID to retrieve history for | `13753364` |

**Request Example:**
```
/api/v1/orders/history_by_id?order_id=13753364
```

**Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "history_id": 641452639,
      "order_id": 315992721,
      "client_order_id": "ade1aa6...",
      "symbol": "XPL",
      "side": "ask",
      "price": "1.0865",
      "initial_amount": "984",
      "filled_amount": "0",
      "cancelled_amount": "984",
      "event_type": "cancel",
      "order_type": "limit",
      "order_status": "cancelled",
      "stop_price": null,
      "stop_parent_order_id": null,
      "reduce_only": false,
      "created_at": 1759224895038
    }
  ],
  "error": null,
  "code": null
}
```

**Response Fields:**
- `history_id`: Unique history record identifier
- `order_id`: Original order identifier
- `client_order_id`: User-assigned order ID
- `symbol`: Trading pair
- `side`: Order direction (bid/ask)
- `price`: Order price
- `initial_amount`: Original order amount
- `filled_amount`: Executed amount
- `cancelled_amount`: Cancelled amount
- `event_type`: Order event (make/take/cancel)
- `order_type`: Order classification
- `order_status`: Current order state
- `stop_price`: Conditional order trigger price
- `stop_parent_order_id`: Related stop order ID
- `reduce_only`: Reduces-only flag
- `created_at`: Timestamp of order creation

**Status Codes:**
- 200: Success
- 400: Invalid request parameters
- 401: Unauthorized access
- 500: Internal server error

---

## WebSocket API

### Connection

**WebSocket URLs:**
- **Mainnet:** `wss://ws.pacifica.fi/ws`
- **Testnet:** `wss://test-ws.pacifica.fi/ws`

**Connection Characteristics:**
- Connection will close if no message sent for 60 seconds
- Maximum connection lifetime is 24 hours
- Universal endpoint for all websocket streams

**Heartbeat Mechanism:**

To keep connection alive, send ping:
```json
{
    "method": "ping"
}
```

Server responds with:
```json
{
    "channel": "pong"
}
```

---

### Subscription Format

**Subscribe to a channel:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "channel_name",
        // additional parameters
    }
}
```

**Unsubscribe from a channel:**
```json
{
    "method": "unsubscribe",
    "params": {
        "source": "channel_name",
        // additional parameters
    }
}
```

---

### Market Data Subscriptions

#### Prices Subscription

Streams all symbols' price information in real-time.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "prices"
    }
}
```

**Stream Response:**
```json
{
    "channel": "prices",
    "data": [
        {
            "symbol": "BTC",
            "funding": "0.0000125",
            "mark": "105473",
            "mid": "105476",
            "oracle": "105473",
            "timestamp": 1749051612681,
            "volume_24h": "63265.87522",
            "next_funding": "0.0000125",
            "open_interest": "0.00524",
            "yesterday_price": "955476"
        }
    ]
}
```

**Response Fields:**
- `symbol`: Trading symbol
- `funding`: Current funding rate
- `mark`: Mark price
- `mid`: Mid price
- `oracle`: Oracle price
- `timestamp`: Update timestamp (milliseconds)
- `volume_24h`: 24-hour trading volume in USD
- `next_funding`: Upcoming funding rate
- `open_interest`: Total open interest amount
- `yesterday_price`: Previous day's closing price

---

#### Orderbook Subscription

Streams orderbook data for a given symbol at a set aggregation level.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "book",
        "symbol": "SOL",
        "agg_level": 1
    }
}
```

**Aggregation Levels:** 1, 2, 5, 10, 100, 1000

**Stream Response:**
```json
{
  "channel": "book",
  "data": {
    "l": [
      [
        {
          "p": "157.43",
          "a": "10.5",
          "n": 3
        }
      ],
      [
        {
          "p": "157.45",
          "a": "8.2",
          "n": 2
        }
      ]
    ],
    "s": "SOL",
    "t": 1749051881187
  }
}
```

**Response Fields:**
- `l`: Array containing [Bids, Asks]
- `p`: Price level
- `a`: Total amount at aggregation level
- `n`: Number of orders at aggregation level
- `s`: Symbol
- `t`: Timestamp in milliseconds

---

#### Trades Subscription

Streams recent trades for a given symbol.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "trades",
        "symbol": "SOL"
    }
}
```

**Stream Response:**
```json
{
  "channel": "trades",
  "data": [
      {
        "a": "0.16",
        "d": "open_long",
        "e": "fulfill_maker",
        "p": "157.43",
        "s": "SOL",
        "t": 1749052438829,
        "tc": "normal",
        "u": "C1obSQwr..."
      }
  ]
}
```

**Response Fields:**
- `a`: Trade amount
- `d`: Trade side (open_long, open_short, close_long, close_short)
- `e`: Trade event type (fulfill_taker, fulfill_maker)
- `p`: Price
- `s`: Market symbol
- `t`: Timestamp in milliseconds
- `tc`: Trade cause (normal, market_liquidation, backstop_liquidation, settlement)
- `u`: Account address

---

#### Candle Subscription

Streams candle information for a given symbol and time interval.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "candle",
        "symbol": "SOL",
        "interval": "1m"
    }
}
```

**Supported Intervals:** 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d

**Stream Response:**
```json
{
  "channel": "candle",
  "data": {
    "t": 1749052260000,
    "T": 1749052320000,
    "s": "SOL",
    "i": "1m",
    "o": "157.3",
    "c": "157.32",
    "h": "157.32",
    "l": "157.3",
    "v": "1.22",
    "n": 8
  }
}
```

**Response Fields:**
- `t`: Start time (milliseconds)
- `T`: End time (milliseconds)
- `s`: Symbol
- `i`: Interval
- `o`: Open price
- `c`: Close price
- `h`: High price
- `l`: Low price
- `v`: Volume
- `n`: Number of trades

---

### Account Data Subscriptions

#### Account Balance Subscription

Streams all updates to total, available, and locked balance.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "account_balance",
        "account": "42trU9A5..."
    }
}
```

**Stream Response:**
```json
{
    "channel": "account_balance",
    "data": {
        "total": "100000.50",
        "available": "75000.25",
        "locked": "25000.25",
        "t": 1234567890
    }
}
```

**Response Fields:**
- `total`: Total account balance
- `available`: Funds currently available
- `locked`: Funds locked in margin/orders
- `t`: Timestamp in milliseconds

---

#### Account Margin Subscription

Streams all changes to account's margin mode in any market.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "account_margin",
        "account": "42trU9A5..."
    }
}
```

**Stream Response:**
```json
{
    "channel": "account_margin",
    "data": {
        "u": "42trU9A5...",
        "s": "ETH",
        "i": true,
        "t": 1234567890
    }
}
```

**Response Fields:**
- `u`: Account address
- `s`: Trading symbol
- `i`: Margin mode (true = isolated)
- `t`: Timestamp in milliseconds

---

#### Account Leverage Subscription

Streams all changes to account's max leverage for any market.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "account_leverage",
        "account": "42trU9A5..."
    }
}
```

**Stream Response:**
```json
{
    "channel": "account_leverage",
    "data": {
        "u": "42trU9A5...",
        "s": "BTC",
        "l": "12",
        "t": 1234567890
    }
}
```

**Response Fields:**
- `u`: Account address
- `s`: Market/symbol
- `l`: New leverage value
- `t`: Timestamp in milliseconds

---

#### Account Info Subscription

Streams all changes to account's overall info (equity, balance, order count, etc.).

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "account_info",
        "account": "42trU9A5..."
    }
}
```

**Stream Response:**
```json
{
    "channel": "account_info",
    "data": {
        "ae": "2000",
        "as": "1500",
        "b": "2000",
        "f": 1,
        "mu": "500",
        "oc": 10,
        "pb": "0",
        "pc": 2,
        "sc": 2,
        "t": 1234567890
    }
}
```

**Response Fields:**
- `ae`: Account equity
- `as`: Available to spend
- `b`: Account balance
- `f`: Account fee tier
- `mu`: Total margin used
- `oc`: Orders count
- `pb`: Pending balance
- `pc`: Positions count
- `sc`: Stop order count
- `t`: Timestamp in milliseconds

---

#### Account Positions Subscription

Streams all changes to account's positions in any market.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "account_positions",
        "account": "42trU9A5..."
    }
}
```

**Stream Response:**
```json
{
    "channel": "account_positions",
    "data": [
        {
            "s": "LINK",
            "a": "3.1",
            "p": "14.156000000000",
            "d": "ask",
            "t": 1749051466633,
            "m": "0",
            "f": "0",
            "i": false
        }
    ]
}
```

**Response Fields:**
- `s`: Symbol
- `a`: Position amount
- `p`: Average entry price
- `d`: Position side (bid/ask)
- `t`: Timestamp in milliseconds
- `m`: Position margin
- `f`: Funding rate
- `i`: Isolated position flag

**Note:** A fully closed position will return an empty data array.

---

#### Account Orders Subscription

Streams all changes to account's open orders in any market.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "account_orders",
        "account": "42trU9A5..."
    }
}
```

**Stream Response:**
```json
{
  "channel": "account_orders",
  "data": [
    {
      "I": null,
      "a": "29580",
      "c": "0",
      "d": "bid",
      "f": "0",
      "i": 560509,
      "p": "0.27046",
      "ot": "limit",
      "ro": false,
      "s": "XLM",
      "sp": null,
      "st": null,
      "t": 1749054246822
    }
  ]
}
```

**Response Fields:**
- `I`: Client order ID (UUID)
- `a`: Original amount
- `c`: Cancelled amount
- `d`: Side (bid/ask)
- `f`: Filled amount
- `i`: Order ID
- `ot`: Order type
- `ro`: Reduce only flag
- `s`: Symbol
- `sp`: Stop price
- `st`: Stop type
- `t`: Timestamp

**Order Events (oe):**
- `make`: Order placed
- `stop_created`: Stop order created
- `cancel`: User cancelled
- `filled`: Order completed

**Order Statuses (os):**
- `open`
- `partially_filled`
- `filled`
- `cancelled`
- `rejected`

**Note:** An order that has been cancelled/filled will be streamed and return empty.

---

#### Account Order Updates Subscription

Streams the amount and nature of changes to any of account's open orders.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "account_order_updates",
        "account": "42trU9A5..."
    }
}
```

**Stream Response:**
```json
{
  "channel": "account_order_updates",
  "data": [
    {
      "i": 622900,
      "s": "TRUMP",
      "d": "bid",
      "p": "10.979",
      "a": "91.1",
      "f": "2.1",
      "oe": "fulfill_limit",
      "os": "partially_filled",
      "ot": "limit"
    }
  ]
}
```

**Response Fields:**
- `i`: Order ID
- `s`: Symbol
- `d`: Side (bid/ask)
- `p`: Average filled price
- `a`: Original amount
- `f`: Filled amount
- `oe`: Order event type
- `os`: Order status
- `ot`: Order type

**Order Event Types:**
- `make`
- `stop_created`
- `fulfill_market`
- `cancel`
- `expired`

**Order Statuses:**
- `open`
- `partially_filled`
- `filled`
- `cancelled`
- `rejected`

---

#### Account Trades Subscription

Streams all trades that take place for an account.

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "source": "account_trades",
        "account": "42trU9A5..."
    }
}
```

**Stream Response:**
```json
{
  "channel": "account_trades",
  "data": [
    {
      "I": null,
      "a": "7.8",
      "f": "0.00501618",
      "h": 9020975,
      "i": 484871,
      "n": "-0.00501618",
      "o": "3.215567",
      "p": "3.2155",
      "s": "SUI",
      "t": 1749053764375,
      "tc": "normal",
      "te": "fulfill_maker",
      "ts": "open_long",
      "u": "42trU9A5..."
    }
  ]
}
```

**Response Fields:**
- `I`: Client order ID
- `a`: Trade amount
- `f`: Trade fee
- `h`: History ID
- `i`: Order ID
- `n`: PnL
- `o`: Entry price
- `p`: Price
- `s`: Symbol
- `t`: Timestamp (milliseconds)
- `tc`: Trade classification (normal, market_liquidation, backstop_liquidation, settlement)
- `te`: Trade execution type (fulfill_maker, fulfill_taker)
- `ts`: Trade side
- `u`: Account address

---

### WebSocket Trading Operations

**Note:** The documentation indicates WebSocket trading operations exist (create market order, create limit order, cancel order, cancel all orders) but specific endpoint documentation was not accessible. Use the Python SDK for implementation guidance:
- https://github.com/pacifica-fi/python-sdk

Example files:
- `ws/create_order.py` - WebSocket order creation
- REST API operations can serve as reference for message structure

---

## Rate Limits

### REST API Rate Limits

- Every IP address starts with **100 credits**
- Each HTTP method decrements credits by **1**
- If credits drop below 0, returns **HTTP 429 error**
- Credits reset to **100 every 60 seconds**

### WebSocket API Rate Limits

- Maximum **100 concurrent WebSocket connections per IP address**
- Exceeding 100 connections triggers **HTTP 429 error**
- Each connection limited to **20 subscriptions per channel**

### API Config Keys

For enhanced rate limiting:
- Each account can have up to **5 API Config Keys**
- Generated via REST API
- Used to enhance websocket rate-limiting

**Generation Endpoints:**
- `POST /api/v1/account/api_keys/create`
- `POST /api/v1/account/api_keys/revoke`
- `POST /api/v1/account/api_keys`

**Key Format:**
- Prefix: 8 character prefix
- Structure: `{8_char_prefix}_{base58_encoded_uuid}`

**Usage Methods:**
1. **WebSockets:** Add header `"PF-API-KEY": "your_rate_limit_key"`
2. **REST APIs:** Include header with `"Content-Type": "application/json"`

**Request Body Requirements:**
- `account`: User's wallet address
- `signature`: Cryptographic signature
- `timestamp`: Current timestamp in milliseconds
- `expiry_window` (optional): Signature expiration

For specific rate limit details, contact Pacifica's Discord API channel.

---

## Additional Resources

- **Python SDK:** https://github.com/pacifica-fi/python-sdk
- **Frontend (Generate API Keys):** https://app.pacifica.fi/apikey
- **Support:** Discord API channel
- **Official Website:** https://www.pacifica.fi
- **Documentation:** https://docs.pacifica.fi

---

## Notes

1. **Agent Wallets** are strongly recommended for programmatic trading to protect main wallet private keys
2. Use the **Python SDK** for easier implementation of signing and trading
3. All POST requests require **Ed25519 signature** authentication
4. **Deterministic JSON formatting** is used to generate signatures
5. GET requests and WebSocket subscriptions **do not require signatures**
6. WebSocket connections have a **60-second idle timeout** - use ping/pong to keep alive
7. Maximum WebSocket connection lifetime is **24 hours**
8. Pacifica is built on **Solana blockchain** for perpetual futures trading

---

*This documentation is based on the official Pacifica API documentation available at docs.pacifica.fi as of 2025-10-02. For the most up-to-date information and additional details, please refer to the official documentation.*
