import unittest

from aegis_worker.agents.market_agent import build_signal


def make_continuation_candles() -> list[dict[str, float]]:
    candles = []
    price = 1.1000
    for index in range(80):
        price += 0.0002
        candles.append({
            "open": price - 0.00008,
            "high": price + 0.00015,
            "low": price - 0.00015,
            "close": price,
            "tick_volume": 100.0,
            "time": float(index),
        })
    # Latest completed candle stays inside the recent high, so breakout fails while continuation passes.
    candles[-1]["close"] = candles[-2]["close"] - 0.00005
    candles[-1]["high"] = candles[-2]["high"] - 0.00004
    candles.append({
        "open": candles[-1]["close"],
        "high": candles[-1]["close"] + 0.0001,
        "low": candles[-1]["close"] - 0.0001,
        "close": candles[-1]["close"],
        "tick_volume": 80.0,
        "time": 81.0,
    })
    return candles


class MarketAgentTests(unittest.TestCase):
    def test_continuation_setup_can_create_trade_signal(self) -> None:
        signal = build_signal("EURUSDm", make_continuation_candles(), {"point": 0.00001, "spread": 10})

        self.assertEqual(signal.action, "BUY")
        self.assertEqual(signal.strategy, "ema-rsi-continuation")
        self.assertGreaterEqual(signal.confidence, 0.65)
        self.assertGreater(signal.stop_loss_pips, 0)
        self.assertGreater(signal.take_profit_pips, 0)
        self.assertIn("continuation_buy_score", signal.indicators)


if __name__ == "__main__":
    unittest.main()
