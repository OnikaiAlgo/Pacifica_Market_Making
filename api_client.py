import time
import aiohttp
import json
import base58
from solders.keypair import Keypair
from typing import Optional, Dict, Any, List


def sort_json_keys(value):
    """Recursively sort dictionary keys for consistent JSON serialization."""
    if isinstance(value, dict):
        sorted_dict = {}
        for key in sorted(value.keys()):
            sorted_dict[key] = sort_json_keys(value[key])
        return sorted_dict
    elif isinstance(value, list):
        return [sort_json_keys(item) for item in value]
    else:
        return value


class ApiClient:
    """
    An asynchronous client for interacting with the Pacifica Finance API,
    handling session management and Solana-based request signing.
    """

    def __init__(self, private_key: str, release_mode: bool = True):
        """
        Initialize the Pacifica API client.

        Args:
            private_key: Solana private key in base58 format
            release_mode: If True, suppress debug messages
        """
        if not private_key:
            raise ValueError("PRIVATE_KEY is missing.")

        try:
            self.keypair = Keypair.from_base58_string(private_key)
            self.public_key = str(self.keypair.pubkey())
        except Exception as e:
            raise ValueError(f"Invalid Solana private key: {e}")

        self.private_key = private_key
        self.release_mode = release_mode

        # Pacifica API endpoints
        self.base_url = "https://api.pacifica.fi/api/v1"
        self.ws_url = "wss://ws.pacifica.fi/ws"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _prepare_message(self, header: dict, payload: dict) -> str:
        """
        Prepare a message for signing following Pacifica's format.

        Args:
            header: Message header containing type, timestamp, expiry_window
            payload: Message payload with request data

        Returns:
            JSON string ready for signing
        """
        if "type" not in header or "timestamp" not in header or "expiry_window" not in header:
            raise ValueError("Header must have type, timestamp, and expiry_window")

        data = {
            **header,
            "data": payload,
        }

        message = sort_json_keys(data)
        # Use compact JSON format (no spaces)
        message = json.dumps(message, separators=(",", ":"))
        return message

    def _sign_message(self, header: dict, payload: dict) -> tuple:
        """
        Sign a message using Solana keypair.

        Args:
            header: Message header
            payload: Message payload

        Returns:
            Tuple of (message, signature)
        """
        message = self._prepare_message(header, payload)
        message_bytes = message.encode("utf-8")
        signature = self.keypair.sign_message(message_bytes)
        signature_b58 = base58.b58encode(bytes(signature)).decode("ascii")
        return message, signature_b58

    def _create_signed_request(self, request_type: str, payload: dict,
                               timestamp: Optional[int] = None,
                               expiry_window: int = 5000) -> dict:
        """
        Create a signed request for Pacifica API.

        Args:
            request_type: Type of request (e.g., 'create_order', 'cancel_order')
            payload: Request payload
            timestamp: Unix timestamp in milliseconds (auto-generated if None)
            expiry_window: Expiry window in milliseconds (default 5000)

        Returns:
            Complete signed request dictionary
        """
        if timestamp is None:
            timestamp = int(time.time() * 1_000)

        signature_header = {
            "timestamp": timestamp,
            "expiry_window": expiry_window,
            "type": request_type,
        }

        _, signature = self._sign_message(signature_header, payload)

        request_header = {
            "account": self.public_key,
            "signature": signature,
            "timestamp": signature_header["timestamp"],
            "expiry_window": signature_header["expiry_window"],
        }

        return {
            **request_header,
            **payload,
        }

    async def _make_request(self, method: str, endpoint: str,
                           data: Optional[dict] = None,
                           params: Optional[dict] = None,
                           signed: bool = False) -> dict:
        """
        Make an HTTP request to the Pacifica API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: URL query parameters
            signed: Whether this is a signed request

        Returns:
            JSON response from the API
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://pacifica.fi",
            "Referer": "https://pacifica.fi/",
            "Connection": "keep-alive",
            "DNT": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }

        try:
            if method.upper() == "GET":
                async with self.session.get(url, params=params, headers=headers) as response:
                    if not response.ok:
                        error_body = await response.text()
                        if not self.release_mode:
                            print(f"API Error on {method} {endpoint}: Status={response.status}, Body={error_body}")
                    response.raise_for_status()
                    return await response.json()

            elif method.upper() == "POST":
                async with self.session.post(url, json=data, headers=headers) as response:
                    if not response.ok:
                        error_body = await response.text()
                        if not self.release_mode:
                            print(f"API Error on {method} {endpoint}: Status={response.status}, Body={error_body}")
                    response.raise_for_status()
                    return await response.json()

            elif method.upper() == "DELETE":
                async with self.session.delete(url, json=data, headers=headers) as response:
                    if not response.ok:
                        error_body = await response.text()
                        if not self.release_mode:
                            print(f"API Error on {method} {endpoint}: Status={response.status}, Body={error_body}")
                    response.raise_for_status()
                    return await response.json()

            elif method.upper() == "PUT":
                async with self.session.put(url, json=data, headers=headers) as response:
                    if not response.ok:
                        error_body = await response.text()
                        if not self.release_mode:
                            print(f"API Error on {method} {endpoint}: Status={response.status}, Body={error_body}")
                    response.raise_for_status()
                    return await response.json()

            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except Exception as e:
            if not self.release_mode:
                print(f"Request failed: {e}")
            raise

    # ============================================================================
    # PUBLIC ENDPOINTS - Market Data
    # ============================================================================

    async def get_exchange_info(self) -> dict:
        """
        Get exchange information including all markets and their specifications.
        Public endpoint - no authentication required.

        Returns:
            Exchange information with market details
        """
        return await self._make_request("GET", "/markets")

    async def get_markets(self) -> dict:
        """
        Get information about all available markets.
        Public endpoint - no authentication required.

        Returns:
            List of all markets with their specifications
        """
        return await self._make_request("GET", "/info")

    async def get_prices(self, symbol: Optional[str] = None) -> dict:
        """
        Get current prices for markets.
        Public endpoint - no authentication required.

        Args:
            symbol: Optional symbol to get price for (e.g., "BTC")

        Returns:
            Current market prices
        """
        params = {"symbol": symbol} if symbol else None
        return await self._make_request("GET", "/prices", params=params)

    async def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        """
        Get orderbook for a specific market.
        Public endpoint - no authentication required.

        Args:
            symbol: Market symbol (e.g., "BTC")
            depth: Depth of orderbook (default 20)

        Returns:
            Orderbook with bids and asks
        """
        params = {"symbol": symbol, "depth": depth}
        return await self._make_request("GET", "/orderbook", params=params)

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> dict:
        """
        Get recent trades for a specific market.
        Public endpoint - no authentication required.

        Args:
            symbol: Market symbol (e.g., "BTC")
            limit: Number of trades to return (default 100)

        Returns:
            List of recent trades
        """
        params = {"symbol": symbol, "limit": limit}
        return await self._make_request("GET", "/trades", params=params)

    async def get_klines(self, symbol: str, interval: str,
                        start_time: Optional[int] = None,
                        end_time: Optional[int] = None,
                        limit: int = 500) -> dict:
        """
        Get candlestick/kline data for a market.
        Public endpoint - no authentication required.

        Args:
            symbol: Market symbol (e.g., "BTC")
            interval: Kline interval (e.g., "1m", "5m", "1h", "1d")
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Number of klines to return (default 500)

        Returns:
            Kline/candlestick data
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        return await self._make_request("GET", "/klines", params=params)

    async def get_funding_history(self, symbol: str,
                                  start_time: Optional[int] = None,
                                  end_time: Optional[int] = None,
                                  limit: int = 100) -> dict:
        """
        Get historical funding rates for a market.
        Public endpoint - no authentication required.

        Args:
            symbol: Market symbol (e.g., "BTC")
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Number of records to return (default 100)

        Returns:
            Historical funding rate data
        """
        params = {
            "symbol": symbol,
            "limit": limit
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        return await self._make_request("GET", "/funding_history", params=params)

    async def get_symbol_filters(self, symbol: str) -> dict:
        """
        Get trading filters and precision information for a symbol.

        Args:
            symbol: Market symbol (e.g., "BTC")

        Returns:
            Dictionary containing price_precision, tick_size, quantity_precision,
            step_size, and min_notional
        """
        markets = await self.get_markets()

        for market in markets.get('data', []):
            if market.get('symbol') == symbol:
                # Extract precision and step size information
                tick_size = float(market.get('tick_size', '0.01'))
                step_size = float(market.get('lot_size', '0.001'))
                min_notional = float(market.get('min_order_size', '10.0'))

                # Calculate precision from tick/step size
                tick_size_str = str(tick_size)
                price_precision = len(tick_size_str.split('.')[1].rstrip('0')) if '.' in tick_size_str else 0

                step_size_str = str(step_size)
                quantity_precision = len(step_size_str.split('.')[1].rstrip('0')) if '.' in step_size_str else 0

                return {
                    'price_precision': price_precision,
                    'tick_size': tick_size,
                    'quantity_precision': quantity_precision,
                    'step_size': step_size,
                    'min_notional': min_notional
                }

        raise ValueError(f"Could not find filters for symbol '{symbol}'.")

    # ============================================================================
    # PRIVATE ENDPOINTS - Account Management
    # ============================================================================

    async def get_account_info(self) -> dict:
        """
        Get account information including balances and settings.
        Requires authentication.

        Returns:
            Account information
        """
        params = {"account": self.public_key}
        return await self._make_request("GET", "/account", params=params, signed=False)

    async def get_account_settings(self) -> dict:
        """
        Get account settings including leverage and margin mode.
        Requires authentication.

        Returns:
            Account settings
        """
        params = {"account": self.public_key}
        return await self._make_request("GET", "/account/settings", params=params, signed=False)

    async def change_leverage(self, symbol: str, leverage: int) -> dict:
        """
        Change the leverage for a specific market.
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            leverage: Leverage value (e.g., 10 for 10x)

        Returns:
            Updated leverage information
        """
        payload = {
            "symbol": symbol,
            "leverage": str(leverage)
        }
        request = self._create_signed_request("update_leverage", payload)

        if not self.release_mode:
            print(f"Changing leverage for {symbol} to {leverage}x")

        return await self._make_request("POST", "/account/leverage", data=request, signed=True)

    async def update_margin_mode(self, symbol: str, margin_mode: str) -> dict:
        """
        Update margin mode for a specific market.
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            margin_mode: Margin mode ("cross" or "isolated")

        Returns:
            Updated margin mode information
        """
        payload = {
            "symbol": symbol,
            "margin_mode": margin_mode
        }
        request = self._create_signed_request("update_margin_mode", payload)
        return await self._make_request("POST", "/account/margin_mode", data=request, signed=True)

    # ============================================================================
    # PRIVATE ENDPOINTS - Position Management
    # ============================================================================

    async def get_position_risk(self, symbol: Optional[str] = None) -> dict:
        """
        Get position information and risk metrics.
        Requires authentication.

        Args:
            symbol: Optional market symbol to filter by (e.g., "BTC")

        Returns:
            Position risk information
        """
        params = {"account": self.public_key}
        if symbol:
            params["symbol"] = symbol

        return await self._make_request("GET", "/positions", params=params, signed=False)

    async def get_positions(self, symbol: Optional[str] = None) -> dict:
        """
        Get current positions.
        Requires authentication.

        Args:
            symbol: Optional market symbol to filter by (e.g., "BTC")

        Returns:
            Current positions
        """
        return await self.get_position_risk(symbol)

    async def set_position_tpsl(self, symbol: str, side: str,
                               take_profit: Optional[dict] = None,
                               stop_loss: Optional[dict] = None) -> dict:
        """
        Set take profit and/or stop loss for a position.
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            side: Order side ("bid" or "ask")
            take_profit: Take profit configuration (stop_price, limit_price, amount, client_order_id)
            stop_loss: Stop loss configuration (stop_price, limit_price, amount, client_order_id)

        Returns:
            TP/SL order information
        """
        payload = {
            "symbol": symbol,
            "side": side
        }

        if take_profit:
            payload["take_profit"] = take_profit
        if stop_loss:
            payload["stop_loss"] = stop_loss

        request = self._create_signed_request("set_position_tpsl", payload)
        return await self._make_request("POST", "/positions/tpsl", data=request, signed=True)

    # ============================================================================
    # PRIVATE ENDPOINTS - Order Management
    # ============================================================================

    async def place_order(self, symbol: str, price: str, quantity: str,
                         side: str, reduce_only: bool = False,
                         tif: str = "GTC", client_order_id: Optional[str] = None) -> dict:
        """
        Place a limit order.
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            price: Order price
            quantity: Order quantity/amount
            side: Order side ("bid" for buy, "ask" for sell)
            reduce_only: If True, order will only reduce position (default False)
            tif: Time in force ("GTC", "IOC", "FOK", "GTX") (default "GTC")
            client_order_id: Optional client-specified order ID

        Returns:
            Order creation response
        """
        payload = {
            "symbol": symbol,
            "price": str(price),
            "amount": str(quantity),
            "side": side,
            "reduce_only": reduce_only,
            "tif": tif
        }

        if client_order_id:
            payload["client_order_id"] = client_order_id

        request = self._create_signed_request("create_order", payload)

        if not self.release_mode:
            print(f"Placing {side} limit order: {quantity} {symbol} @ {price}")

        return await self._make_request("POST", "/orders/create", data=request, signed=True)

    async def place_market_order(self, symbol: str, quantity: str, side: str,
                                reduce_only: bool = False,
                                slippage_percent: str = "0.5",
                                client_order_id: Optional[str] = None) -> dict:
        """
        Place a market order.
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            quantity: Order quantity/amount
            side: Order side ("bid" for buy, "ask" for sell)
            reduce_only: If True, order will only reduce position (default False)
            slippage_percent: Maximum slippage percentage (default "0.5")
            client_order_id: Optional client-specified order ID

        Returns:
            Order creation response
        """
        payload = {
            "symbol": symbol,
            "amount": str(quantity),
            "side": side,
            "reduce_only": reduce_only,
            "slippage_percent": slippage_percent
        }

        if client_order_id:
            payload["client_order_id"] = client_order_id

        request = self._create_signed_request("create_market_order", payload)

        if not self.release_mode:
            print(f"Placing {side} market order: {quantity} {symbol}")

        return await self._make_request("POST", "/orders/create_market", data=request, signed=True)

    async def place_stop_order(self, symbol: str, side: str, trigger_price: str,
                              order_type: str = "market",
                              limit_price: Optional[str] = None,
                              quantity: Optional[str] = None,
                              reduce_only: bool = False,
                              client_order_id: Optional[str] = None) -> dict:
        """
        Place a stop order (stop-loss or take-profit).
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            side: Order side ("bid" for buy, "ask" for sell)
            trigger_price: Price at which to trigger the order
            order_type: Order type when triggered ("market" or "limit")
            limit_price: Limit price if order_type is "limit"
            quantity: Order quantity (None uses full position)
            reduce_only: If True, order will only reduce position (default False)
            client_order_id: Optional client-specified order ID

        Returns:
            Stop order creation response
        """
        payload = {
            "symbol": symbol,
            "side": side,
            "stop_price": str(trigger_price),
            "order_type": order_type,
            "reduce_only": reduce_only
        }

        if limit_price:
            payload["limit_price"] = str(limit_price)
        if quantity:
            payload["amount"] = str(quantity)
        if client_order_id:
            payload["client_order_id"] = client_order_id

        request = self._create_signed_request("create_stop_order", payload)
        return await self._make_request("POST", "/orders/create_stop", data=request, signed=True)

    async def cancel_order(self, symbol: str, order_id: Optional[int] = None,
                          client_order_id: Optional[str] = None) -> dict:
        """
        Cancel a specific order.
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            order_id: Exchange order ID
            client_order_id: Client-specified order ID

        Returns:
            Cancellation response

        Note:
            Must provide either order_id or client_order_id
        """
        if not order_id and not client_order_id:
            raise ValueError("Must provide either order_id or client_order_id")

        payload = {"symbol": symbol}

        if order_id:
            payload["order_id"] = order_id
        if client_order_id:
            payload["client_order_id"] = client_order_id

        request = self._create_signed_request("cancel_order", payload)

        if not self.release_mode:
            print(f"Cancelling order {order_id or client_order_id} for {symbol}")

        return await self._make_request("POST", "/orders/cancel", data=request, signed=True)

    async def cancel_all_orders(self, symbol: Optional[str] = None,
                               all_symbols: bool = False,
                               exclude_reduce_only: bool = False) -> dict:
        """
        Cancel all open orders.
        Requires authentication.

        Args:
            symbol: Market symbol to cancel orders for (e.g., "BTC")
            all_symbols: If True, cancel orders for all symbols
            exclude_reduce_only: If True, don't cancel reduce-only orders

        Returns:
            Cancellation response
        """
        payload = {
            "all_symbols": all_symbols,
            "exclude_reduce_only": exclude_reduce_only
        }

        if symbol and not all_symbols:
            payload["symbol"] = symbol

        request = self._create_signed_request("cancel_all_orders", payload)

        if not self.release_mode:
            if all_symbols:
                print("Cancelling all open orders for all symbols")
            else:
                print(f"Cancelling all open orders for {symbol}")

        return await self._make_request("POST", "/orders/cancel_all", data=request, signed=True)

    async def cancel_stop_order(self, symbol: str, order_id: Optional[int] = None,
                               client_order_id: Optional[str] = None) -> dict:
        """
        Cancel a specific stop order.
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            order_id: Exchange order ID
            client_order_id: Client-specified order ID

        Returns:
            Cancellation response

        Note:
            Must provide either order_id or client_order_id
        """
        if not order_id and not client_order_id:
            raise ValueError("Must provide either order_id or client_order_id")

        payload = {"symbol": symbol}

        if order_id:
            payload["order_id"] = order_id
        if client_order_id:
            payload["client_order_id"] = client_order_id

        request = self._create_signed_request("cancel_stop_order", payload)
        return await self._make_request("POST", "/orders/cancel_stop", data=request, signed=True)

    async def batch_orders(self, actions: List[dict]) -> dict:
        """
        Execute multiple order operations in a single request.
        Requires authentication.

        Args:
            actions: List of action dictionaries, each containing:
                     - type: "Create", "Cancel", "CancelAll", etc.
                     - data: Action-specific data

        Returns:
            Batch operation results

        Example:
            actions = [
                {
                    "type": "Create",
                    "data": {
                        "account": "...",
                        "signature": "...",
                        "timestamp": 123456789,
                        "expiry_window": 5000,
                        "symbol": "BTC",
                        "price": "100000",
                        "amount": "0.1",
                        "side": "bid",
                        "tif": "GTC"
                    }
                },
                {
                    "type": "Cancel",
                    "data": {
                        "account": "...",
                        "signature": "...",
                        "timestamp": 123456789,
                        "expiry_window": 5000,
                        "symbol": "BTC",
                        "order_id": 12345
                    }
                }
            ]
        """
        payload = {"actions": actions}
        return await self._make_request("POST", "/orders/batch", data=payload, signed=True)

    async def get_order_status(self, symbol: str, order_id: Optional[int] = None,
                              client_order_id: Optional[str] = None) -> dict:
        """
        Get status of a specific order.
        Requires authentication.

        Args:
            symbol: Market symbol (e.g., "BTC")
            order_id: Exchange order ID
            client_order_id: Client-specified order ID

        Returns:
            Order status information

        Note:
            Must provide either order_id or client_order_id
        """
        if not order_id and not client_order_id:
            raise ValueError("Must provide either order_id or client_order_id")

        payload = {"symbol": symbol}

        if order_id:
            payload["order_id"] = order_id
        if client_order_id:
            payload["client_order_id"] = client_order_id

        request = self._create_signed_request("get_order", payload)

        if not self.release_mode:
            print(f"Getting status for order {order_id or client_order_id}")

        return await self._make_request("POST", "/orders/status", data=request, signed=True)

    async def get_open_orders(self, symbol: Optional[str] = None) -> dict:
        """
        Get all open orders.
        Requires authentication.

        Args:
            symbol: Optional market symbol to filter by (e.g., "BTC")

        Returns:
            List of open orders
        """
        params = {"account": self.public_key}
        if symbol:
            params["symbol"] = symbol

        return await self._make_request("GET", "/orders", params=params, signed=False)

    async def get_order_history(self, symbol: Optional[str] = None,
                               start_time: Optional[int] = None,
                               end_time: Optional[int] = None,
                               limit: int = 100,
                               offset: int = 0) -> dict:
        """
        Get order history.
        Requires authentication.

        Args:
            symbol: Optional market symbol to filter by (e.g., "BTC")
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Number of records to return (default 100)
            offset: Number of records to skip (default 0)

        Returns:
            Order history
        """
        params = {
            "account": self.public_key,
            "limit": limit,
            "offset": offset
        }

        if symbol:
            params["symbol"] = symbol
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        return await self._make_request("GET", "/orders/history", params=params, signed=False)

    async def get_trade_history(self, symbol: Optional[str] = None,
                                start_time: Optional[int] = None,
                                end_time: Optional[int] = None,
                                limit: int = 100,
                                offset: int = 0) -> dict:
        """
        Get trade history.
        Requires authentication.

        Args:
            symbol: Optional market symbol to filter by (e.g., "BTC")
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Number of records to return (default 100)
            offset: Number of records to skip (default 0)

        Returns:
            Trade history
        """
        params = {
            "account": self.public_key,
            "limit": limit,
            "offset": offset
        }

        if symbol:
            params["symbol"] = symbol
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        return await self._make_request("GET", "/positions/history", params=params, signed=False)

    # ============================================================================
    # PRIVATE ENDPOINTS - Subaccount Management
    # ============================================================================

    async def create_subaccount(self, subaccount_name: str) -> dict:
        """
        Create a new subaccount.
        Requires authentication.

        Args:
            subaccount_name: Name for the new subaccount

        Returns:
            Subaccount creation response
        """
        payload = {"subaccount_name": subaccount_name}
        request = self._create_signed_request("create_subaccount", payload)
        return await self._make_request("POST", "/subaccount/create", data=request, signed=True)

    async def transfer_subaccount_fund(self, from_account: str, to_account: str,
                                      amount: str, currency: str = "USDC") -> dict:
        """
        Transfer funds between subaccounts.
        Requires authentication.

        Args:
            from_account: Source account address
            to_account: Destination account address
            amount: Amount to transfer
            currency: Currency to transfer (default "USDC")

        Returns:
            Transfer response
        """
        payload = {
            "from_account": from_account,
            "to_account": to_account,
            "amount": str(amount),
            "currency": currency
        }
        request = self._create_signed_request("transfer_subaccount_fund", payload)
        return await self._make_request("POST", "/subaccount/transfer", data=request, signed=True)

    # ============================================================================
    # PRIVATE ENDPOINTS - Wallet Management
    # ============================================================================

    async def request_withdrawal(self, amount: str, destination: str,
                                 currency: str = "USDC") -> dict:
        """
        Request a withdrawal from the exchange.
        Requires authentication.

        Args:
            amount: Amount to withdraw
            destination: Destination address
            currency: Currency to withdraw (default "USDC")

        Returns:
            Withdrawal request response
        """
        payload = {
            "amount": str(amount),
            "destination": destination,
            "currency": currency
        }
        request = self._create_signed_request("request_withdrawal", payload)
        return await self._make_request("POST", "/wallet/withdraw", data=request, signed=True)

    # ============================================================================
    # GENERIC SIGNED REQUEST METHOD
    # ============================================================================

    async def signed_request(self, method: str, endpoint: str,
                            request_type: str, payload: Optional[dict] = None) -> dict:
        """
        Generic method for making signed requests to the Pacifica API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (should start with /)
            request_type: Type of request for signing (e.g., 'create_order')
            payload: Request payload (will be signed)

        Returns:
            JSON response from the API

        Example:
            response = await client.signed_request(
                "POST",
                "/orders/create",
                "create_order",
                {"symbol": "BTC", "price": "100000", "amount": "0.1", "side": "bid", "tif": "GTC"}
            )
        """
        if payload is None:
            payload = {}

        request = self._create_signed_request(request_type, payload)
        return await self._make_request(method, endpoint, data=request, signed=True)