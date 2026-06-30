from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LiveLifeSignal:
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
    news_risk: str = "BYPASSED"
    news_summary: str = "Live Life profile: OpenAI/news assessment bypassed for demo testing."
    research_source_count: int = 0

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


class LiveLifeReviewAgent:
    """Demo-only local review profile for testing when OpenAI is unavailable."""

    def review(self, signal: Any, context: dict[str, Any] | None = None) -> LiveLifeSignal:
        approved = signal.action != "HOLD"
        warnings = [
            "Live Life is a demo testing profile and does not guarantee profit.",
            "OpenAI/news review is bypassed; deterministic risk and MT5 checks still apply."
        ]
        return LiveLifeSignal(
            symbol=signal.symbol,
            action=signal.action,
            confidence=max(float(signal.confidence), 0.70) if approved else float(signal.confidence),
            lot_size=signal.lot_size,
            entry_type=signal.entry_type,
            stop_loss_pips=signal.stop_loss_pips,
            take_profit_pips=signal.take_profit_pips,
            approved_for_risk_check=approved,
            reason=f"Live Life local review approved the raw strategy setup: {signal.reason}" if approved else signal.reason,
            warnings=warnings,
            research_source_count=int((context or {}).get("research", {}).get("successful_sources", 0))
        )
