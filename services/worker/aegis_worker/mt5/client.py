from typing import Any

from aegis_worker.config import settings


class DemoMt5Client:
    """MT5 boundary for Exness demo trading."""

    def __init__(self) -> None:
        self.mt5 = None
        self.connected = False
        self.connection_error: str | None = None
        self._connect()

    def _has_credentials(self) -> bool:
        return bool(settings.exness_demo_login and settings.exness_demo_password and settings.exness_demo_server)

    def _connect(self) -> None:
        if not self._has_credentials():
            self.connection_error = "Missing EXNESS_DEMO_LOGIN, EXNESS_DEMO_PASSWORD, or EXNESS_DEMO_SERVER."
            return

        try:
            import MetaTrader5 as mt5
        except ImportError:
            self.connection_error = "MetaTrader5 Python package is not installed."
            return

        if not mt5.initialize():
            self.connection_error = f"MT5 initialize failed: {mt5.last_error()}"
            return

        authorized = mt5.login(
            login=int(settings.exness_demo_login or "0"),
            password=settings.exness_demo_password,
            server=settings.exness_demo_server
        )
        if not authorized:
            self.connection_error = f"MT5 login failed: {mt5.last_error()}"
            return

        self.mt5 = mt5
        self.connected = True

    def account_info(self) -> dict[str, Any]:
        if not self.connected or self.mt5 is None:
            return {
                "login": "demo-local" if not self._has_credentials() else settings.exness_demo_login,
                "balance": 10000 if not self._has_credentials() else 0,
                "equity": 10000 if not self._has_credentials() else 0,
                "profit": 0,
                "margin": 0,
                "margin_free": 10000 if not self._has_credentials() else 0,
                "is_demo": True,
                "connected": False,
                "connection_error": self.connection_error
            }

        info = self.mt5.account_info()
        if info is None:
            return {
                "login": settings.exness_demo_login,
                "balance": 0,
                "equity": 0,
                "profit": 0,
                "margin": 0,
                "margin_free": 0,
                "is_demo": False,
                "connected": False,
                "connection_error": f"MT5 account_info failed: {self.mt5.last_error()}"
            }

        data = info._asdict()
        trade_mode = data.get("trade_mode")
        return {
            "login": str(data.get("login")),
            "balance": float(data.get("balance", 0)),
            "equity": float(data.get("equity", 0)),
            "profit": float(data.get("profit", 0)),
            "margin": float(data.get("margin", 0)),
            "margin_free": float(data.get("margin_free", 0)),
            "is_demo": trade_mode == self.mt5.ACCOUNT_TRADE_MODE_DEMO,
            "connected": True,
            "server": data.get("server"),
            "currency": data.get("currency"),
            "trade_allowed": bool(data.get("trade_allowed")),
            "trade_expert": bool(data.get("trade_expert"))
        }

    def positions(self) -> list[dict[str, Any]]:
        if not self.connected or self.mt5 is None:
            return []

        positions = self.mt5.positions_get() or []
        return [
            {
                "ticket": str(position.ticket),
                "symbol": position.symbol,
                "type": "BUY" if position.type == self.mt5.POSITION_TYPE_BUY else "SELL",
                "volume": float(position.volume),
                "price_open": float(position.price_open),
                "price_current": float(position.price_current),
                "sl": float(position.sl),
                "tp": float(position.tp),
                "profit": float(position.profit),
                "magic": int(position.magic),
                "comment": position.comment
            }
            for position in positions
        ]

    def has_open_position(self, symbol: str | None = None) -> bool:
        positions = self.positions()
        if symbol is None:
            return len(positions) > 0
        return any(position["symbol"] == symbol for position in positions)

    def symbol_info(self, symbol: str) -> dict[str, Any]:
        if not self.connected or self.mt5 is None:
            return {"symbol": symbol, "point": 0.01 if symbol.startswith("BTC") or symbol.startswith("XAU") else 0.00001, "spread": 0}

        if not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 could not select symbol {symbol}: {self.mt5.last_error()}")

        info = self.mt5.symbol_info(symbol)
        tick = self.mt5.symbol_info_tick(symbol)
        if info is None:
            raise RuntimeError(f"MT5 symbol info unavailable: {symbol}")

        data = info._asdict()
        return {
            "symbol": symbol,
            "point": float(data.get("point", 0.00001)),
            "spread": int(data.get("spread", 0)),
            "digits": int(data.get("digits", 5)),
            "trade_stops_level": int(data.get("trade_stops_level", 0)),
            "bid": float(tick.bid) if tick else 0,
            "ask": float(tick.ask) if tick else 0
        }

    def close_position(self, ticket: int) -> dict[str, Any]:
        if not self.connected or self.mt5 is None:
            return {
                "closed": False,
                "ticket": str(ticket),
                "error": self.connection_error or "MT5 is not connected."
            }

        positions = self.mt5.positions_get(ticket=ticket)
        if not positions:
            return {
                "closed": False,
                "ticket": str(ticket),
                "error": "Position not found."
            }

        position = positions[0]
        symbol = position.symbol
        if not self.mt5.symbol_select(symbol, True):
            return {
                "closed": False,
                "ticket": str(ticket),
                "error": f"MT5 could not select symbol {symbol}: {self.mt5.last_error()}"
            }

        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return {
                "closed": False,
                "ticket": str(ticket),
                "error": f"MT5 tick unavailable for {symbol}."
            }

        is_buy = position.type == self.mt5.POSITION_TYPE_BUY
        close_type = self.mt5.ORDER_TYPE_SELL if is_buy else self.mt5.ORDER_TYPE_BUY
        price = tick.bid if is_buy else tick.ask
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": float(position.volume),
            "type": close_type,
            "price": price,
            "deviation": 20,
            "magic": 260625,
            "comment": "AegisTrade close demo",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC
        }
        result = self.mt5.order_send(request)
        if result is None:
            return {
                "closed": False,
                "ticket": str(ticket),
                "error": f"MT5 order_send failed: {self.mt5.last_error()}"
            }

        result_data = result._asdict()
        return {
            "closed": result_data.get("retcode") == self.mt5.TRADE_RETCODE_DONE,
            "ticket": str(ticket),
            "retcode": result_data.get("retcode"),
            "comment": result_data.get("comment"),
            "symbol": symbol,
            "volume": float(position.volume)
        }

    def candles(self, symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]:
        if not self.connected or self.mt5 is None:
            base = 2300 if symbol.startswith("XAU") else 1.08
            return [{"close": base + index * 0.01} for index in range(count)]

        timeframe_map = {
            "M1": self.mt5.TIMEFRAME_M1,
            "M5": self.mt5.TIMEFRAME_M5,
            "M15": self.mt5.TIMEFRAME_M15,
            "H1": self.mt5.TIMEFRAME_H1
        }
        rates = self.mt5.copy_rates_from_pos(symbol, timeframe_map.get(timeframe, self.mt5.TIMEFRAME_M5), 0, count)
        if rates is None:
            raise RuntimeError(f"MT5 candle fetch failed for {symbol}: {self.mt5.last_error()}")

        return [
            {
                "time": int(rate["time"]),
                "open": float(rate["open"]),
                "high": float(rate["high"]),
                "low": float(rate["low"]),
                "close": float(rate["close"]),
                "tick_volume": int(rate["tick_volume"])
            }
            for rate in rates
        ]

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        if not self.connected or self.mt5 is None:
            has_credentials = self._has_credentials()
            return {
                "accepted": not has_credentials,
                "mode": "placeholder-demo" if not has_credentials else "mt5-not-connected",
                "order": order,
                "ticket": "placeholder-ticket" if not has_credentials else None,
                "connection_error": self.connection_error
            }

        symbol = order["symbol"]
        if not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 could not select symbol {symbol}: {self.mt5.last_error()}")

        tick = self.mt5.symbol_info_tick(symbol)
        symbol_info = self.mt5.symbol_info(symbol)
        if tick is None or symbol_info is None:
            raise RuntimeError(f"MT5 symbol unavailable: {symbol}")

        action = order["action"]
        order_type = self.mt5.ORDER_TYPE_BUY if action == "BUY" else self.mt5.ORDER_TYPE_SELL
        price = tick.ask if action == "BUY" else tick.bid
        point = symbol_info.point
        min_stop_points = max(getattr(symbol_info, "trade_stops_level", 0), 1)
        sl_points = max(int(order["stop_loss_pips"]), min_stop_points + 50)
        tp_points = max(int(order["take_profit_pips"]), min_stop_points + 100)
        sl_distance = sl_points * point
        tp_distance = tp_points * point
        sl = price - sl_distance if action == "BUY" else price + sl_distance
        tp = price + tp_distance if action == "BUY" else price - tp_distance

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(order["lot_size"]),
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 260625,
            "comment": "AegisTrade demo order",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC
        }
        result = self.mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"MT5 order_send failed: {self.mt5.last_error()}")

        result_data = result._asdict()
        return {
            "accepted": result_data.get("retcode") == self.mt5.TRADE_RETCODE_DONE,
            "mode": "mt5-demo",
            "ticket": str(result_data.get("order")),
            "retcode": result_data.get("retcode"),
            "comment": result_data.get("comment"),
            "order": order
        }
