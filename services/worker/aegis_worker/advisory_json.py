import json

from aegis_worker.agents.ai_review_agent import AiReviewAgent
from aegis_worker.agents.market_agent import build_signal
from aegis_worker.mt5.client import DemoMt5Client
from aegis_worker.risk.manager import RiskManager

SYMBOLS = ["XAUUSDm", "EURUSDm", "BTCUSDm"]


def main() -> None:
    client = DemoMt5Client()
    ai_review_agent = AiReviewAgent()
    risk_manager = RiskManager()
    account = client.account_info()
    positions = client.positions()
    ranked = []

    for symbol in SYMBOLS:
        symbol_positions = [position for position in positions if position["symbol"] == symbol]
        try:
            candles = client.candles(symbol=symbol, timeframe="M5", count=200)
            symbol_info = client.symbol_info(symbol)
            signal = build_signal(symbol=symbol, candles=candles, symbol_info=symbol_info)
            reviewed = ai_review_agent.review(
                signal=signal,
                context={
                    "account": account,
                    "open_positions": positions,
                    "symbol_info": symbol_info,
                    "latest_candle": candles[-1] if candles else None,
                    "mode": "demo-only-read-only-advisory"
                }
            )
            risk = risk_manager.validate(signal=reviewed, account=account)
            veto_reasons = []
            if symbol_positions:
                veto_reasons.append("Open position already exists for this symbol.")
            if not risk.get("approved"):
                veto_reasons.append(str(risk.get("reason")))

            ranked.append({
                "symbol": symbol,
                "rank_score": round(float(reviewed.confidence) * (0 if veto_reasons else 100), 2),
                "action": reviewed.action,
                "confidence": reviewed.confidence,
                "can_trade_now": len(veto_reasons) == 0,
                "veto_reasons": veto_reasons,
                "explanation": reviewed.reason,
                "warnings": reviewed.warnings,
                "open_position_count": len(symbol_positions),
                "stop_loss_points": reviewed.stop_loss_pips,
                "take_profit_points": reviewed.take_profit_pips
            })
        except Exception as error:
            ranked.append({
                "symbol": symbol,
                "rank_score": 0,
                "action": "HOLD",
                "confidence": 0,
                "can_trade_now": False,
                "veto_reasons": [str(error)],
                "explanation": "Advisory scan failed for this symbol.",
                "warnings": [],
                "open_position_count": len(symbol_positions),
                "stop_loss_points": 0,
                "take_profit_points": 0
            })

    ranked.sort(key=lambda item: item["rank_score"], reverse=True)
    print(json.dumps({"setups": ranked, "positions": positions, "account": account}))


if __name__ == "__main__":
    main()
