import json
from pathlib import Path
from typing import Any

from aegis_worker.config import settings
from aegis_worker.mt5.client import DemoMt5Client
from aegis_worker.trading_cycle import run_cycle

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ACCOUNT_DIR = PROJECT_ROOT / "runtime" / "accounts" / settings.mt5_account_id
COMMANDS_DIR = ACCOUNT_DIR / "commands"


def write_json(name: str, payload: dict[str, Any]) -> None:
    ACCOUNT_DIR.mkdir(parents=True, exist_ok=True)
    destination = ACCOUNT_DIR / name
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(destination)


def read_control() -> dict[str, Any]:
    control_path = ACCOUNT_DIR / "control.json"
    if not control_path.exists():
        return {"auto_trade_enabled": settings.auto_trade_enabled}
    try:
        payload = json.loads(control_path.read_text(encoding="utf-8"))
        return {"auto_trade_enabled": bool(payload.get("auto_trade_enabled", False))}
    except (OSError, ValueError, TypeError):
        return {"auto_trade_enabled": False}


def process_commands(client: DemoMt5Client) -> list[dict[str, Any]]:
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for command_file in sorted(COMMANDS_DIR.glob("*.json")):
        try:
            command = json.loads(command_file.read_text(encoding="utf-8"))
            command_type = command.get("type")
            if command_type == "close_position":
                result = client.close_position(int(command["ticket"]))
            elif command_type == "run_cycle":
                result = run_cycle(execute=read_control()["auto_trade_enabled"])
            elif command_type == "set_auto_trade":
                enabled = bool(command.get("enabled", False))
                write_json("control.json", {"auto_trade_enabled": enabled})
                result = {"ok": True, "auto_trade_enabled": enabled}
            else:
                result = {"ok": False, "error": f"Unknown command: {command_type}"}
            results.append({"id": command_file.stem, "result": result})
            write_json(f"command-{command_file.stem}.json", result)
        except Exception as error:
            results.append({"id": command_file.stem, "error": str(error)})
        finally:
            command_file.unlink(missing_ok=True)
    return results
