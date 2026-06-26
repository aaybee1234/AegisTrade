from typing import Any


class RiskManager:
    def __init__(self) -> None:
        self.allowed_symbols = {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "XAUUSDm", "EURUSDm", "GBPUSDm", "USDJPYm", "BTCUSDm"}
        self.max_lot_size = 0.01
        self.min_confidence = 0.65

    def validate(self, signal: Any, account: dict[str, Any]) -> dict[str, Any]:
        if not account.get("is_demo"):
            return {"approved": False, "reason": "Only demo accounts are allowed."}

        if signal.action == "HOLD":
            return {"approved": False, "reason": signal.reason}

        if not getattr(signal, "approved_for_risk_check", True):
            return {"approved": False, "reason": "AI review did not approve risk check handoff."}

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

