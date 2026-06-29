import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aegis_worker.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGS_DIR = PROJECT_ROOT / "runtime" / "accounts" / settings.mt5_account_id / "logs"

_ALLOWED_STREAMS = {"app", "trade", "ai"}


def append_log(stream: str, event: dict[str, Any]) -> None:
    if stream not in _ALLOWED_STREAMS:
        stream = "app"

    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stream": stream,
        **event
    }
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with (LOGS_DIR / f"{stream}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str, separators=(",", ":")) + "\n")
