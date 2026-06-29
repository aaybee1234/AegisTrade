import json
import time
from datetime import datetime, timezone

from aegis_worker.advisory_json import build_advisory
from aegis_worker.config import settings
from aegis_worker.mt5.client import DemoMt5Client
from aegis_worker.runtime_bridge import process_commands, read_control, write_json
from aegis_worker.status_json import build_status
from aegis_worker.trading_cycle import run_cycle

ADVISORY_INTERVAL_SECONDS = 300


def main() -> None:
    last_advisory = 0.0
    last_auto_cycle = 0.0
    while True:
        try:
            client = DemoMt5Client()
            commands = process_commands(client)
            auto_trade_enabled = read_control()["auto_trade_enabled"]
            now = time.monotonic()
            cycle = None
            if auto_trade_enabled and now - last_auto_cycle >= settings.auto_scan_interval_seconds:
                cycle = run_cycle(execute=True)
                last_auto_cycle = now

            status = build_status(client)
            status["bot"]["auto_trade_enabled"] = auto_trade_enabled
            status["bridge"] = {
                "account_id": settings.mt5_account_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "commands_processed": len(commands),
                "cycle_ok": cycle.get("ok") if cycle else None,
                "next_auto_scan_in_seconds": max(0, int(settings.auto_scan_interval_seconds - (now - last_auto_cycle))) if auto_trade_enabled else None
            }
            write_json("status.json", status)

            if now - last_advisory >= ADVISORY_INTERVAL_SECONDS:
                write_json("advisory.json", build_advisory(client))
                last_advisory = now

            print(json.dumps({"ok": True, "connected": status["account"].get("connected")}), flush=True)
        except Exception as error:
            write_json("worker-error.json", {
                "ok": False,
                "error": str(error),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            print(json.dumps({"ok": False, "error": str(error)}), flush=True)
        time.sleep(max(settings.worker_poll_seconds, 3))


if __name__ == "__main__":
    main()
