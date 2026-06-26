from aegis_worker.agents.ai_review_agent import AiReviewAgent
from aegis_worker.agents.market_agent import build_signal
from aegis_worker.mt5.client import DemoMt5Client
from aegis_worker.risk.manager import RiskManager

SYMBOLS = ["XAUUSDm", "EURUSDm", "BTCUSDm"]
MAX_OPEN_TRADES = 2


def main() -> None:
    client = DemoMt5Client()
    ai_review_agent = AiReviewAgent()
    risk_manager = RiskManager()

    account = client.account_info()
    if not account["is_demo"]:
        raise RuntimeError("AegisTrade MVP only supports demo accounts.")

    open_positions = client.positions()
    if len(open_positions) >= MAX_OPEN_TRADES:
        print(f"safety: max open trades reached ({len(open_positions)}/{MAX_OPEN_TRADES}); no new trades placed")
        for position in open_positions:
            print(f"open: {position['symbol']} {position['type']} {position['volume']} profit={position['profit']} ticket={position['ticket']}")
        return

    for symbol in SYMBOLS:
        if client.has_open_position(symbol):
            print(f"{symbol}: skipped - open position already exists")
            continue

        if len(client.positions()) >= MAX_OPEN_TRADES:
            print(f"safety: max open trades reached ({MAX_OPEN_TRADES}); stopping scan")
            return

        candles = client.candles(symbol=symbol, timeframe="M5", count=200)
        symbol_info = client.symbol_info(symbol)
        signal = build_signal(symbol=symbol, candles=candles, symbol_info=symbol_info)
        reviewed_signal = ai_review_agent.review(
            signal=signal,
            context={
                "account": account,
                "open_positions": client.positions(),
                "symbol_info": symbol_info,
                "latest_candle": candles[-1] if candles else None,
                "mode": "demo-only"
            }
        )
        decision = risk_manager.validate(signal=reviewed_signal, account=account)

        if not decision["approved"]:
            print(f"{symbol}: rejected - {decision['reason']}")
            continue

        result = client.place_order(decision["order"])
        print(f"{symbol}: order result {result}")


if __name__ == "__main__":
    main()
