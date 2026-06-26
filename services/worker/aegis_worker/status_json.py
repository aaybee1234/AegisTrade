import json
from typing import Any

from aegis_worker.config import settings
from aegis_worker.mt5.client import DemoMt5Client


def build_status(client: DemoMt5Client | None = None) -> dict[str, Any]:
    active_client = client or DemoMt5Client()
    account = active_client.account_info()
    positions = active_client.positions()
    daily = active_client.daily_trade_stats()
    return {
        "account": account,
        "positions": positions,
        "daily": daily,
        "bot": {
            "auto_trade_enabled": settings.auto_trade_enabled,
            "max_open_trades": settings.max_open_trades,
            "max_daily_trades": settings.max_daily_trades,
            "max_risk_per_trade_usd": settings.max_risk_per_trade_usd,
            "target_profit_per_trade_usd": settings.target_profit_per_trade_usd
        },
        "summary": {
            "open_positions": len(positions),
            "floating_pl": round(sum(position["profit"] for position in positions), 2)
        }
    }


def main() -> None:
    print(json.dumps(build_status()))


if __name__ == "__main__":
    main()
