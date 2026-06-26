# AegisTrade Team Progress Brief

## What We Are Building

AegisTrade is a demo-first AI-assisted trading automation platform for Exness MT5 demo accounts. The goal is to let users test automated trading ideas safely before any real-money support is considered.

The MVP connects a web dashboard to a backend API and a Python worker that talks to a locally running MetaTrader 5 terminal. The worker reads Exness demo account state, analyzes market candles, creates a trade signal, optionally reviews it with an AI model, validates it through deterministic risk rules, and then sends only approved demo orders to MT5.

This is intentionally not a live-money trading product yet. The MVP is a controlled demo execution and observability platform.

## Current Proof

We have proven the full execution path:

```text
Next.js Dashboard
  -> Express API
  -> Python Worker
  -> MetaTrader5 Python package
  -> MetaTrader 5 desktop terminal
  -> Exness MT5 demo account
```

Verified Exness demo account:

```text
Server: Exness-MT5Trial16
Account type: Demo
Balance source: MT5 account_info()
Symbols discovered: EURUSDm, BTCUSDm, XAUUSDm, and other Exness suffix symbols
```

Demo orders have been successfully placed through MT5:

- EURUSDm BUY 0.01 was accepted.
- BTCUSDm SELL 0.01 was accepted.
- BTC SL behavior was observed and explained.
- Invalid-stop rejections were used to improve stop sizing.

## Current Open-State Behavior

The worker now includes an MVP safety gate:

```text
MAX_OPEN_TRADES = 2
```

The worker behavior is:

- If two positions are open, do not place more trades.
- If a symbol already has an open position, skip that symbol.
- Reject live accounts.
- Reject symbols outside the allowlist.
- Reject signals without SL/TP.
- Reject low-confidence signals.

The latest worker status confirmed:

```text
Open positions: 2
Symbols: EURUSDm and BTCUSDm
No blind duplicate loop should occur while max open trades is reached.
```

## Agent Definitions

### 1. Market Data Agent

Implementation area:

```text
services/worker/aegis_worker/mt5/client.py
```

Responsibilities:

- Connect to local MT5 terminal.
- Login to Exness demo account using `.env` credentials.
- Read account balance, equity, margin, floating P/L.
- Fetch candles from MT5.
- Fetch symbol metadata such as point size, spread, digits, and stop level.
- Read open positions.

This is not an LLM agent. It is a tool/data boundary.

### 2. Strategy Agent

Implementation area:

```text
services/worker/aegis_worker/agents/market_agent.py
services/worker/aegis_worker/strategy_config.py
```

Responsibilities:

- Calculate simple trend state from recent candles.
- Use EMA-style short/long averages.
- Estimate ATR-style candle range.
- Apply symbol-specific stop/target sizing.
- Produce a structured signal:

```json
{
  "symbol": "BTCUSDm",
  "action": "SELL",
  "confidence": 0.68,
  "lot_size": 0.01,
  "stop_loss_pips": 22682,
  "take_profit_pips": 36291,
  "reason": "Short trend is below long trend..."
}
```

Current symbol-specific rules:

- EURUSDm: tighter spread and stop limits.
- XAUUSDm: wider gold stops and spread filtering.
- BTCUSDm: much wider crypto stops based on point size and volatility.

### 3. AI Review Agent

Implementation area:

```text
services/worker/aegis_worker/agents/ai_review_agent.py
```

Responsibilities:

- Review the strategy signal.
- Explain why the trade might be valid or risky.
- Return structured JSON.
- Fall back locally if the OpenAI API is unavailable or rate-limited.

Important boundary:

```text
The AI review agent cannot place trades.
The AI review agent cannot bypass risk rules.
```

Current model settings are loaded from private `.env`:

```text
OPENAI_MODEL=gpt-4.1-mini
OPENAI_REASONING_MODEL=gpt-4.1
```

### 4. Risk Manager Agent

Implementation area:

```text
services/worker/aegis_worker/risk/manager.py
```

Responsibilities:

- Enforce demo-only trading.
- Enforce symbol allowlist.
- Enforce max lot size.
- Enforce minimum confidence.
- Enforce SL/TP presence.
- Enforce AI handoff approval flag.

This is deterministic code, not an LLM. This is the main safety gate.

### 5. Execution Agent

