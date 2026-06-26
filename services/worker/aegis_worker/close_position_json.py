import json
import sys

from aegis_worker.mt5.client import DemoMt5Client


def main() -> None:
    if len(sys.argv) != 2:
        print(json.dumps({"closed": False, "error": "Usage: python -m aegis_worker.close_position_json <ticket>"}))
        raise SystemExit(2)

    try:
        ticket = int(sys.argv[1])
    except ValueError:
        print(json.dumps({"closed": False, "error": "Ticket must be a number."}))
        raise SystemExit(2)

    client = DemoMt5Client()
    result = client.close_position(ticket)
    print(json.dumps(result))
    raise SystemExit(0 if result.get("closed") else 1)


if __name__ == "__main__":
    main()
