import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aegis_worker.config import settings
from aegis_worker.live_life import LiveLifeReviewAgent
from aegis_worker.risk.manager import RiskManager


def signal(action: str = "BUY") -> SimpleNamespace:
    return SimpleNamespace(
        symbol="EURUSDm",
        action=action,
        confidence=0.66,
        lot_size=0.01,
        entry_type="MARKET",
        stop_loss_pips=200,
        take_profit_pips=400,
        reason="Deterministic setup."
    )


class LiveLifeTests(unittest.TestCase):
    def test_local_profile_approves_a_trade_setup_without_openai(self) -> None:
        reviewed = LiveLifeReviewAgent().review(signal())

        self.assertTrue(reviewed.approved_for_risk_check)
        self.assertGreaterEqual(reviewed.confidence, 0.70)
        self.assertTrue(any("OpenAI/news review is bypassed" in item for item in reviewed.warnings))

    def test_local_profile_hands_valid_setup_to_risk_without_research_gate(self) -> None:
        reviewed = LiveLifeReviewAgent().review(signal(), {"research": {"successful_sources": 0}})
        account = {"connected": True, "is_demo": True, "trade_allowed": True, "trade_expert": True}

        with patch.object(settings, "trading_profile", "live_life"):
            result = RiskManager().validate(reviewed, account, {"opened": 0, "closed": 0, "net_profit": 0})

        self.assertTrue(result["approved"])
        self.assertEqual(reviewed.news_risk, "BYPASSED")
        self.assertEqual(reviewed.research_source_count, 0)

    def test_local_profile_does_not_turn_hold_into_a_trade(self) -> None:
        reviewed = LiveLifeReviewAgent().review(signal("HOLD"))

        self.assertFalse(reviewed.approved_for_risk_check)
        self.assertEqual(reviewed.action, "HOLD")

    def test_real_account_remains_blocked(self) -> None:
        reviewed = LiveLifeReviewAgent().review(signal())
        result = RiskManager().validate(
            reviewed,
            {"connected": True, "is_demo": False, "trade_allowed": True, "trade_expert": True}
        )

        self.assertFalse(result["approved"])
        self.assertIn("demo", result["reason"].lower())


if __name__ == "__main__":
    unittest.main()
