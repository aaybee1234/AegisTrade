import json
from typing import Any

from aegis_worker.agents.ai_review_agent import AiReviewAgent
from aegis_worker.agents.market_agent import build_signal
from aegis_worker.config import settings
from aegis_worker.live_life import LiveLifeReviewAgent
from aegis_worker.portfolio_config import portfolio_for_symbol
from aegis_worker.mt5.client import DemoMt5Client
from aegis_worker.research.market_context import context_for_symbol
from aegis_worker.risk.manager import RiskManager



def build_advisory(client: DemoMt5Client | None = None) -> dict[str, Any]:
    active_client = client or DemoMt5Client()
    review_agent = LiveLifeReviewAgent() if settings.trading_profile == "live_life" else AiReviewAgent()
    risk_manager = RiskManager()
    account = active_client.account_info()
    positions = active_client.positions()
    daily = active_client.daily_trade_stats()
    ranked: list[dict[str, Any]] = []

    for symbol in settings.trading_symbols:
        symbol_positions = [position for position in positions if position["symbol"] == symbol]
        try:
            candles = active_client.candles(symbol=symbol, timeframe="M5", count=200)
            symbol_info = active_client.symbol_info(symbol)
            research = context_for_symbol(symbol)
            signal = build_signal(symbol=symbol, candles=candles, symbol_info=symbol_info)
            reviewed = review_agent.review(
                signal=signal,
                context={
                    "account": account,
                    "daily": daily,
                    "open_positions": positions,
                    "symbol_info": symbol_info,
                    "latest_completed_candle": candles[-2] if len(candles) >= 2 else None,
                    "research": research,
                    "mode": "demo-only-read-only-advisory"
                }
            )
            risk = risk_manager.validate(signal=reviewed, account=account, daily_stats=daily)
            veto_reasons = []
            if symbol_positions:
                veto_reasons.append("Open position already exists for this symbol.")
            if not risk.get("approved"):
                veto_reasons.append(str(risk.get("reason")))

            rank_score = round(float(reviewed.confidence) * (0 if veto_reasons else 100), 2)
            ranked.append({
                "symbol": symbol,
                "portfolio": portfolio_for_symbol(symbol),
                "rank_score": rank_score,
                "action": reviewed.action,
                "confidence": reviewed.confidence,
                "can_trade_now": len(veto_reasons) == 0,
                "veto_reasons": veto_reasons,
                "explanation": reviewed.reason,
                "warnings": reviewed.warnings,
                "open_position_count": len(symbol_positions),
                "stop_loss_points": reviewed.stop_loss_pips,
                "take_profit_points": reviewed.take_profit_pips,
                "strategy": getattr(signal, "strategy", "unknown"),
                "indicators": getattr(signal, "indicators", {}),
                "news_risk": reviewed.news_risk,
                "news_summary": reviewed.news_summary,
                "research_source_count": reviewed.research_source_count,
                "research_errors": research.get("errors", []),
                "headlines": research.get("headlines", [])[:3],
                "crypto_trending": research.get("crypto_trending", [])[:5]
            })
        except Exception as error:
            ranked.append({
                "symbol": symbol,
                "portfolio": portfolio_for_symbol(symbol),
                "rank_score": 0,
                "action": "HOLD",
                "confidence": 0,
                "can_trade_now": False,
                "veto_reasons": [str(error)],
                "explanation": "Advisory scan failed for this symbol.",
                "warnings": [],
                "open_position_count": len(symbol_positions),
                "stop_loss_points": 0,
                "take_profit_points": 0,
                "strategy": "unavailable",
                "indicators": {},
                "news_risk": "UNKNOWN",
                "news_summary": "Research unavailable for this scan.",
                "research_source_count": 0,
                "research_errors": [str(error)],
                "headlines": [],
                "crypto_trending": []
            })

    ranked.sort(key=lambda item: item["rank_score"], reverse=True)
    return {"setups": ranked, "positions": positions, "account": account, "daily": daily, "profile": settings.trading_profile, "environment": settings.trading_environment, "portfolios": settings.trading_portfolios, "symbols": settings.trading_symbols}


def main() -> None:
    print(json.dumps(build_advisory()))


if __name__ == "__main__":
    main()
