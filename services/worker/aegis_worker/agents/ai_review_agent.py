import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from aegis_worker.config import settings


@dataclass
class ReviewedSignal:
    symbol: str
    action: str
    confidence: float
    lot_size: float
    stop_loss_pips: int
    take_profit_pips: int
    approved_for_risk_check: bool
    reason: str
    warnings: list[str] = field(default_factory=list)
    entry_type: str = "MARKET"

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


class AiReviewAgent:
    def review(self, signal: Any, context: dict[str, Any]) -> ReviewedSignal:
        if not settings.openai_api_key:
            return self._fallback_review(signal, "OPENAI_API_KEY is not configured.")

        try:
            payload = {
                "model": settings.openai_model,
                "input": [
                    {
                        "role": "system",
                        "content": (
                            "You are the AI review agent for a demo-only MT5 trading bot. "
                            "You do not execute trades. Return only valid JSON. "
                            "Be conservative. If the signal is HOLD, keep it HOLD."
                        )
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "signal": signal.model_dump(),
                                "context": context,
                                "required_json_keys": [
                                    "symbol",
                                    "action",
                                    "confidence",
                                    "lot_size",
                                    "entry_type",
                                    "stop_loss_pips",
                                    "take_profit_pips",
                                    "approved_for_risk_check",
                                    "reason",
                                    "warnings"
                                ]
                            }
                        )
                    }
                ],
                "text": {"format": {"type": "json_object"}}
            }
            request = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))

            return self._parse_review(body, signal)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as error:
            return self._fallback_review(signal, f"AI review fallback used: {error}")

    def _parse_review(self, body: dict[str, Any], signal: Any) -> ReviewedSignal:
        output_text = body.get("output_text")
        if not output_text:
            output_text = self._extract_output_text(body)

        data = json.loads(output_text)
        return ReviewedSignal(
            symbol=str(data.get("symbol", signal.symbol)),
            action=str(data.get("action", signal.action)),
            confidence=float(data.get("confidence", signal.confidence)),
            lot_size=float(data.get("lot_size", signal.lot_size)),
            entry_type=str(data.get("entry_type", signal.entry_type)),
            stop_loss_pips=int(data.get("stop_loss_pips", signal.stop_loss_pips)),
            take_profit_pips=int(data.get("take_profit_pips", signal.take_profit_pips)),
            approved_for_risk_check=bool(data.get("approved_for_risk_check", signal.action != "HOLD")),
            reason=str(data.get("reason", signal.reason)),
            warnings=list(data.get("warnings", []))
        )

    def _extract_output_text(self, body: dict[str, Any]) -> str:
        for item in body.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and "text" in content:
                    return str(content["text"])
        raise ValueError("OpenAI response did not include output text.")

    def _fallback_review(self, signal: Any, warning: str) -> ReviewedSignal:
        return ReviewedSignal(
            symbol=signal.symbol,
            action=signal.action,
            confidence=signal.confidence,
            lot_size=signal.lot_size,
            entry_type=signal.entry_type,
            stop_loss_pips=signal.stop_loss_pips,
            take_profit_pips=signal.take_profit_pips,
            approved_for_risk_check=signal.action != "HOLD",
            reason=signal.reason,
            warnings=[warning]
        )
