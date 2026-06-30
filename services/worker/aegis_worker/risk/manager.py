from typing import Any

from aegis_worker.config import settings


class RiskManager:
    def __init__(self) -> None:
        self.allowed_symbols = set(settings.trading_symbols)
        self.max_lot_size = 0.01
        self.min_confidence = 0.65

    def validate(self, signal: Any, account: dict[str, Any], daily_stats: dict[str, Any] | None = None) -> dict[str, Any]:
        if not account.get("connected"):
            return {"approved": False, "reason": "MT5 is not connected."}

        if not account.get("is_demo"):
            return {"approved": False, "reason": "Only demo accounts are allowed."}

        if not account.get("trade_allowed") or not account.get("trade_expert"):
            return {"approved": False, "reason": "MT5 automated trading is not allowed by the terminal/account."}

        if daily_stats and int(daily_stats.get("closed", 0)) >= settings.max_daily_trades:
            return {"approved": False, "reason": "Daily completed-trade limit reached."}

        if daily_stats and int(daily_stats.get("opened", 0)) >= settings.max_daily_trades:
            return {"approved": False, "reason": "Daily opened-trade limit reached."}

        if daily_stats and float(daily_stats.get("net_profit", 0)) <= -settings.max_daily_loss_usd:
            return {"approved": False, "reason": "Daily loss limit reached. Bot is locked until the next UTC day."}

        if signal.action == "HOLD":
            return {"approved": False, "reason": signal.reason}

        if not getattr(signal, "approved_for_risk_check", True):
            return {"approved": False, "reason": "AI review did not approve risk check handoff."}

        news_risk = getattr(signal, "news_risk", "LOW")
        local_review_bypass = settings.trading_profile == "live_life" and news_risk == "BYPASSED"
        if not local_review_bypass:
            if news_risk not in {"LOW", "MEDIUM"}:
                return {"approved": False, "reason": "AI/news review vetoed this setup."}

            if int(getattr(signal, "research_source_count", 0)) < 2:
                return {"approved": False, "reason": "Research source coverage is too low for automatic execution."}

        if signal.symbol not in self.allowed_symbols:
            return {"approved": False, "reason": "Symbol is not allowed."}

        if signal.lot_size > self.max_lot_size:
            return {"approved": False, "reason": "Lot size is above MVP limit."}

        if signal.confidence < self.min_confidence:
            return {"approved": False, "reason": "Confidence is below threshold."}

        if signal.stop_loss_pips <= 0 or signal.take_profit_pips <= 0:
            return {"approved": False, "reason": "Stop loss and take profit are required."}

        return {
            "approved": True,
            "order": {
                "symbol": signal.symbol,
                "action": signal.action,
                "lot_size": signal.lot_size,
                "stop_loss_pips": signal.stop_loss_pips,
                "take_profit_pips": signal.take_profit_pips
            }
        }
