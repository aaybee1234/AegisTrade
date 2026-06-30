from dataclasses import asdict, dataclass, field
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
    strategy: str = "ema-rsi-breakout"
    indicators: dict[str, float] = field(default_factory=dict)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


def ema(values: list[float], period: int) -> float:
    if len(values) < period:
        return average(values)
    multiplier = 2 / (period + 1)
    result = average(values[:period])
    for value in values[period:]:
        result = (value - result) * multiplier + result
    return result


def rsi(values: list[float], period: int = 14) -> float:
    if len(values) < period + 1:
        return 50
    changes = [current - previous for previous, current in zip(values[-period - 1:-1], values[-period:])]
    gains = average([max(change, 0) for change in changes])
    losses = average([abs(min(change, 0)) for change in changes])
    if losses == 0:
        return 100
    relative_strength = gains / losses
    return 100 - (100 / (1 + relative_strength))


def calculate_atr_points(candles: list[dict[str, Any]], point: float, period: int = 14) -> int:
    if len(candles) < period + 1 or point <= 0:
        return 0
    ranges = []
    recent = candles[-period - 1:]
    for previous, candle in zip(recent[:-1], recent[1:]):
        high = float(candle.get("high", candle["close"]))
        low = float(candle.get("low", candle["close"]))
        previous_close = float(previous["close"])
        ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return int(average(ranges) / point)


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def hold_signal(symbol: str, reason: str, confidence: float = 0.2) -> TradeSignal:
    config = config_for_symbol(symbol)
    return TradeSignal(
        symbol=symbol,
        action="HOLD",
        confidence=confidence,
        lot_size=config.lot_size,
        stop_loss_pips=0,
        take_profit_pips=0,
        reason=reason
    )


def build_signal(symbol: str, candles: list[dict[str, Any]], symbol_info: dict[str, Any] | None = None) -> TradeSignal:
    config = config_for_symbol(symbol)
    completed = candles[:-1]
    if len(completed) < 60:
        return hold_signal(symbol, "Not enough completed candle history.", 0)

    point = float((symbol_info or {}).get("point", 0.00001))
    spread_points = int((symbol_info or {}).get("spread", 0))
    if spread_points > config.max_spread_points:
        return hold_signal(symbol, f"Spread is too high for {symbol}: {spread_points} points.")

    closes = [float(candle["close"]) for candle in completed]
    volumes = [float(candle.get("tick_volume", 0)) for candle in completed]
    fast_ema = ema(closes[-80:], 20)
    slow_ema = ema(closes[-100:], 50)
    previous_fast_ema = ema(closes[-81:-1], 20)
    momentum_rsi = rsi(closes, 14)
    last_close = closes[-1]
    breakout_high = max(float(candle.get("high", candle["close"])) for candle in completed[-7:-1])
    breakout_low = min(float(candle.get("low", candle["close"])) for candle in completed[-7:-1])
    average_volume = average(volumes[-21:-1])
    volume_ratio = volumes[-1] / average_volume if average_volume > 0 else 1

    atr_points = calculate_atr_points(completed, point)
    stop_points = clamp(
        int(max(atr_points * config.atr_multiplier, config.min_stop_points)),
        config.min_stop_points,
        config.max_stop_points
    )
    take_profit_points = int(stop_points * config.risk_reward)

    breakout_buy_checks = {
        "trend": fast_ema > slow_ema,
        "slope": fast_ema > previous_fast_ema,
        "momentum": 52 <= momentum_rsi <= 68,
        "breakout": last_close > breakout_high,
        "volume": volume_ratio >= 0.9
    }
    breakout_sell_checks = {
        "trend": fast_ema < slow_ema,
        "slope": fast_ema < previous_fast_ema,
        "momentum": 32 <= momentum_rsi <= 48,
        "breakout": last_close < breakout_low,
        "volume": volume_ratio >= 0.9
    }
    continuation_buy_checks = {
        "trend": fast_ema > slow_ema,
        "slope": fast_ema > previous_fast_ema,
        "momentum": 44 <= momentum_rsi <= 66,
        "above_slow": last_close > slow_ema,
        "volume": volume_ratio >= 0.55
    }
    continuation_sell_checks = {
        "trend": fast_ema < slow_ema,
        "slope": fast_ema < previous_fast_ema,
        "momentum": 34 <= momentum_rsi <= 56,
        "below_slow": last_close < slow_ema,
        "volume": volume_ratio >= 0.55
    }

    breakout_buy_score = sum(breakout_buy_checks.values())
    breakout_sell_score = sum(breakout_sell_checks.values())
    continuation_buy_score = sum(continuation_buy_checks.values())
    continuation_sell_score = sum(continuation_sell_checks.values())
    indicators = {
        "ema20": round(fast_ema, 8),
        "ema50": round(slow_ema, 8),
        "rsi14": round(momentum_rsi, 2),
        "atr_points": float(atr_points),
        "spread_points": float(spread_points),
        "volume_ratio": round(volume_ratio, 2),
        "breakout_buy_score": float(breakout_buy_score),
        "breakout_sell_score": float(breakout_sell_score),
        "continuation_buy_score": float(continuation_buy_score),
        "continuation_sell_score": float(continuation_sell_score)
    }

    action = "HOLD"
    score = max(breakout_buy_score, breakout_sell_score)
    strategy = "ema-rsi-breakout"
    if breakout_buy_score >= 4 and breakout_buy_score > breakout_sell_score:
        action = "BUY"
    elif breakout_sell_score >= 4 and breakout_sell_score > breakout_buy_score:
        action = "SELL"
    else:
        score = max(continuation_buy_score, continuation_sell_score)
        strategy = "ema-rsi-continuation"
        if continuation_buy_score >= 4 and continuation_buy_score > continuation_sell_score:
            action = "BUY"
        elif continuation_sell_score >= 4 and continuation_sell_score > continuation_buy_score:
            action = "SELL"

    if action == "HOLD":
        signal = hold_signal(
            symbol,
            (
                f"No aligned setup: breakout buy/sell {breakout_buy_score}/5/{breakout_sell_score}/5, "
                f"continuation buy/sell {continuation_buy_score}/5/{continuation_sell_score}/5."
            ),
            0.45
        )
        signal.indicators = indicators
        signal.strategy = "multi-setup-scan"
        return signal

    confidence = min(0.62 + score * 0.025, 0.75)
    return TradeSignal(
        symbol=symbol,
        action=action,
        confidence=confidence,
        lot_size=config.lot_size,
        stop_loss_pips=stop_points,
        take_profit_pips=take_profit_points,
        reason=(
            f"{action} {strategy} setup passed {score}/5 checks. EMA trend and slope align, RSI={momentum_rsi:.1f}, "
            f"volume={volume_ratio:.2f}x, ATR stop={stop_points}, target={take_profit_points}."
        ),
        strategy=strategy,
        indicators=indicators
    )
