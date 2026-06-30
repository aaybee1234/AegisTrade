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

        initialize_args: dict[str, Any] = {
            "login": int(settings.exness_demo_login or "0"),
            "password": settings.exness_demo_password,
            "server": settings.exness_demo_server,
            "timeout": 60_000
        }
        if settings.mt5_terminal_path:
            initialize_args["path"] = settings.mt5_terminal_path

        if not mt5.initialize(**initialize_args):
            self.connection_error = f"MT5 initialize/login failed: {mt5.last_error()}"
            mt5.shutdown()
            return

        info = mt5.account_info()
        if info is None or str(info.login) != str(settings.exness_demo_login):
            self.connection_error = f"MT5 opened but the configured account is unavailable: {mt5.last_error()}"
            mt5.shutdown()
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
                "time": int(getattr(position, "time", 0)),
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

    def has_bot_entry_since(self, symbol: str, timestamp: int) -> bool:
        if not self.connected or self.mt5 is None:
            return False

        from datetime import datetime, timezone

        start = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        deals = self.mt5.history_deals_get(start, now) or []
        return any(
            getattr(deal, "symbol", None) == symbol
            and int(getattr(deal, "magic", 0)) == 260625
            and getattr(deal, "entry", None) == self.mt5.DEAL_ENTRY_IN
            for deal in deals
        )

    def latest_bot_entry_age_seconds(self, symbol: str) -> int | None:
        if not self.connected or self.mt5 is None:
            return None

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        deals = self.mt5.history_deals_get(now - timedelta(days=1), now) or []
        entries = [
            int(getattr(deal, "time", 0))
            for deal in deals
            if getattr(deal, "symbol", None) == symbol
            and int(getattr(deal, "magic", 0)) == 260625
            and getattr(deal, "entry", None) == self.mt5.DEAL_ENTRY_IN
        ]
        if not entries:
            return None
        return max(0, int(now.timestamp()) - max(entries))

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

    def daily_trade_stats(self) -> dict[str, Any]:
        if not self.connected or self.mt5 is None:
            return {
                "opened": 0,
                "closed": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "net_profit": 0,
                "remaining": settings.max_daily_trades
            }

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        deals = self.mt5.history_deals_get(start, now) or []
        bot_deals = [deal for deal in deals if int(getattr(deal, "magic", 0)) == 260625]
        opened = sum(1 for deal in bot_deals if deal.entry == self.mt5.DEAL_ENTRY_IN)
        closed_deals = [
            deal for deal in bot_deals
            if deal.entry in {self.mt5.DEAL_ENTRY_OUT, self.mt5.DEAL_ENTRY_OUT_BY}
        ]
        outcomes = [
            float(deal.profit) + float(deal.commission) + float(deal.swap)
            for deal in closed_deals
        ]
        wins = sum(1 for profit in outcomes if profit > 0)
        losses = sum(1 for profit in outcomes if profit <= 0)
        closed = len(closed_deals)
        return {
            "opened": opened,
            "closed": closed,
            "wins": wins,
            "losses": losses,
            "win_rate": round((wins / closed * 100) if closed else 0, 2),
            "net_profit": round(sum(outcomes), 2),
            "remaining": max(settings.max_daily_trades - closed, 0)
        }

    def _range_bounds(self, range_name: str) -> tuple[Any, Any, str]:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        if range_name == "yesterday":
            return today - timedelta(days=1), today, "Yesterday"
        if range_name == "last3":
            return today - timedelta(days=2), now, "Last 3 days"
        if range_name == "last7":
            return today - timedelta(days=6), now, "Last 7 days"
        return today, now, "Today"

    def _deal_margin_estimate(self, deal: Any) -> float:
        if self.mt5 is None:
            return 0
        symbol = getattr(deal, "symbol", "")
        volume = float(getattr(deal, "volume", 0) or 0)
        price = float(getattr(deal, "price", 0) or 0)
        if not symbol or volume <= 0 or price <= 0:
            return 0
        deal_type = getattr(deal, "type", None)
        order_type = self.mt5.ORDER_TYPE_BUY if deal_type == self.mt5.DEAL_TYPE_BUY else self.mt5.ORDER_TYPE_SELL
        margin = self.mt5.order_calc_margin(order_type, symbol, volume, price)
        return abs(float(margin)) if margin is not None else 0

    def _position_margin_estimate(self, position: dict[str, Any]) -> float:
        if self.mt5 is None:
            return 0
        symbol = position["symbol"]
        order_type = self.mt5.ORDER_TYPE_BUY if position["type"] == "BUY" else self.mt5.ORDER_TYPE_SELL
        margin = self.mt5.order_calc_margin(order_type, symbol, float(position["volume"]), float(position["price_current"]))
        return abs(float(margin)) if margin is not None else 0

    def performance_summary(self, range_name: str = "today") -> dict[str, Any]:
        normalized = range_name if range_name in {"today", "yesterday", "last3", "last7"} else "today"
        if not self.connected or self.mt5 is None:
            return {
                "range": normalized,
                "label": "Today",
                "total_invested_usd": 0,
                "open_invested_usd": 0,
                "realized_return_usd": 0,
                "floating_return_usd": 0,
                "total_return_usd": 0,
                "return_percent": 0,
                "opened": 0,
                "closed": 0,
                "wins": 0,
                "losses": 0
            }

        start, end, label = self._range_bounds(normalized)
        deals = self.mt5.history_deals_get(start, end) or []
        bot_deals = [deal for deal in deals if int(getattr(deal, "magic", 0)) == 260625]
        entry_deals = [deal for deal in bot_deals if getattr(deal, "entry", None) == self.mt5.DEAL_ENTRY_IN]
        closed_deals = [
            deal for deal in bot_deals
            if getattr(deal, "entry", None) in {self.mt5.DEAL_ENTRY_OUT, self.mt5.DEAL_ENTRY_OUT_BY}
        ]
        outcomes = [
            float(getattr(deal, "profit", 0)) + float(getattr(deal, "commission", 0)) + float(getattr(deal, "swap", 0))
            for deal in closed_deals
        ]
        positions = [position for position in self.positions() if int(position.get("magic", 0)) == 260625]
        open_invested = sum(self._position_margin_estimate(position) for position in positions)
        total_invested = sum(self._deal_margin_estimate(deal) for deal in entry_deals)
        if normalized in {"today", "last3", "last7"}:
            total_invested += open_invested
        realized = round(sum(outcomes), 2)
        floating = round(sum(float(position["profit"]) for position in positions), 2)
        total_return = round(realized + floating, 2)
        invested = round(total_invested, 2)
        return {
            "range": normalized,
            "label": label,
            "total_invested_usd": invested,
            "open_invested_usd": round(open_invested, 2),
            "realized_return_usd": realized,
            "floating_return_usd": floating,
            "total_return_usd": total_return,
            "return_percent": round((total_return / invested * 100) if invested else 0, 2),
            "opened": len(entry_deals),
            "closed": len(closed_deals),
            "wins": sum(1 for value in outcomes if value > 0),
            "losses": sum(1 for value in outcomes if value <= 0)
        }

    def performance_ranges(self) -> dict[str, Any]:
        return {
            key: self.performance_summary(key)
            for key in ("today", "yesterday", "last3", "last7")
        }

    def close_profit_targets(self) -> list[dict[str, Any]]:
        results = []
        for position in self.positions():
            if position["magic"] != 260625:
                continue
            if position["profit"] >= settings.target_profit_per_trade_usd:
                results.append(self.close_position(int(position["ticket"])))
        return results

    def _normalized_volume(self, requested: float, symbol_info: Any) -> float:
        minimum = float(symbol_info.volume_min)
        maximum = float(symbol_info.volume_max)
        step = float(symbol_info.volume_step)
        capped = min(max(requested, minimum), maximum)
        steps = int((capped - minimum) / step + 1e-9)
        normalized = minimum + steps * step
        return round(normalized, 8)

    def _estimated_profit(self, order_type: int, symbol: str, volume: float, start: float, end: float) -> float:
        if self.mt5 is None:
            return 0
        result = self.mt5.order_calc_profit(order_type, symbol, volume, start, end)
        return float(result) if result is not None else 0
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
        price = float(tick.ask if action == "BUY" else tick.bid)
        point = float(symbol_info.point)
        digits = int(symbol_info.digits)
        min_stop_points = max(int(getattr(symbol_info, "trade_stops_level", 0)), 1)
        sl_points = max(int(order["stop_loss_pips"]), min_stop_points + 50)
        sl_distance = sl_points * point
        sl = price - sl_distance if action == "BUY" else price + sl_distance

        volume = self._normalized_volume(float(order["lot_size"]), symbol_info)
        estimated_loss = abs(self._estimated_profit(order_type, symbol, volume, price, sl))
        if estimated_loss > settings.max_risk_per_trade_usd:
            scaled = volume * settings.max_risk_per_trade_usd / estimated_loss
            volume = self._normalized_volume(scaled, symbol_info)
            estimated_loss = abs(self._estimated_profit(order_type, symbol, volume, price, sl))

        if estimated_loss > settings.max_risk_per_trade_usd + 0.01:
            return {
                "accepted": False,
                "mode": "risk-veto",
                "ticket": None,
                "comment": (
                    f"Minimum broker volume risks ${estimated_loss:.2f}, above the "
                    f"${settings.max_risk_per_trade_usd:.2f} limit."
                ),
                "order": order
            }

        tick_size = float(getattr(symbol_info, "trade_tick_size", point) or point)
        tick_value = abs(float(getattr(symbol_info, "trade_tick_value", 0) or 0))
        profit_per_price_unit = (tick_value / tick_size) * volume if tick_size > 0 else 0
        desired_profit_usd = max(
            settings.target_profit_per_trade_usd,
            estimated_loss * settings.minimum_risk_reward
        )
        desired_tp_distance = (
            desired_profit_usd / profit_per_price_unit
            if profit_per_price_unit > 0 else int(order["take_profit_pips"]) * point
        )
        tp_distance = max(desired_tp_distance, (min_stop_points + 50) * point)
        tp = price + tp_distance if action == "BUY" else price - tp_distance
        sl = round(sl, digits)
        tp = round(tp, digits)
        estimated_profit = abs(self._estimated_profit(order_type, symbol, volume, price, tp))
        if estimated_loss <= 0 or estimated_profit < estimated_loss * settings.minimum_risk_reward:
            return {
                "accepted": False,
                "mode": "risk-veto",
                "ticket": None,
                "comment": "Broker pricing cannot meet the configured minimum risk/reward.",
                "order": order,
                "estimated_loss_usd": round(estimated_loss, 2),
                "estimated_profit_usd": round(estimated_profit, 2)
            }

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
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
            "order": order,
            "estimated_loss_usd": round(estimated_loss, 2),
            "estimated_profit_usd": round(estimated_profit, 2),
            "volume": volume,
            "sl": sl,
            "tp": tp
        }
