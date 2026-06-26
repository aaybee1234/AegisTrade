import json

from aegis_worker.trading_cycle import run_cycle


def main() -> None:
    print(json.dumps(run_cycle()))


if __name__ == "__main__":
    main()
