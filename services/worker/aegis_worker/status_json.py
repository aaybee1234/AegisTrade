import json

from aegis_worker.mt5.client import DemoMt5Client


def main() -> None:
    client = DemoMt5Client()
    account = client.account_info()
    positions = client.positions()
    payload = {
        "account": account,
        "positions": positions,
        "summary": {
            "open_positions": len(positions),
            "floating_pl": round(sum(position["profit"] for position in positions), 2)
        }
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
