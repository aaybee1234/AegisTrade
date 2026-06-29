import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aegis_worker.config import settings
from aegis_worker.event_log import append_log

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ACTIVITY_PATH = PROJECT_ROOT / "runtime" / "accounts" / settings.mt5_account_id / "ai_activity.json"


def _read_activity() -> dict[str, Any]:
    if not ACTIVITY_PATH.exists():
        return {}
    try:
        return json.loads(ACTIVITY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def record_ai_activity(
    *,
    status: str,
    symbol: str,
    latency_ms: int,
    request_id: str | None = None,
    response_id: str | None = None,
    response_model: str | None = None,
    usage: dict[str, Any] | None = None,
    error: str | None = None
) -> None:
    current = _read_activity()
    attempted = status in {"success", "error"}
    current["configured"] = bool(settings.openai_api_key)
    current["configured_model"] = settings.openai_model
    current["total_requests"] = int(current.get("total_requests", 0)) + (1 if attempted else 0)
    current["successful_requests"] = int(current.get("successful_requests", 0)) + (1 if status == "success" else 0)
    current["failed_requests"] = int(current.get("failed_requests", 0)) + (1 if status == "error" else 0)
    current["skipped_reviews"] = int(current.get("skipped_reviews", 0)) + (1 if status == "not_configured" else 0)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    current["last_call"] = {
        "status": status,
        "symbol": symbol,
        "latency_ms": latency_ms,
        "request_id": request_id,
        "response_id": response_id,
        "response_model": response_model,
        "usage": usage or {},
        "error": error
    }

    ACTIVITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = ACTIVITY_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(current), encoding="utf-8")
    temporary.replace(ACTIVITY_PATH)
    append_log("ai", {"event": "openai_review", "status": status, "symbol": symbol, "latency_ms": latency_ms, "request_id": request_id, "response_id": response_id, "response_model": response_model, "usage": usage or {}, "error": error})
