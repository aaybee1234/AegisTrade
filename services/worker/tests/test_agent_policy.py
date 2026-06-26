import json
import unittest
from types import SimpleNamespace

from aegis_worker.agents.ai_review_agent import AiReviewAgent
from aegis_worker.risk.manager import RiskManager


class AgentPolicyTests(unittest.TestCase):
    def test_ai_cannot_rewrite_trade_parameters(self) -> None:
        signal = SimpleNamespace(
            symbol="EURUSDm",
            action="BUY",
            confidence=0.68,
            lot_size=0.01,
            entry_type="MARKET",
            stop_loss_pips=200,
            take_profit_pips=400,
            reason="Deterministic trend signal."
        )
        body = {
            "output_text": json.dumps({
                "symbol": "BTCUSDm",
                "action": "SELL",
                "confidence": 0.99,
                "lot_size": 1.0,
                "entry_type": "LIMIT",
                "stop_loss_pips": 1,
                "take_profit_pips": 999999,
                "approved_for_risk_check": True,
                "reason": "Reviewed",
                "warnings": []
            })
        }

        reviewed = AiReviewAgent()._parse_review(body, signal)

        self.assertEqual(reviewed.symbol, signal.symbol)
        self.assertEqual(reviewed.action, signal.action)
        self.assertEqual(reviewed.lot_size, signal.lot_size)
        self.assertEqual(reviewed.stop_loss_pips, signal.stop_loss_pips)
        self.assertEqual(reviewed.take_profit_pips, signal.take_profit_pips)
        self.assertEqual(reviewed.confidence, signal.confidence)

    def test_daily_limit_is_a_hard_veto(self) -> None:
        signal = SimpleNamespace(
            symbol="EURUSDm",
            action="BUY",
            confidence=0.68,
            lot_size=0.01,
            stop_loss_pips=200,
            take_profit_pips=400,
            approved_for_risk_check=True
        )
        account = {
            "connected": True,
            "is_demo": True,
            "trade_allowed": True,
            "trade_expert": True
        }

        result = RiskManager().validate(signal, account, {"closed": 100})

        self.assertFalse(result["approved"])
        self.assertIn("Daily", result["reason"])

    def test_real_account_is_always_rejected(self) -> None:
        signal = SimpleNamespace(action="HOLD", reason="No setup")
        account = {"connected": True, "is_demo": False}

        result = RiskManager().validate(signal, account)

        self.assertFalse(result["approved"])
        self.assertIn("demo", result["reason"].lower())


if __name__ == "__main__":
    unittest.main()
