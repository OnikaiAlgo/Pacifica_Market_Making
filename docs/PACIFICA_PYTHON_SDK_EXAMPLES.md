# Pacifica Python SDK - Complete Examples & Documentation

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Common Utilities](#common-utilities)
   - [Constants](#constants)
   - [Utility Functions](#utility-functions)
4. [REST API Examples](#rest-api-examples)
   - [Create Market Order](#create-market-order)
   - [Create Limit Order](#create-limit-order)
   - [Cancel Order](#cancel-order)
   - [Cancel All Orders](#cancel-all-orders)
   - [Batch Orders](#batch-orders)
   - [Create Position TP/SL](#create-position-tpsl)
   - [Create Subaccount](#create-subaccount)
   - [Create Subaccount (Hardware Wallet)](#create-subaccount-hardware-wallet)
   - [Transfer Subaccount Funds](#transfer-subaccount-funds)
   - [Transfer Subaccount Funds (Hardware Wallet)](#transfer-subaccount-funds-hardware-wallet)
   - [API Agent Keys](#api-agent-keys)
   - [API Config Keys](#api-config-keys)
   - [Deposit](#deposit)
5. [WebSocket Examples](#websocket-examples)
   - [Create Market Order (WS)](#create-market-order-ws)
   - [Create Market Order with Agent Wallet (WS)](#create-market-order-agent-wallet-ws)
   - [Create Limit Order (WS)](#create-limit-order-ws)
   - [Cancel Order (WS)](#cancel-order-ws)
   - [Cancel All Orders (WS)](#cancel-all-orders-ws)
   - [Subscribe to Prices (WS)](#subscribe-to-prices-ws)
6. [Best Practices](#best-practices)
7. [Common Pitfalls](#common-pitfalls)

---

## Overview

The Pacifica Python SDK provides a comprehensive interface for interacting with the Pacifica decentralized exchange (DEX) on Solana. It supports:

- **Market and limit orders** on perpetual futures
- **Position management** with take profit/stop loss
- **Subaccount management** for isolated risk
- **Agent wallets** for delegated trading
- **Hardware wallet support** (Ledger)
- **WebSocket real-time connections**
- **Batch operations** for efficient execution

The SDK uses Solana keypairs for authentication and message signing, ensuring secure and verifiable transactions.

---

## Installation

### Requirements

```bash
pip install solders requests websockets base58 borsh-construct solana spl-token
```

### Dependencies

- **solders**: Solana Python SDK for keypair management
- **requests**: HTTP client for REST API calls
- **websockets**: WebSocket client for real-time connections
- **base58**: Base58 encoding/decoding
- **borsh-construct**: Binary serialization for Solana programs
- **solana**: Solana RPC client
- **spl-token**: SPL token utilities

### Project Structure

```
pacifica_sdk/
├── common/
│   ├── constants.py    # API URLs and network configuration
│   └── utils.py        # Message signing utilities
├── rest/               # REST API examples
│   ├── create_market_order.py
│   ├── create_limit_order.py
│   └── ...
└── ws/                 # WebSocket examples
    ├── create_market_order.py
    ├── subscribe_prices.py
    └── ...
```

---

## Common Utilities

### Constants

**File: `common/constants.py`**

```python
# Mainnet
REST_URL = "https://api.pacifica.fi/api/v1"
WS_URL = "wss://ws.pacifica.fi/ws"

# Testnet
# REST_URL = "https://test-api.pacifica.fi/api/v1"
# WS_URL = "wss://test-ws.pacifica.fi/ws"
```

**Purpose**: Defines the API endpoints for Pacifica's mainnet and testnet.

**Key Points**:
- Uncomment testnet URLs for testing
- Always use HTTPS/WSS for security
- Mainnet is the default production environment

---

### Utility Functions

**File: `common/utils.py`**

```python
import json
import base58
import subprocess


def sign_message(header, payload, keypair):
    message = prepare_message(header, payload)
    message_bytes = message.encode("utf-8")
    signature = keypair.sign_message(message_bytes)
    return (message, base58.b58encode(bytes(signature)).decode("ascii"))


def sign_with_hardware_wallet(header, payload, hardware_wallet_path):
    message = prepare_message(header, payload)

    # Construct the solana CLI command
    cmd = [
        "solana",
        "sign-offchain-message",
        "-k",
        hardware_wallet_path,
        message,
    ]

    try:
        # Execute the command and get the signature
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            raise Exception(f"Ledger signing failed: {result.stderr}")

        # The output contains both the approval message and the signature
        # We need to extract just the signature (the last line)
        output_lines = result.stdout.strip().split("\n")
        signature = output_lines[-1]  # already in base58 ASCII format

        return (message, signature)

    except Exception as e:
        print(f"Error signing with Ledger: {e}")
        raise


def prepare_message(header, payload):
    if (
        "type" not in header
        or "timestamp" not in header
        or "expiry_window" not in header
    ):
        raise ValueError("Header must have type, timestamp, and expiry_window")

    data = {
        **header,
        "data": payload,
    }

    message = sort_json_keys(data)

    # Specifying the separaters is important because the JSON message is expected to be compact.
    message = json.dumps(message, separators=(",", ":"))

    return message


def sort_json_keys(value):
    if isinstance(value, dict):
        sorted_dict = {}
        for key in sorted(value.keys()):
            sorted_dict[key] = sort_json_keys(value[key])
        return sorted_dict
    elif isinstance(value, list):
        return [sort_json_keys(item) for item in value]
    else:
        return value
```

**Key Functions**:

1. **`sign_message(header, payload, keypair)`**
   - Signs a message using a Solana keypair
   - Returns tuple: (message, base58_signature)
   - Used for software wallet signing

2. **`sign_with_hardware_wallet(header, payload, hardware_wallet_path)`**
   - Signs using Ledger hardware wallet via Solana CLI
   - Requires `solana` CLI tool installed
   - Returns tuple: (message, base58_signature)

3. **`prepare_message(header, payload)`**
   - Constructs the canonical JSON message for signing
   - Sorts keys alphabetically (critical for signature verification)
   - Uses compact JSON format (no spaces)

4. **`sort_json_keys(value)`**
   - Recursively sorts dictionary keys
   - Ensures deterministic message format
   - Required for signature verification

**Important Notes**:
- Message format MUST be deterministic (sorted keys, compact JSON)
- Hardware wallet requires longer `expiry_window` (e.g., 200,000ms) for user approval time
- All signatures are base58-encoded

---

## REST API Examples

### Create Market Order

**File: `rest/create_market_order.py`**

```python
import time
import uuid

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message


API_URL = f"{REST_URL}/orders/create_market"
PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


def main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_market_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "reduce_only": False,
        "amount": "0.1",
        "side": "bid",
        "slippage_percent": "0.5",
        "client_order_id": str(uuid.uuid4()),
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Address: {public_key}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Creates a market order that executes immediately at the best available price.

**Key Parameters**:
- `symbol` (str): Trading pair symbol (e.g., "BTC", "ETH", "SOL")
- `reduce_only` (bool): If True, only reduces existing position (won't open new position)
- `amount` (str): Order size in base asset (e.g., "0.1" BTC)
- `side` (str): "bid" for long/buy, "ask" for short/sell
- `slippage_percent` (str): Maximum acceptable slippage (e.g., "0.5" = 0.5%)
- `client_order_id` (str): Unique client-side order ID (UUID recommended)
- `timestamp` (int): Unix timestamp in milliseconds
- `expiry_window` (int): Signature validity period in milliseconds (5,000 = 5 seconds)

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "order_id": 123456,
    "client_order_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "filled",
    "filled_amount": "0.1",
    "average_price": "50000.5"
  }
}
```

---

### Create Limit Order

**File: `rest/create_limit_order.py`**

```python
import time
import uuid

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message


API_URL = f"{REST_URL}/orders/create"
PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


def main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "price": str(100_000),
        "reduce_only": False,
        "amount": "0.1",
        "side": "bid",
        "tif": "GTC",
        "client_order_id": str(uuid.uuid4()),
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Address: {public_key}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Creates a limit order that only executes at a specified price or better.

**Key Parameters**:
- `symbol` (str): Trading pair symbol
- `price` (str): Limit price as string (e.g., "100000")
- `reduce_only` (bool): Only reduce existing positions
- `amount` (str): Order size in base asset
- `side` (str): "bid" (buy) or "ask" (sell)
- `tif` (str): Time in force - "GTC" (Good Till Cancel), "IOC" (Immediate or Cancel), "FOK" (Fill or Kill)
- `client_order_id` (str): Unique client order ID

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "order_id": 123457,
    "client_order_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "open",
    "price": "100000",
    "amount": "0.1",
    "filled_amount": "0"
  }
}
```

---

### Cancel Order

**File: `rest/cancel_order.py`**

```python
import time

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message


API_URL = f"{REST_URL}/orders/cancel"
PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


def main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "cancel_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "order_id": 42069,  # or "client_order_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Address: {public_key}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Cancels an existing open order.

**Key Parameters**:
- `symbol` (str): Trading pair symbol
- `order_id` (int): Exchange-assigned order ID, OR
- `client_order_id` (str): Client-assigned order ID (use one or the other, not both)

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "order_id": 42069,
    "status": "cancelled"
  }
}
```

---

### Cancel All Orders

**File: `rest/cancel_all_orders.py`**

```python
import time

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message

API_URL = f"{REST_URL}/orders/cancel_all"
PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


def main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "cancel_all_orders",
    }

    # Construct the signature payload
    signature_payload = {
        "all_symbols": True,
        "exclude_reduce_only": False,
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Address: {public_key}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Cancels all open orders for the account, with optional filters.

**Key Parameters**:
- `all_symbols` (bool): If True, cancels orders across all symbols; if False, specify `symbol` parameter
- `exclude_reduce_only` (bool): If True, keeps reduce-only orders active (useful for protecting positions)

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "cancelled_count": 5,
    "order_ids": [123, 456, 789, 1011, 1213]
  }
}
```

---

### Batch Orders

**File: `rest/batch_orders.py`**

```python
import time
import uuid

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message


API_URL = f"{REST_URL}/orders/batch"
PRIVATE_KEY = ""


def main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    timestamp = int(time.time() * 1_000)
    request_list = []

    # BATCH ORDER 1: CREATE ORDER

    # Scaffold the signature header
    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "price": str(100_000),
        "reduce_only": False,
        "amount": "0.1",
        "side": "bid",
        "tif": "GTC",
        "client_order_id": str(uuid.uuid4()),
    }

    # Use the helper function to sign the message
    _, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }
    request = {
        **request_header,
        **signature_payload,
    }
    request_list.append(
        {
            "type": "Create",
            "data": request,
        }
    )

    # BATCH ORDER 2: CANCEL ORDER

    # Scaffold the signature header
    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "cancel_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "order_id": 42069,  # or "client_order_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }

    # Use the helper function to sign the message
    _, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }
    request = {
        **request_header,
        **signature_payload,
    }
    request_list.append(
        {
            "type": "Cancel",
            "data": request,
        }
    )

    # Send the request
    headers = {"Content-Type": "application/json"}
    request_payload = {"actions": request_list}
    response = requests.post(API_URL, json=request_payload, headers=headers)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Requests: {requests}")


if __name__ == "__main__":
    main()
```

**What it does**: Executes multiple order operations (create, cancel, etc.) in a single atomic batch request.

**Key Parameters**:
- `actions` (list): Array of action objects
- Each action has:
  - `type` (str): "Create", "Cancel", "CancelAll", "CreateMarket"
  - `data` (dict): The signed request payload for that action

**Important Notes**:
- All actions in the batch use the **same timestamp**
- Each action requires its **own signature**
- Batch is atomic: all succeed or all fail
- More efficient than individual requests (lower latency, lower fees)

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "type": "Create",
        "success": true,
        "order_id": 123458
      },
      {
        "type": "Cancel",
        "success": true,
        "order_id": 42069
      }
    ]
  }
}
```

---

### Create Position TP/SL

**File: `rest/create_position_tpsl.py`**

```python
import time
import uuid

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message


# Assume a BTC long position has already been opened
API_URL = f"{REST_URL}/positions/tpsl"
PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


def main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "set_position_tpsl",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "side": "ask",
        "take_profit": {
            "stop_price": "120000",
            "limit_price": "120300",
            "amount": "0.1",
            "client_order_id": str(uuid.uuid4()),
        },
        "stop_loss": {
            "stop_price": "99800",
            # omitting limit_price to place a market order at trigger
            # omitting amount to use the full position size
            # client_order_id is optional
        },
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Address: {public_key}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Sets take-profit and stop-loss orders for an existing position.

**Key Parameters**:
- `symbol` (str): Trading pair symbol
- `side` (str): "ask" for long position exit, "bid" for short position exit
- `take_profit` (dict, optional):
  - `stop_price` (str): Trigger price for TP
  - `limit_price` (str, optional): Limit price (omit for market order)
  - `amount` (str, optional): Amount to close (omit for full position)
  - `client_order_id` (str, optional): Client order ID
- `stop_loss` (dict, optional):
  - Same fields as take_profit

**Important Notes**:
- Can set TP only, SL only, or both
- Omitting `limit_price` creates a market order at trigger
- Omitting `amount` uses full position size
- Side must be opposite of position (ask to close long, bid to close short)

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "take_profit_order_id": 123459,
    "stop_loss_order_id": 123460
  }
}
```

---

### Create Subaccount

**File: `rest/create_subaccount.py`**

```python
"""
## Authentication Flow

The authentication flow uses a cross-signature scheme to ensure that both the main account and the subaccount consent to the relationship. This is necessary because:

1. The main account must authorize the creation of a subaccount under its control
2. The subaccount must consent to being controlled by the main account
3. The API server must verify both signatures to prevent unauthorized subaccount creation

```
┌─────────────┐                ┌────────────┐               ┌────────────┐
│ Main Account│                │ Subaccount │               │ API Server │
└──────┬──────┘                └─────┬──────┘               └─────┬──────┘
       │                             │                            │
       │                             │                            │
       │ Step 1: Sign main_pubkey    │                            │
       │◄────────────────────────────┤                            │
       │                             │                            │
       │                             │                            │
       │ Step 2: Sign sub_signature  │                            │
       ├────────────────────────────►│                            │
       │                             │                            │
       │                             │                            │
       │ Step 3: Send both signature │                            │
       └─────────────────────────────┼───────────────────────────►│
                                     │                            │
                                     │                            │
                                     │                     Step 4: Verify
                                     │                      signatures
                                     │                            │
                                     │                            │
                                     │                     Step 5: Create
                                     │                      relationship
                                     │                            │
```

## Authentication Steps

1. **Subaccount Signs Main Account's Public Key**:

   - The subaccount signs the main account's public key using its private key
   - This creates the `sub_signature` which proves the subaccount consents to the relationship

2. **Main Account Signs the Subaccount's Signature**:

   - The main account signs the `sub_signature` using its private key
   - This creates the `main_signature` which proves the main account consents to the relationship

3. **API Server Verification**:
   - The API server verifies that `sub_signature` was created by the subaccount's private key by signing the main account's public key
   - The API server verifies that `main_signature` was created by the main account's private key by signing the `sub_signature`
   - If both verifications succeed, the subaccount relationship is established
"""

import time

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message

API_URL = f"{REST_URL}/account/subaccount/create"
MAIN_PRIVATE_KEY = ""
SUB_PRIVATE_KEY = ""


def main():

    # Generate main and sub accounts from private keys
    main_keypair = Keypair.from_base58_string(MAIN_PRIVATE_KEY)
    sub_keypair = Keypair.from_base58_string(SUB_PRIVATE_KEY)

    # Generate a timestamp and expiry window
    # Both signatures must have the same timestamp and expiry window.
    timestamp = int(time.time() * 1_000)
    expiry_window = 5_000

    # Get public keys
    main_public_key = str(main_keypair.pubkey())
    sub_public_key = str(sub_keypair.pubkey())

    # Step 1: Subaccount signs the main account's public key
    subaccount_signature_header = {
        "timestamp": timestamp,
        "expiry_window": expiry_window,
        "type": "subaccount_initiate",
    }

    payload = {"account": main_public_key}

    subaccount_message, subaccount_signature = sign_message(
        subaccount_signature_header, payload, sub_keypair
    )

    # Step 2: Main account signs the sub_signature
    main_account_signature_header = {
        "timestamp": timestamp,
        "expiry_window": expiry_window,
        "type": "subaccount_confirm",
    }

    payload = {"signature": subaccount_signature}

    main_account_message, main_signature = sign_message(
        main_account_signature_header, payload, main_keypair
    )

    # Step 3: Create and send the request
    request = {
        "main_account": main_public_key,
        "subaccount": sub_public_key,
        "main_signature": main_signature,
        "sub_signature": subaccount_signature,
        "timestamp": timestamp,
        "expiry_window": expiry_window,
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Main Account: {main_public_key}")
    print(f"Main Message: {main_account_message}")
    print(f"Main Signature: {main_signature}")
    print(f"Sub Account: {sub_public_key}")
    print(f"Sub Message: {subaccount_message}")
    print(f"Sub Signature: {subaccount_signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Creates a subaccount relationship between a main account and a subaccount for isolated risk management.

**Authentication Flow**:
1. **Subaccount** signs main account's public key → `sub_signature`
2. **Main account** signs the `sub_signature` → `main_signature`
3. Both signatures sent to API for verification

**Key Parameters**:
- `main_account` (str): Main account public key
- `subaccount` (str): Subaccount public key
- `main_signature` (str): Main account's signature
- `sub_signature` (str): Subaccount's signature
- `timestamp` (int): Must be same for both signatures
- `expiry_window` (int): Must be same for both signatures

**Important Notes**:
- **Cross-signature verification** prevents unauthorized subaccount creation
- Both accounts must consent to the relationship
- Timestamp and expiry_window must match for both signatures
- Subaccount can only have one main account

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "main_account": "9xQe....",
    "subaccount": "3kPz....",
    "relationship": "active"
  }
}
```

---

### Create Subaccount (Hardware Wallet)

**File: `rest/create_subaccount_hardware.py`**

```python
import time
import json

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message, sign_with_hardware_wallet

API_URL = f"{REST_URL}/account/subaccount/create"
MAIN_HARDWARE_PUB_KEY = ""
MAIN_HARDWARE_PATH = ""  # e.g. "usb://ledger?key=1"
SUB_PRIVATE_KEY = ""


def main():

    # Generate subaccount from private key
    sub_keypair = Keypair.from_base58_string(SUB_PRIVATE_KEY)

    # Generate a timestamp and expiry window
    # Both signatures must have the same timestamp and expiry window.
    timestamp = int(time.time() * 1_000)
    expiry_window = 200_000

    # Get public keys
    sub_public_key = str(sub_keypair.pubkey())

    # Step 1: Subaccount signs the main account's public key
    subaccount_signature_header = {
        "timestamp": timestamp,
        "expiry_window": expiry_window,
        "type": "subaccount_initiate",
    }

    payload = {"account": MAIN_HARDWARE_PUB_KEY}

    subaccount_message, subaccount_signature = sign_message(
        subaccount_signature_header, payload, sub_keypair
    )

    # Step 2: Main account signs the sub_signature
    main_account_signature_header = {
        "timestamp": timestamp,
        "expiry_window": expiry_window,
        "type": "subaccount_confirm",
    }

    payload = {"signature": subaccount_signature}

    print("Signing with hardware wallet...")
    main_account_message, main_signature = sign_with_hardware_wallet(
        main_account_signature_header, payload, MAIN_HARDWARE_PATH
    )

    # Step 3: Create and send the request
    request = {
        "main_account": MAIN_HARDWARE_PUB_KEY,
        "subaccount": sub_public_key,
        "main_signature": {
            "type": "hardware",
            "value": main_signature,
        },
        "sub_signature": subaccount_signature,
        "timestamp": timestamp,
        "expiry_window": expiry_window,
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Main Account: {MAIN_HARDWARE_PUB_KEY}")
    print(f"Main Message: {main_account_message}")
    print(f"Main Signature: {main_signature}")
    print(f"Sub Account: {sub_public_key}")
    print(f"Sub Message: {subaccount_message}")
    print(f"Sub Signature: {subaccount_signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Same as create_subaccount but uses a Ledger hardware wallet for the main account.

**Key Differences from Software Wallet**:
- `MAIN_HARDWARE_PATH`: Ledger device path (e.g., `"usb://ledger?key=1"`)
- `expiry_window`: Increased to 200,000ms (3+ minutes) for hardware signing time
- `main_signature`: Wrapped in object with `"type": "hardware"` and `"value": signature`

**Hardware Wallet Requirements**:
- Solana CLI tool installed
- Ledger device connected and unlocked
- Solana app opened on Ledger
- User must physically approve signature on device

**Expected Response**: Same as regular subaccount creation

---

### Transfer Subaccount Funds

**File: `rest/transfer_subaccount_fund.py`**

```python
import time

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message


API_URL = f"{REST_URL}/account/subaccount/transfer"
FROM_PRIVATE_KEY = ""  # must be a main account or a subaccount
TO_PUBLIC_KEY = ""  # must be the above's child subaccount or parent main account


def main():
    # Generate account based on private key
    from_keypair = Keypair.from_base58_string(FROM_PRIVATE_KEY)
    from_public_key = str(from_keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "transfer_funds",
    }

    # Construct the signature payload
    signature_payload = {
        "to_account": TO_PUBLIC_KEY,
        "amount": "420.69",
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, from_keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": from_public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"From Account: {from_public_key}")
    print(f"To Account: {TO_PUBLIC_KEY}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Transfers funds between a main account and its subaccount (bidirectional).

**Key Parameters**:
- `to_account` (str): Recipient public key (must be related account)
- `amount` (str): Amount to transfer in USDC

**Transfer Rules**:
- Main → Subaccount: Allowed
- Subaccount → Main: Allowed
- Subaccount → Subaccount: Only if same main account
- Unrelated accounts: Not allowed

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "from_account": "9xQe....",
    "to_account": "3kPz....",
    "amount": "420.69",
    "transaction_id": "abc123..."
  }
}
```

---

### Transfer Subaccount Funds (Hardware Wallet)

**File: `rest/transfer_subaccount_fund_hardware.py`**

```python
import time
import json

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_with_hardware_wallet


API_URL = f"{REST_URL}/account/subaccount/transfer"
HARDWARE_PATH = ""  # e.g. "usb://ledger?key=1"
FROM_HARDWARE_PUB_KEY = ""  # must be a main account in hardware wallet
TO_PUBLIC_KEY = ""  # must be the above's child subaccount


def main():
    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 200_000,
        "type": "transfer_funds",
    }

    # Construct the signature payload
    signature_payload = {
        "to_account": TO_PUBLIC_KEY,
        "amount": "420.69",
    }

    print("Signing with hardware wallet...")
    message, signature = sign_with_hardware_wallet(
        signature_header, signature_payload, HARDWARE_PATH
    )

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": FROM_HARDWARE_PUB_KEY,
        "signature": {
            "type": "hardware",
            "value": signature,
        },
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"From Account: {FROM_HARDWARE_PUB_KEY}")
    print(f"To Account: {TO_PUBLIC_KEY}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    main()
```

**What it does**: Same as transfer_subaccount_fund but uses a Ledger hardware wallet.

**Key Differences**:
- Uses `sign_with_hardware_wallet()` instead of `sign_message()`
- Longer `expiry_window` (200,000ms) for hardware signing
- Signature wrapped in `{"type": "hardware", "value": signature}`

---

### API Agent Keys

**File: `rest/api_agent_keys.py`**

```python
"""
This example shows how to bind an api agent key (also called agent wallet)
to an account and use the api agent key to sign on behalf of the account
to create a market order.
"""

import time
import uuid

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message


BIND_AGENT_WALLET_API_URL = f"{REST_URL}/agent/bind"
MARKET_ORDER_API_URL = f"{REST_URL}/orders/create_market"
PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


def main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Generate a new agent wallet
    agent_wallet_private_key = Keypair()
    agent_wallet_public_key = str(agent_wallet_private_key.pubkey())

    # ---------------------------------------------------------------
    # Bind agent wallet
    # ---------------------------------------------------------------

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "bind_agent_wallet",
    }

    # Construct the signature payload
    signature_payload = {
        "agent_wallet": agent_wallet_public_key,
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(BIND_AGENT_WALLET_API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Address: {public_key}")
    print(f"Agent Wallet: {agent_wallet_public_key}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")
    print("\n")

    # ---------------------------------------------------------------
    # Create market order
    # ---------------------------------------------------------------

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_market_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "reduce_only": False,
        "amount": "0.1",
        "side": "bid",
        "slippage_percent": "0.5",
        "client_order_id": str(uuid.uuid4()),
    }

    # Use the helper function to sign the message, with the agent wallet's private key
    message, signature = sign_message(
        signature_header, signature_payload, agent_wallet_private_key
    )

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "agent_wallet": agent_wallet_public_key,  # use the agent wallet's public key
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = requests.post(MARKET_ORDER_API_URL, json=request, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Address: {public_key}")
    print(f"Message: {message}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    main()
```

**What it does**:
1. Creates and binds an agent wallet to the main account
2. Uses the agent wallet to trade on behalf of the main account

**Agent Wallet Benefits**:
- Delegate trading permissions without exposing main private key
- Can be revoked at any time
- Useful for trading bots and automated strategies
- Main account retains full control

**Key Steps**:
1. **Bind Agent Wallet**:
   - Main account signs binding request with agent wallet public key
   - Creates delegation relationship

2. **Trade with Agent Wallet**:
   - Sign orders with agent wallet private key
   - Include both `account` (main) and `agent_wallet` (agent) in request
   - Agent wallet acts on behalf of main account

**Expected Response**:
```json
// Bind response
{
  "success": true,
  "data": {
    "account": "9xQe....",
    "agent_wallet": "7kLm....",
    "status": "bound"
  }
}

// Order response (same as regular market order)
```

---

### API Config Keys

**File: `rest/api_config_keys.py`**

```python
"""
This example shows how to create, revoke, and list api config keys for an account.
Please refer to https://docs.pacifica.fi/api-documentation/api/rate-limits/api-config-keys#using-a-pacifica-api-config-key
for the use of API Config Keys.
"""

import time
import json

import requests
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message


CREATE_ENDPOINT = f"{REST_URL}/account/api_keys/create"
REVOKE_ENDPOINT = f"{REST_URL}/account/api_keys/revoke"
LIST_ENDPOINT = f"{REST_URL}/account/api_keys"

PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


def create_api_config_key(keypair: Keypair):
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5000,
        "type": "create_api_key",
    }

    # Construct the signature payload
    signature_payload = {}

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    print(f"Message: {message}")
    print(f"Signature: {signature}")

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "agent_wallet": None,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}
    request = {
        **request_header,
        **signature_payload,
    }
    response = requests.post(CREATE_ENDPOINT, json=request, headers=headers)

    return response


def revoke_api_config_key(keypair: Keypair, api_key: str):
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5000,
        "type": "revoke_api_key",
    }

    # Construct the signature payload
    signature_payload = {
        "api_key": api_key,
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    print(f"Message: {message}")
    print(f"Signature: {signature}")

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "agent_wallet": None,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}
    request = {
        **request_header,
        **signature_payload,
    }
    response = requests.post(REVOKE_ENDPOINT, json=request, headers=headers)

    return response


def list_api_config_keys(keypair: Keypair):
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5000,
        "type": "list_api_keys",
    }

    # Construct the signature payload
    signature_payload = {}

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    print(f"Message: {message}")
    print(f"Signature: {signature}")

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "agent_wallet": None,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}
    request = {
        **request_header,
        **signature_payload,
    }
    response = requests.post(LIST_ENDPOINT, json=request, headers=headers)

    return response


def main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)

    print("Creating API Config Key")
    response = create_api_config_key(keypair)
    print(json.dumps(response.json(), indent=4))

    api_key = response.json()["data"]["api_key"]

    print("Listing API Config Keys")
    response = list_api_config_keys(keypair)
    print(json.dumps(response.json(), indent=4))

    print(f"Revoking API Config Key {api_key}")
    response = revoke_api_config_key(keypair, api_key)
    print(json.dumps(response.json(), indent=4))

    print("Listing API Keys")
    response = list_api_config_keys(keypair)
    print(json.dumps(response.json(), indent=4))


if __name__ == "__main__":
    main()
```

**What it does**: Manages API config keys for rate limit management and API access control.

**API Config Keys vs Agent Keys**:
- **API Config Keys**: For rate limits, API access control, not for trading
- **Agent Keys**: For delegated trading permissions

**Operations**:

1. **Create API Config Key**:
   - Generates a new API key for the account
   - Returns API key string to use in future requests

2. **List API Config Keys**:
   - Shows all active API keys for the account
   - Displays creation date and status

3. **Revoke API Config Key**:
   - Deactivates a specific API key
   - Revoked keys cannot be reactivated (must create new)

**Expected Responses**:
```json
// Create
{
  "success": true,
  "data": {
    "api_key": "pk_abc123xyz...",
    "created_at": "2024-01-15T10:30:00Z"
  }
}

// List
{
  "success": true,
  "data": {
    "api_keys": [
      {
        "api_key": "pk_abc123xyz...",
        "created_at": "2024-01-15T10:30:00Z",
        "status": "active"
      }
    ]
  }
}

// Revoke
{
  "success": true,
  "data": {
    "api_key": "pk_abc123xyz...",
    "status": "revoked"
  }
}
```

---

### Deposit

**File: `rest/deposit.py`**

```python
from borsh_construct import CStruct, U64
from solders.keypair import Keypair
from solders.instruction import Instruction, AccountMeta
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
import hashlib

PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"
DEPOSIT_AMOUNT = 4200.69  # minimum amount is 10

PROGRAM_ID = Pubkey.from_string("PCFA5iYgmqK6MqPhWNKg7Yv7auX7VZ4Cx7T1eJyrAMH")
CENTRAL_STATE = Pubkey.from_string("9Gdmhq4Gv1LnNMp7aiS1HSVd7pNnXNMsbuXALCQRmGjY")
PACIFICA_VAULT = Pubkey.from_string("72R843XwZxqWhsJceARQQTTbYtWy6Zw9et2YV4FpRHTa")
USDC_MINT = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
SYS_PROGRAM_ID = Pubkey.from_string("11111111111111111111111111111111")

RPC_URL = "https://api.mainnet-beta.solana.com"

deposit_layout = CStruct("amount" / U64)


def get_discriminator(name: str) -> bytes:
    return hashlib.sha256(f"global:{name}".encode()).digest()[:8]


def build_deposit_instruction_data(amount: float) -> bytes:
    borsh_args = deposit_layout.build(
        {"amount": int(round(amount * 1_000_000))}
    )  # 6 decimals
    return get_discriminator("deposit") + borsh_args


def get_associated_token_address(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return Pubkey.find_program_address(
        [
            bytes(owner),
            bytes(TOKEN_PROGRAM_ID),
            bytes(mint),
        ],
        ASSOCIATED_TOKEN_PROGRAM_ID,
    )[0]


def main():
    # Load user keypair
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    client = Client(RPC_URL)

    # Get associated token address
    user_usdc_ata = get_associated_token_address(keypair.pubkey(), USDC_MINT)
    event_authority, _ = Pubkey.find_program_address([b"__event_authority"], PROGRAM_ID)

    # Prepare accounts
    keys = [
        AccountMeta(
            pubkey=keypair.pubkey(), is_signer=True, is_writable=True
        ),  # depositor
        AccountMeta(
            pubkey=user_usdc_ata, is_signer=False, is_writable=True
        ),  # depositorUsdcAccount
        AccountMeta(pubkey=CENTRAL_STATE, is_signer=False, is_writable=True),
        AccountMeta(pubkey=PACIFICA_VAULT, is_signer=False, is_writable=True),
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(
            pubkey=ASSOCIATED_TOKEN_PROGRAM_ID, is_signer=False, is_writable=False
        ),
        AccountMeta(pubkey=USDC_MINT, is_signer=False, is_writable=False),
        AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=event_authority, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PROGRAM_ID, is_signer=False, is_writable=False),
    ]

    # Build instruction
    data = build_deposit_instruction_data(DEPOSIT_AMOUNT)
    ix = Instruction(program_id=PROGRAM_ID, accounts=keys, data=data)

    # Build and send transaction
    tx = Transaction().add(ix)
    resp = client.send_transaction(tx, keypair)
    print("Deposit transaction signature:", resp)


if __name__ == "__main__":
    main()
```

**What it does**: Deposits USDC from a Solana wallet to Pacifica exchange for trading.

**Key Parameters**:
- `DEPOSIT_AMOUNT` (float): Amount in USDC (minimum 10 USDC)
- `PRIVATE_KEY` (str): Solana wallet private key with USDC balance

**Program Accounts** (Hardcoded for Mainnet):
- `PROGRAM_ID`: Pacifica program address
- `CENTRAL_STATE`: Pacifica central state account
- `PACIFICA_VAULT`: USDC vault for deposits
- `USDC_MINT`: USDC token mint address

**Process**:
1. Derives user's USDC Associated Token Account (ATA)
2. Builds deposit instruction with Borsh serialization
3. Creates Solana transaction
4. Sends transaction to Solana RPC

**Important Notes**:
- Requires USDC in user's wallet
- Transaction fees paid in SOL
- Deposit is on-chain (Solana transaction)
- All other operations are off-chain (Pacifica API)

**Expected Response**:
```python
"Deposit transaction signature: 5xK7mP...abc123"
```

---

## WebSocket Examples

### Create Market Order (WS)

**File: `ws/create_market_order.py`**

```python
import asyncio
import json
import time
import uuid

import websockets
from solders.keypair import Keypair

from common.constants import WS_URL
from common.utils import sign_message

PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


async def exec_main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_market_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "reduce_only": False,
        "amount": "0.1",
        "side": "bid",
        "slippage_percent": "0.5",
        "client_order_id": str(uuid.uuid4()),
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Combine headers and payload for the final message
    message_to_send = {
        **request_header,
        **signature_payload,
    }

    # Connect to WebSocket
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        # Prepare the WebSocket message according to the backend format
        ws_message = {
            "id": str(uuid.uuid4()),
            "params": {"create_market_order": message_to_send},
        }

        # Send the message
        await websocket.send(json.dumps(ws_message))

        # Wait for response
        response = await websocket.recv()
        print(f"Response: {response}")

        # Print details for debugging
        print("\nDebug Info:")
        print(f"Address: {public_key}")
        print(f"Message: {message}")
        print(f"Signature: {signature}")
        print(f"WebSocket Message: {ws_message}")


async def main():
    await exec_main()


if __name__ == "__main__":
    asyncio.run(main())
```

**What it does**: Same as REST market order but via WebSocket for lower latency.

**WebSocket Message Format**:
```python
{
    "id": "unique-request-id",  # UUID for request tracking
    "params": {
        "create_market_order": {
            # ... signed order parameters
        }
    }
}
```

**Key Differences from REST**:
- **Lower latency**: WebSocket keeps connection open
- **Bidirectional**: Can receive real-time updates
- **Persistent connection**: Uses `ping_interval=30` for keepalive
- **Message ID**: Each request has unique `id` for response tracking

**Expected Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "result": {
    "success": true,
    "data": {
      "order_id": 123456,
      "status": "filled"
    }
  }
}
```

---

### Create Market Order with Agent Wallet (WS)

**File: `ws/create_market_order_agent_wallet.py`**

```python
import asyncio
import json
import time
import uuid

import websockets
from solders.keypair import Keypair

from common.constants import WS_URL
from common.utils import sign_message

PRIVATE_KEY = ""
API_PRIVATE_KEY = ""  # must be the above public key's registered agent wallet


async def exec_main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())
    api_keypair = Keypair.from_base58_string(API_PRIVATE_KEY)
    agent_key = str(api_keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_market_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "reduce_only": False,
        "amount": "0.1",
        "side": "bid",
        "slippage_percent": "0.5",
        "client_order_id": str(uuid.uuid4()),
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, api_keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "agent_wallet": agent_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Combine headers and payload for the final message
    message_to_send = {
        **request_header,
        **signature_payload,
    }

    # Connect to WebSocket
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        # Prepare the WebSocket message according to the backend format
        ws_message = {
            "id": str(uuid.uuid4()),
            "params": {"create_market_order": message_to_send},
        }

        # Send the message
        await websocket.send(json.dumps(ws_message))

        # Wait for response
        response = await websocket.recv()
        print(f"Response: {response}")

        # Print details for debugging
        print("\nDebug Info:")
        print(f"Address: {public_key}")
        print(f"Message: {message}")
        print(f"Signature: {signature}")
        print(f"WebSocket Message: {ws_message}")


async def main():
    await exec_main()


if __name__ == "__main__":
    asyncio.run(main())
```

**What it does**: Creates a market order via WebSocket using an agent wallet.

**Key Points**:
- Agent wallet must be pre-bound to the account (see API Agent Keys)
- Sign with **agent wallet private key**, not main account
- Include both `account` (main) and `agent_wallet` (agent) in request
- Same low-latency benefits as regular WebSocket

---

### Create Limit Order (WS)

**File: `ws/create_limit_order.py`**

```python
import asyncio
import json
import time
import uuid

import websockets
from solders.keypair import Keypair

from common.constants import WS_URL
from common.utils import sign_message

PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


async def exec_main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "price": str(100_000),
        "reduce_only": False,
        "amount": "0.1",
        "side": "bid",
        "tif": "GTC",
        "client_order_id": str(uuid.uuid4()),
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Combine headers and payload for the final message
    message_to_send = {
        **request_header,
        **signature_payload,
    }

    # Connect to WebSocket
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        # Prepare the WebSocket message according to the backend format
        ws_message = {
            "id": str(uuid.uuid4()),
            "params": {"create_order": message_to_send},
        }

        # Send the message
        await websocket.send(json.dumps(ws_message))

        # Wait for response
        response = await websocket.recv()
        print(f"Response: {response}")

        # Print details for debugging
        print("\nDebug Info:")
        print(f"Address: {public_key}")
        print(f"Message: {message}")
        print(f"Signature: {signature}")
        print(f"WebSocket Message: {ws_message}")


async def main():
    await exec_main()


if __name__ == "__main__":
    asyncio.run(main())
```

**What it does**: Same as REST limit order but via WebSocket.

**WebSocket Advantage**:
- Faster order placement in volatile markets
- Can subscribe to order updates on same connection
- Lower overhead than repeated HTTP requests

---

### Cancel Order (WS)

**File: `ws/cancel_order.py`**

```python
import asyncio
import json
import time
import uuid

import websockets
from solders.keypair import Keypair

from common.constants import WS_URL
from common.utils import sign_message

PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


async def exec_main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "cancel_order",
    }

    # Construct the signature payload
    signature_payload = {
        "symbol": "BTC",
        "order_id": 42069,  # or "client_order_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Combine headers and payload for the final message
    message_to_send = {
        **request_header,
        **signature_payload,
    }

    # Connect to WebSocket
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        # Prepare the WebSocket message according to the backend format
        ws_message = {
            "id": str(uuid.uuid4()),
            "params": {"cancel_order": message_to_send},
        }

        # Send the message
        await websocket.send(json.dumps(ws_message))

        # Wait for response
        response = await websocket.recv()
        print(f"Response: {response}")

        # Print details for debugging
        print("\nDebug Info:")
        print(f"Address: {public_key}")
        print(f"Message: {message}")
        print(f"Signature: {signature}")
        print(f"WebSocket Message: {ws_message}")


async def main():
    await exec_main()


if __name__ == "__main__":
    asyncio.run(main())
```

**What it does**: Same as REST cancel order but via WebSocket.

**Use Case**: Ultra-fast order cancellation for market making and HFT strategies.

---

### Cancel All Orders (WS)

**File: `ws/cancel_all_orders.py`**

```python
import asyncio
import json
import time
import uuid

import websockets
from solders.keypair import Keypair

from common.constants import WS_URL
from common.utils import sign_message

PRIVATE_KEY = ""  # e.g. "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"


async def exec_main():
    # Generate account based on private key
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "cancel_all_orders",
    }

    # Construct the signature payload
    signature_payload = {
        "all_symbols": True,
        "exclude_reduce_only": False,
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Combine headers and payload for the final message
    message_to_send = {
        **request_header,
        **signature_payload,
    }

    # Connect to WebSocket
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        # Prepare the WebSocket message according to the backend format
        ws_message = {
            "id": str(uuid.uuid4()),
            "params": {"cancel_all_orders": message_to_send},
        }

        # Send the message
        await websocket.send(json.dumps(ws_message))

        # Wait for response
        response = await websocket.recv()
        print(f"Response: {response}")

        # Print details for debugging
        print("\nDebug Info:")
        print(f"Address: {public_key}")
        print(f"Message: {message}")
        print(f"Signature: {signature}")
        print(f"WebSocket Message: {ws_message}")


async def main():
    await exec_main()


if __name__ == "__main__":
    asyncio.run(main())
```

**What it does**: Same as REST cancel all orders but via WebSocket.

**Emergency Use**: Fast emergency cancellation of all orders (e.g., risk management event).

---

### Subscribe to Prices (WS)

**File: `ws/subscribe_prices.py`**

```python
import asyncio
import json

import websockets

from common.constants import WS_URL


async def exec_main():
    # Connect to WebSocket
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        # Prepare the WebSocket message according to the backend format
        ws_message = {"method": "subscribe", "params": {"source": "prices"}}

        # Send the message
        await websocket.send(json.dumps(ws_message))

        # Wait for response
        async for message in websocket:
            data = json.loads(message)
            print(data)


async def main():
    await exec_main()


if __name__ == "__main__":
    asyncio.run(main())
```

**What it does**: Subscribes to real-time price updates for all trading pairs.

**Key Features**:
- **No signature required** (public data stream)
- **Real-time updates**: Prices pushed as they change
- **All symbols**: Receives updates for all trading pairs
- **Continuous stream**: Uses `async for` to process messages continuously

**Message Format**:
```python
{
    "method": "subscribe",
    "params": {
        "source": "prices"
    }
}
```

**Expected Response Stream**:
```json
{
  "type": "price_update",
  "data": {
    "symbol": "BTC",
    "price": "50123.45",
    "timestamp": 1705234567890
  }
}
{
  "type": "price_update",
  "data": {
    "symbol": "ETH",
    "price": "3456.78",
    "timestamp": 1705234568000
  }
}
// ... continuous stream
```

**Use Cases**:
- Real-time price monitoring
- Market making bot price feeds
- Trading signal generation
- Portfolio valuation updates

---

## Best Practices

### 1. Security

- **Never hardcode private keys** in production code
  ```python
  # Bad
  PRIVATE_KEY = "2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b"

  # Good
  import os
  PRIVATE_KEY = os.environ.get("PACIFICA_PRIVATE_KEY")
  ```

- **Use agent wallets** for trading bots to limit exposure
- **Revoke agent wallets** when no longer needed
- **Use subaccounts** for isolated risk management

### 2. Message Signing

- **Always sort JSON keys** before signing (handled by `utils.py`)
- **Use compact JSON** format (no spaces) for signatures
- **Match timestamp and expiry_window** across batch operations
- **Increase expiry_window** for hardware wallets (200,000ms+)

### 3. Order Management

- **Always use client_order_id** (UUID) for order tracking
  ```python
  import uuid
  "client_order_id": str(uuid.uuid4())
  ```

- **Set reduce_only=True** for position-closing orders to prevent accidental position flipping
- **Use batch orders** for atomic multi-step operations
- **Set TP/SL** immediately after opening positions

### 4. WebSocket Connections

- **Use ping_interval=30** to maintain connection
  ```python
  async with websockets.connect(WS_URL, ping_interval=30) as websocket:
  ```

- **Implement reconnection logic** for production:
  ```python
  async def connect_with_retry(max_retries=5):
      for i in range(max_retries):
          try:
              async with websockets.connect(WS_URL, ping_interval=30) as ws:
                  return ws
          except Exception as e:
              if i == max_retries - 1:
                  raise
              await asyncio.sleep(2 ** i)  # exponential backoff
  ```

- **Handle message errors gracefully**
- **Track request IDs** for WebSocket responses

### 5. Error Handling

```python
def safe_api_call(func):
    try:
        response = func()
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None
```

### 6. Rate Limiting

- **Use API config keys** for higher rate limits
- **Implement backoff** on rate limit errors (429)
- **Prefer batch operations** over individual requests
- **Use WebSocket** for high-frequency operations

### 7. Decimal Precision

- **Always use strings** for numeric values to preserve precision
  ```python
  # Bad
  "amount": 0.1  # May lose precision

  # Good
  "amount": "0.1"  # Exact precision
  ```

### 8. Testing

- **Test on testnet first**
  ```python
  # Switch to testnet in constants.py
  REST_URL = "https://test-api.pacifica.fi/api/v1"
  WS_URL = "wss://test-ws.pacifica.fi/ws"
  ```

- **Start with small amounts**
- **Verify signatures offline** before sending
- **Log all requests and responses** for debugging

---

## Common Pitfalls

### 1. Signature Verification Failures

**Problem**: Signature verification fails with "Invalid signature" error.

**Causes**:
- JSON keys not sorted alphabetically
- JSON not compact (contains spaces)
- Timestamp/expiry_window mismatch in batch operations
- Using wrong private key (main vs agent)

**Solution**:
```python
# Always use the utility functions
from common.utils import sign_message

# These handle correct JSON formatting automatically
message, signature = sign_message(header, payload, keypair)
```

### 2. Expiry Window Too Short

**Problem**: Hardware wallet signing fails or requests timeout.

**Cause**: Default 5,000ms expiry_window is too short for hardware approval.

**Solution**:
```python
# For hardware wallets, use longer expiry
signature_header = {
    "timestamp": timestamp,
    "expiry_window": 200_000,  # 200 seconds for Ledger approval
    "type": "...",
}
```

### 3. Reduce-Only Not Set

**Problem**: Accidentally increase position when trying to close.

**Cause**: `reduce_only=False` when closing positions.

**Solution**:
```python
# When closing positions, always set reduce_only=True
signature_payload = {
    "symbol": "BTC",
    "reduce_only": True,  # Ensures you can't flip position
    "amount": "0.1",
    "side": "ask",  # Opposite of position direction
    ...
}
```

### 4. Client Order ID Collisions

**Problem**: Duplicate client_order_id causes order rejection.

**Cause**: Reusing or hardcoding client_order_id.

**Solution**:
```python
import uuid

# Always generate unique ID for each order
"client_order_id": str(uuid.uuid4())
```

### 5. Decimal Precision Loss

**Problem**: Order amounts are incorrect or rejected.

**Cause**: Using float instead of string.

**Solution**:
```python
# Bad
"amount": 0.1  # Float may lose precision

# Good
"amount": "0.1"  # String preserves exact value
```

### 6. WebSocket Connection Drops

**Problem**: WebSocket disconnects unexpectedly.

**Causes**:
- No ping_interval set (server timeout)
- Network issues
- No reconnection logic

**Solution**:
```python
# Set ping interval
async with websockets.connect(WS_URL, ping_interval=30) as ws:
    # ... your code

# Implement reconnection
async def maintain_connection():
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=30) as ws:
                await handle_messages(ws)
        except websockets.ConnectionClosed:
            print("Connection lost, reconnecting...")
            await asyncio.sleep(5)
```

### 7. Wrong Side for Position Closure

**Problem**: Position increases instead of closing.

**Cause**: Using same side as opening order.

**Solution**:
```python
# If you opened a long (bid) position
# Close with ask (opposite side)
signature_payload = {
    "side": "ask",  # Opposite of "bid"
    "reduce_only": True,
    ...
}
```

### 8. Batch Operation Timestamp Mismatch

**Problem**: Batch operation fails with "Invalid timestamp" error.

**Cause**: Each action in batch has different timestamp.

**Solution**:
```python
# Generate timestamp ONCE for entire batch
timestamp = int(time.time() * 1_000)

# Use SAME timestamp for all actions
for action in batch_actions:
    signature_header = {
        "timestamp": timestamp,  # Same for all
        "expiry_window": 5_000,
        ...
    }
```

### 9. Subaccount Transfer Restrictions

**Problem**: Transfer fails with "Unauthorized transfer" error.

**Cause**: Trying to transfer between unrelated accounts.

**Solution**:
```python
# Transfers only allowed between:
# 1. Main → Subaccount (same relationship)
# 2. Subaccount → Main (same relationship)
# 3. Subaccount → Subaccount (same main account)

# Verify relationship before transfer
```

### 10. Agent Wallet Not Bound

**Problem**: Agent wallet signature fails.

**Cause**: Trying to use agent wallet before binding to main account.

**Solution**:
```python
# Step 1: Bind agent wallet FIRST
# (see API Agent Keys example)

# Step 2: Then use agent wallet for trading
# Include agent_wallet in request
request_header = {
    "account": main_public_key,
    "agent_wallet": agent_public_key,  # Must be bound
    "signature": signature,
    ...
}
```

---

## Quick Reference

### REST Endpoints
- Market Order: `POST /api/v1/orders/create_market`
- Limit Order: `POST /api/v1/orders/create`
- Cancel Order: `POST /api/v1/orders/cancel`
- Cancel All: `POST /api/v1/orders/cancel_all`
- Batch Orders: `POST /api/v1/orders/batch`
- Position TP/SL: `POST /api/v1/positions/tpsl`
- Create Subaccount: `POST /api/v1/account/subaccount/create`
- Transfer Funds: `POST /api/v1/account/subaccount/transfer`
- Bind Agent: `POST /api/v1/agent/bind`
- API Keys: `POST /api/v1/account/api_keys/*`

### WebSocket Methods
- Market Order: `{"params": {"create_market_order": {...}}}`
- Limit Order: `{"params": {"create_order": {...}}}`
- Cancel Order: `{"params": {"cancel_order": {...}}}`
- Cancel All: `{"params": {"cancel_all_orders": {...}}}`
- Subscribe Prices: `{"method": "subscribe", "params": {"source": "prices"}}`

### Signature Types
- `create_market_order`
- `create_order`
- `cancel_order`
- `cancel_all_orders`
- `set_position_tpsl`
- `subaccount_initiate`
- `subaccount_confirm`
- `transfer_funds`
- `bind_agent_wallet`
- `create_api_key`
- `revoke_api_key`
- `list_api_keys`

### Order Sides
- `bid`: Long/Buy
- `ask`: Short/Sell

### Time in Force (TIF)
- `GTC`: Good Till Cancel
- `IOC`: Immediate or Cancel
- `FOK`: Fill or Kill

---

**Documentation Version**: 1.0
**Last Updated**: 2024-01-15
**SDK Compatibility**: Pacifica Python SDK v1.x

For the latest API documentation, visit: https://docs.pacifica.fi
