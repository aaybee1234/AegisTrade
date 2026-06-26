# MVP Flow

## Agent Boundaries

- Market agent: produces a trade idea from indicators and optional AI review.
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

