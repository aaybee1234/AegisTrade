# MVP Flow

## Agent Boundaries

- Market agent: produces a trade candidate from deterministic indicators only.
- Research context: gathers official macro/energy feeds and crypto discovery data; it cannot create a trade.
- AI review agent: explains, ranks, lowers confidence, or vetoes the existing candidate.
- Risk manager: deterministic approval gate.
- Execution agent: only component allowed to call MT5 order APIs.
- Monitor agent: watches open trades and account limits.
- Journal agent: writes human-readable summaries.

## First Strategy

Buy candidate:

```text
EMA20 > EMA50
RSI between 45 and 70
price above EMA20
spread below limit
```

Sell candidate:

```text
EMA20 < EMA50
RSI between 30 and 55
price below EMA20
spread below limit
```

Hold:

```text
Anything else
```

## Execution Order

```text
completed candles -> deterministic setup -> research context -> AI veto/review -> hard risk gate -> MT5 demo execution
```

The flow fails closed when required AI review or research coverage is unavailable. AI never changes symbol, side, lot size, stop loss, or take profit.
