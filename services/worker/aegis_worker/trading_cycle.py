from typing import Any

from aegis_worker.agents.ai_review_agent import AiReviewAgent
from aegis_worker.agents.market_agent import build_signal
from aegis_worker.config import settings
from aegis_worker.mt5.client import DemoMt5Client
from aegis_worker.risk.manager import RiskManager

SYMBOLS = ["XAUUSDm", "EURUSDm", "BTCUSDm"]


def run_cycle(execute: bool | None = None) -> dict[str, Any]:
    should_execute = settings.auto_trade_enabled if execute is None else execute
    client = DemoMt5Client()
    ai_review_agent = AiReviewAgent()
    risk_manager = RiskManager()
    events: list[dict[str, Any]] = []

    account = client.account_info()
    if not account.get("connected"):
        return {"ok": False, "executed": False, "account": account, "events": events}
    if not account.get("is_demo"):
        return {
            "ok": False,
            "executed": False,
            "account": account,
            "events": [{"type": "veto", "reason": "AegisTrade autonomous mode is demo-only."}]
        }

    positions = client.positions()
    daily = client.daily_trade_stats()
    if not should_execute:
        return {
            "ok": True,
            "executed": False,
            "reason": "AUTO_TRADE_ENABLED is false; advisory and monitoring remain active.",
            "account": account,
            "positions": positions,
            "daily": daily,
            "events": events
        }

    for result in client.close_profit_targets():
        events.append({"type": "profit_close", "result": result})

    positions = client.positions()

    if daily["opened"] >= settings.max_daily_trades or daily["closed"] >= settings.max_daily_trades:
        events.append({"type": "veto", "reason": "Daily trade limit reached."})
        return {"ok": True, "executed": True, "account": account, "positions": positions, "daily": daily, "events": events}

    if len(positions) >= settings.max_open_trades:
        events.append({"type": "veto", "reason": "Maximum open trades reached."})
        return {"ok": True, "executed": True, "account": account, "positions": positions, "daily": daily, "events": events}

    for symbol in SYMBOLS:
        positions = client.positions()
        if any(position["symbol"] == symbol for position in positions):
            events.append({"type": "skip", "symbol": symbol, "reason": "Position already open."})
            continue
        if len(positions) >= settings.max_open_trades:
            break

        try:
            candles = client.candles(symbol=symbol, timeframe="M5", count=200)
            symbol_info = client.symbol_info(symbol)
            signal = build_signal(symbol=symbol, candles=candles, symbol_info=symbol_info)
            reviewed = ai_review_agent.review(
                signal=signal,
                context={
                    "account": account,
                    "daily": daily,
                    "open_positions": positions,
                    "symbol_info": symbol_info,
                    "latest_candle": candles[-1] if candles else None,
                    "mode": "demo-only"
                }
            )
            decision = risk_manager.validate(signal=reviewed, account=account, daily_stats=daily)
            if not decision["approved"]:
                events.append({
                    "type": "veto",
                    "symbol": symbol,
                    "action": reviewed.action,
                    "reason": decision["reason"],
                    "explanation": reviewed.reason,
                    "warnings": reviewed.warnings
                })
                continue

            result = client.place_order(decision["order"])
            events.append({"type": "order", "symbol": symbol, "result": result})
            if result.get("accepted"):
                break
        except Exception as error:
            events.append({"type": "error", "symbol": symbol, "reason": str(error)})

    return {
        "ok": True,
        "executed": True,
        "account": account,
        "positions": client.positions(),
        "daily": client.daily_trade_stats(),
        "events": events
    }
