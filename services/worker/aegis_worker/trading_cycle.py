from typing import Any

from aegis_worker.agents.ai_review_agent import AiReviewAgent
from aegis_worker.agents.market_agent import build_signal
from aegis_worker.config import settings
from aegis_worker.mt5.client import DemoMt5Client
from aegis_worker.research.market_context import context_for_symbol
from aegis_worker.risk.manager import RiskManager

SYMBOLS = ["XAUUSDm", "EURUSDm", "BTCUSDm"]


def _latest_completed_candle_time(candles: list[dict[str, Any]]) -> int | None:
    if len(candles) < 2:
        return None
    value = candles[-2].get("time")
    return int(value) if value is not None else None


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
    daily = client.daily_trade_stats()

    if daily["opened"] >= settings.max_daily_trades or daily["closed"] >= settings.max_daily_trades:
        events.append({"type": "veto", "reason": "Daily trade limit reached."})
        return {"ok": True, "executed": True, "account": account, "positions": positions, "daily": daily, "events": events}

    if float(daily.get("net_profit", 0)) <= -settings.max_daily_loss_usd:
        events.append({"type": "veto", "reason": "Daily loss limit reached. Bot is locked until the next UTC day."})
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

        latest_age = client.latest_bot_entry_age_seconds(symbol)
        if latest_age is not None and latest_age < settings.trade_cooldown_seconds:
            events.append({
                "type": "skip",
                "symbol": symbol,
                "reason": f"Cooldown active for {settings.trade_cooldown_seconds - latest_age} more seconds."
            })
            continue

        try:
            candles = client.candles(symbol=symbol, timeframe="M5", count=200)
            candle_time = _latest_completed_candle_time(candles)
            if candle_time is not None and client.has_bot_entry_since(symbol, candle_time):
                events.append({"type": "skip", "symbol": symbol, "reason": "Bot already entered on the latest completed candle."})
                continue

            symbol_info = client.symbol_info(symbol)
            research = context_for_symbol(symbol)
            signal = build_signal(symbol=symbol, candles=candles, symbol_info=symbol_info)
            reviewed = ai_review_agent.review(
                signal=signal,
                context={
                    "account": account,
                    "daily": daily,
                    "open_positions": positions,
                    "symbol_info": symbol_info,
                    "latest_completed_candle": candles[-2] if len(candles) >= 2 else None,
                    "research": research,
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
                    "warnings": reviewed.warnings,
                    "news_risk": reviewed.news_risk,
                    "news_summary": reviewed.news_summary,
                    "research_source_count": reviewed.research_source_count,
                    "indicators": getattr(signal, "indicators", {})
                })
                continue

            result = client.place_order(decision["order"])
            events.append({
                "type": "order",
                "symbol": symbol,
                "action": reviewed.action,
                "result": result,
                "news_risk": reviewed.news_risk,
                "news_summary": reviewed.news_summary,
                "indicators": getattr(signal, "indicators", {})
            })
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