Implementation area:

```text
services/worker/aegis_worker/mt5/client.py
```

Responsibilities:

- Select the symbol in MT5.
- Build an MT5 order request.
- Convert stop/target points into actual SL/TP prices.
- Send demo market orders through `mt5.order_send()`.
- Return retcode, ticket, comment, and accepted/rejected status.

### 6. Monitor / Status Agent

Implementation area:

```text
services/worker/aegis_worker/status_json.py
services/api/src/routes/mt5.ts
```

Responsibilities:

- Read account state.
- Read open positions.
- Return JSON to the API/dashboard.
- Keep the UI live without placing trades.

## Current App Capabilities

### Web Dashboard

Implementation area:

```text
apps/web/src/app/page.tsx
apps/web/src/app/styles.css
```

Current dashboard shows:

- Exness MT5 connection status.
- Account login/server.
- Balance and equity.
- Floating P/L.
- Number of open positions.
- Open position table with symbol, side, volume, open price, SL/TP, and P/L.
- Risk rules.
- Agent status notes.

### API

Implementation area:

```text
services/api/src/routes/mt5.ts
```

Current endpoints:

```text
GET /health
GET /mt5/status
GET /mt5/positions
GET /mt5/symbols
GET /mt5/accounts/:id/status
```

`/mt5/status` calls the Python read-only status module and returns live Exness account/position data.

### Worker

Implementation area:

```text
services/worker/aegis_worker
```

Current commands:

```powershell
cd D:\AegisTrade\services\worker
python -m aegis_worker.status_json
python -m aegis_worker
```

`status_json` is read-only.

`aegis_worker` may place demo trades only if safety checks pass.

## Important Lessons From Testing

### Exness Symbol Suffixes

Exness demo account symbols use suffixes:

```text
EURUSDm
BTCUSDm
XAUUSDm
```

Generic names like `EURUSD`, `BTCUSD`, and `XAUUSD` were not enough.

### BTC Stop Sizing

BTCUSDm has:

```text
point = 0.01
spread can be around 1000 points
```

The first BTC stop was too tight and failed with `Invalid stops`. The strategy now uses symbol-specific stop ranges and ATR-style sizing.

### XAU Spread Filter

XAUUSDm was rejected when spread was too high:

```text
Spread is too high for XAUUSDm: 260 points
```

This is expected and safer than trading through expensive spreads.

### OpenAI Rate Limits

The AI review agent can hit API rate limits. When that happens, it falls back locally and does not block the worker.

## What Is Not Built Yet

- Database persistence for signals/trades/journal.
- Start/stop bot button actually triggering the worker.
- Close-trade button from dashboard.
- Trade history from MT5 deals/orders.
- Daily loss limit enforcement from persisted history.
- User login/authentication.
- Broker account management UI.
- Real backtesting.
- Production scheduler or background service.
- Deployment packaging.

## Recommended Next Sprint

1. Add close-position function.
2. Add dashboard action to close a demo trade by ticket.
3. Add SQLite/Postgres persistence for signals, decisions, and results.
4. Add bot settings table/config:
   - allowed symbols
   - max open trades
   - max daily loss
   - max daily trades
   - min confidence
5. Add trade journal:
   - signal reason
   - AI review result
   - risk decision
   - MT5 retcode
   - final P/L after close
6. Add scheduler:
   - run every 1 or 5 minutes
   - never run overlapping bot cycles
7. Improve strategy:
   - true EMA instead of simple average
   - RSI filter
   - ATR from true range
   - session/time filters
   - symbol-specific spread windows

## Product Positioning

AegisTrade should be described as:

```text
A demo-first AI-assisted trading automation and journaling platform for Exness MT5.
```

Avoid describing it as:

```text
Guaranteed profit bot
AI money printer
Risk-free trading bot
```

The core value is controlled strategy testing, risk enforcement, AI explanations, and transparent journaling.

## Update: Position Close Path Added

The dashboard/API/worker now include a controlled close-position path:

```text
Dashboard Close button
  -> DELETE /mt5/positions/:ticket
  -> python -m aegis_worker.close_position_json <ticket>
  -> MT5 reverse market order for that position
```

This does not close positions automatically. It only closes when a user clicks the dashboard Close button for a visible demo position.


