from dataclasses import asdict, dataclass
from typing import Any

from aegis_worker.strategy_config import config_for_symbol


@dataclass
class TradeSignal:
    symbol: str
    action: str
    confidence: float
    lot_size: float
    stop_loss_pips: int
    take_profit_pips: int
    reason: str
    entry_type: str = "MARKET"

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


def average(values: list[float]) -> float:
    return sum(values) / len(values)


def calculate_atr_points(candles: list[dict[str, Any]], point: float, period: int = 14) -> int:
    if len(candles) < period + 1 or point <= 0:
        return 0

    ranges: list[float] = []
    recent = candles[-period:]
    for candle in recent:
        high = float(candle.get("high", candle["close"]))
        low = float(candle.get("low", candle["close"]))
        ranges.append(max(high - low, 0))

    return int(average(ranges) / point)


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def build_signal(symbol: str, candles: list[dict[str, Any]], symbol_info: dict[str, Any] | None = None) -> TradeSignal:
    config = config_for_symbol(symbol)
    if len(candles) < 50:
        return TradeSignal(
            symbol=symbol,
            action="HOLD",
            confidence=0,
            lot_size=config.lot_size,
            stop_loss_pips=0,
            take_profit_pips=0,
            reason="Not enough candle history."
        )

    point = float((symbol_info or {}).get("point", 0.00001))
    spread_points = int((symbol_info or {}).get("spread", 0))
    atr_points = calculate_atr_points(candles, point)
    stop_points = clamp(
        int(max(atr_points * config.atr_multiplier, config.min_stop_points)),
        config.min_stop_points,
        config.max_stop_points
    )
    take_profit_points = int(stop_points * config.risk_reward)

    if spread_points > config.max_spread_points:
        return TradeSignal(
            symbol=symbol,
            action="HOLD",
            confidence=0.2,
            lot_size=config.lot_size,
            stop_loss_pips=0,
            take_profit_pips=0,
            reason=f"Spread is too high for {symbol}: {spread_points} points."
        )

    closes = [float(candle["close"]) for candle in candles]
    ema20 = average(closes[-20:])
    ema50 = average(closes[-50:])
    last_close = closes[-1]

    if ema20 > ema50 and last_close > ema20:
        return TradeSignal(
            symbol=symbol,
            action="BUY",
            confidence=0.68,
            lot_size=config.lot_size,
            stop_loss_pips=stop_points,
            take_profit_pips=take_profit_points,
            reason=(
                f"Short trend is above long trend. ATR stop={stop_points} points, "
                f"target={take_profit_points} points, spread={spread_points}."
            )
        )

    if ema20 < ema50 and last_close < ema20:
        return TradeSignal(
            symbol=symbol,
            action="SELL",
            confidence=0.68,
            lot_size=config.lot_size,
            stop_loss_pips=stop_points,
            take_profit_pips=take_profit_points,
            reason=(
                f"Short trend is below long trend. ATR stop={stop_points} points, "
                f"target={take_profit_points} points, spread={spread_points}."
            )
        )

    return TradeSignal(
        symbol=symbol,
        action="HOLD",
        confidence=0.45,
        lot_size=config.lot_size,
        stop_loss_pips=0,
        take_profit_pips=0,
        reason="Trend conditions are mixed."
    )
