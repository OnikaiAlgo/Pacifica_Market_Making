#!/usr/bin/env python3
"""
Test script to check order status via WebSocket
Based on Pacifica Python SDK examples
"""
import asyncio
import json
import time
import os
import base58
import websockets
from dotenv import load_dotenv
from solders.keypair import Keypair

# Load environment
load_dotenv()
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WS_URL = "wss://ws.pacifica.fi/ws"

def sort_json_keys(value):
    """Sort JSON keys recursively for signature consistency"""
    if isinstance(value, dict):
        sorted_dict = {}
        for key in sorted(value.keys()):
            sorted_dict[key] = sort_json_keys(value[key])
        return sorted_dict
    elif isinstance(value, list):
        return [sort_json_keys(item) for item in value]
    else:
        return value

def sign_message(header, payload, keypair):
    """Sign a message using Solana keypair"""
    if "type" not in header or "timestamp" not in header or "expiry_window" not in header:
        raise ValueError("Header must have type, timestamp, and expiry_window")

    data = {
        **header,
        "data": payload,
    }

    message = sort_json_keys(data)
    message = json.dumps(message, separators=(",", ":"))

    message_bytes = message.encode("utf-8")
    signature = keypair.sign_message(message_bytes)
    return (message, base58.b58encode(bytes(signature)).decode("ascii"))

async def get_order_status_ws(order_id: int):
    """Test getting order status via WebSocket"""
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    public_key = str(keypair.pubkey())

    print(f"Testing order status via WebSocket for order {order_id}")
    print(f"Account: {public_key}")

    # Try different approaches

    # Approach 1: Try subscription to order updates
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        print("\n=== Approach 1: Subscribe to order updates ===")

        # Try subscribing to user orders
        subscribe_msg = {
            "method": "subscribe",
            "params": {
                "source": "orders",
                "account": public_key
            }
        }

        print(f"Sending: {json.dumps(subscribe_msg, indent=2)}")
        await websocket.send(json.dumps(subscribe_msg))

        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Response: {response}")
        except asyncio.TimeoutError:
            print("Timeout - no response received")

    # Approach 2: Try authenticated query for order status
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        print("\n=== Approach 2: Query order status (authenticated) ===")

        timestamp = int(time.time() * 1_000)

        signature_header = {
            "timestamp": timestamp,
            "expiry_window": 5_000,
            "type": "order_status",
        }

        signature_payload = {
            "order_id": str(order_id)
        }

        try:
            message, signature = sign_message(signature_header, signature_payload, keypair)

            request_header = {
                "account": public_key,
                "signature": signature,
                "timestamp": signature_header["timestamp"],
                "expiry_window": signature_header["expiry_window"],
            }

            message_to_send = {
                **request_header,
                **signature_payload,
            }

            ws_message = {
                "id": f"test_{order_id}",
                "params": {"order_status": message_to_send},
            }

            print(f"Sending: {json.dumps(ws_message, indent=2)}")
            await websocket.send(json.dumps(ws_message))

            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Response: {response}")
        except asyncio.TimeoutError:
            print("Timeout - no response received")
        except Exception as e:
            print(f"Error: {e}")

    # Approach 3: Try subscription to positions
    async with websockets.connect(WS_URL, ping_interval=30) as websocket:
        print("\n=== Approach 3: Subscribe to positions ===")

        subscribe_msg = {
            "method": "subscribe",
            "params": {
                "source": "positions",
                "account": public_key
            }
        }

        print(f"Sending: {json.dumps(subscribe_msg, indent=2)}")
        await websocket.send(json.dumps(subscribe_msg))

        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Response: {response}")
        except asyncio.TimeoutError:
            print("Timeout - no response received")

if __name__ == "__main__":
    # Test with a recent order ID from logs
    order_id = 328074823  # Latest order from logs
    asyncio.run(get_order_status_ws(order_id))