## Update: Live Advisory, Learning Guide, And Model Policy

New app behavior:

- Dashboard auto-refreshes every 10 seconds using a small client component.
- Open positions now show advisory text based on current floating P/L.
- Dashboard includes the explicit AI boundaries:
  - AI can veto trades.
  - AI can explain trades.
  - AI can rank setups.
  - AI cannot bypass risk rules.
- Added a `Guide` page for users to learn trading basics, risk terms, and how the AegisTrade decision flow works.

Model policy note:

- GPT-5.5 can be used as a stronger reasoning/review model if the OpenAI API account has access and billing enabled.
- ChatGPT subscription plans and OpenAI API billing should be treated as separate until verified in the user billing dashboard.
- A stronger model is not treated as a profit guarantee. It is used for vetoing, explaining, ranking, and journaling. Deterministic code remains the execution gate.


## Update: Live Dashboard Sync And Database Groundwork

The dashboard has been changed from a server-refresh model to a true client-side live console.

Live sync behavior:

```text
Browser dashboard
  -> polls Express API every few seconds
  -> Express API calls Python read-only worker modules
  -> Python reads MT5 account, positions, and setup advisory
  -> UI updates account stats, P/L, positions, and ranked setups in-place
```

Added database groundwork:

```text
infra/db/001_initial_schema.sql
```

The schema prepares for:

- users
- MT5 accounts
- bots
- bot settings
- trade signals
- trades
- trade journal
- bot events

Added docs:

```text
docs/runbooks/LOCAL_DEVELOPMENT.md
docs/GITHUB_READINESS.md
```

## Plan Completion Snapshot

Compared to the original handwritten plan, current completion is approximately:

```text
Core Exness demo MT5 execution:        80%
AI review/veto/explain/rank flow:      65%
Risk controls and safety gates:        55%
Live dashboard and trade visibility:   70%
User learning guide:                   45%
Database persistence:                  20%
Subscription/trial packaging:          10%
Production readiness:                  20%
Overall MVP:                           55-60%
```

Current AI rule implementation:

- AI can veto trades: partially implemented through advisory/risk rejection paths.
- AI can explain trades: implemented through AI review/fallback explanation fields.
- AI can rank setups: implemented through `aegis_worker.advisory_json` and `GET /mt5/advisory`.
- AI cannot bypass risk rules: implemented because execution only happens after deterministic `RiskManager.validate()`.

Main remaining gap: persistence and scheduler. The system can read, rank, and execute demo trades, but signal history, AI reviews, risk decisions, and trade outcomes are not yet written to Postgres.

## Update: Windows VPS Startup Scripts

Added a lightweight Windows VPS startup kit for the first low-cost deployment:

```text
deploy/windows/install.ps1
deploy/windows/start.ps1
deploy/windows/stop.ps1
deploy/windows/status.ps1
deploy/windows/test-mt5.ps1
deploy/windows/README.md
```

Recommended first VPS profile:

```text
2 vCPU
2 GB RAM
Windows Server
One MT5 terminal/account
Node API + Next.js dashboard on same VPS
```

This keeps startup cost low. Scale by adding RAM or separating dashboard/database later.

## Update: Fresh Windows VPS Bootstrap

Added a one-script bootstrap path for a new Windows VPS:

```text
deploy/windows/bootstrap.ps1
```

The bootstrap script can:

- download/install Git, Node.js, Python, and Exness MT5
- clone or update the AegisTrade GitHub repo
- prompt for OpenAI and Exness MT5 credentials
- create `.env`
- install npm and Python worker dependencies
- start the API and dashboard

It is designed for Windows Server 2016 where `winget` is usually unavailable. The README now includes a raw GitHub download command so the VPS does not need Git before the first run.

S3/CDN artifact support was also added through `-ArtifactBaseUrl`, using this file layout:

```text
node-v20.18.1-x64.msi
Git-2.51.0-64-bit.exe
python-3.12.8-amd64.exe
exness5setup.exe
```

AWS CLI credentials are not required on the VPS if installer artifacts are public or pre-signed HTTPS URLs. Credentials are only needed if we later automate S3 bucket creation/upload.

Known limitation:

- MT5 installation can be started by script, but MT5 may still require one manual GUI login/confirmation on the VPS before the Python worker can connect reliably.
