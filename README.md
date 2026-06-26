# AegisTrade

AegisTrade is a demo-first, agentic trading bot platform for Exness MT5 demo accounts. The product goal is to let users test automated trading ideas safely with strict risk controls, clear trade explanations, and a journal of every decision.

This is not a real-money trading bot in the MVP. The first version must only connect to demo accounts and must reject live accounts.

## Product Shape

```text
Web Dashboard
  -> API Service
  -> Bot Orchestrator
  -> Market Agent
  -> Risk Manager
  -> MT5 Demo Executor
  -> Monitor + Journal
```

The main rule is simple:

```text
AI can suggest.
Code must approve.
Only the executor can place demo trades.
```

## MVP Features

- User can configure a demo bot profile.
- User can add Exness MT5 demo credentials.
- Worker can connect to MT5 and read account state.
- Worker can fetch candles for allowed symbols.
- Strategy creates a structured trade candidate.
- Agent explains or refines the candidate as JSON.
- Risk manager approves or rejects the candidate using hard rules.
- Executor places approved demo trades only.
- Dashboard shows balance, open trades, signals, rejections, and journal entries.

## Guardrails

- Demo accounts only.
- Fixed lot size for v1.
- Mandatory stop loss and take profit.
- No martingale.
- No averaging down.
- No unlimited retries.
- No trade if spread is too high.
- No trade if daily loss limit is reached.
- No real account support in MVP.

## Monorepo Layout

```text
AegisTrade/
  apps/web/                 Next.js dashboard
  services/api/             Express API for bots, accounts, trades
  services/worker/          Python MT5 worker and agentic flow
  packages/shared/          Shared TypeScript contracts
  infra/                    Local Postgres/Redis compose files
  docs/                     Product and technical notes
```

## Core Trading Flow

1. Bot wakes on an interval.
2. Worker confirms the MT5 account is demo.
3. Worker fetches candles for each allowed symbol.
4. Strategy calculates EMA, RSI, ATR, spread, and trend state.
5. Market agent returns a structured signal: buy, sell, or hold.
6. Risk manager validates the signal against deterministic rules.
7. Executor sends approved demo orders to MT5.
8. API stores signal, trade, rejection, and journal records.
9. Monitor watches open positions and records outcomes.

## Suggested Tech Stack

- Web: Next.js, React, TypeScript
- API: Node.js, Express, TypeScript
- Worker: Python, MetaTrader5 package, pandas
- Database: PostgreSQL
- Queue/cache: Redis
- AI: OpenAI structured JSON responses for explanation and review
- Runtime: Windows VPS for MT5 terminal and Python worker

## Database Model

Initial tables:

- `users`
- `mt5_accounts`
- `bots`
- `bot_settings`
- `trade_signals`
- `trades`
- `trade_journal`

## API Surface

```text
GET  /health

POST /auth/register
POST /auth/login

POST /mt5/accounts
GET  /mt5/accounts/:id/status
GET  /mt5/symbols

POST /bots
GET  /bots
GET  /bots/:id
PATCH /bots/:id/settings
POST /bots/:id/start
POST /bots/:id/stop

GET  /bots/:id/signals
GET  /bots/:id/trades
GET  /bots/:id/journal
```

## Worker Decision Contract

```json
{
  "symbol": "XAUUSD",
  "action": "BUY",
  "confidence": 0.72,
  "lot_size": 0.01,
  "entry_type": "MARKET",
  "stop_loss_pips": 200,
  "take_profit_pips": 400,
  "reason": "EMA20 is above EMA50 and RSI remains in a healthy trend range."
}
```

## Risk Checks

Before any order:

- Bot is enabled.
- Account is demo.
- Symbol is allowed.
- Market is open.
- Lot size is within settings.
- Open trades are below limit.
- Trades today are below limit.
- Daily loss is below limit.
- Stop loss exists.
- Take profit exists.
- Confidence is above threshold.
- Spread is below max allowed.

## Build Milestones

1. Scaffold web, API, worker, shared contracts, and README.
2. Add local Postgres/Redis and database migrations.
3. Implement MT5 connection probe from Python.
4. Fetch account info, symbols, ticks, and candles.
5. Implement indicator strategy.
6. Implement deterministic risk manager.
7. Implement demo order placement.
8. Add API persistence for signals/trades/journal.
9. Connect dashboard to API.
10. Add OpenAI-powered explanation/review agent.
11. Run paper/demo test cycle and tune settings.

## Local Development

Install dependencies from the project root:

```bash
npm install
```

Start infrastructure:

```bash
docker compose -f infra/docker-compose.yml up -d
```

Start the API:

```bash
npm run dev:api
```

Start the web app:

```bash
npm run dev:web
```

Run the Python worker after installing its requirements:

```bash
cd services/worker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m aegis_worker
```


## Implemented Agent Files

- `services/worker/aegis_worker/agents/market_agent.py`: indicator-based signal candidate.
- `services/worker/aegis_worker/agents/ai_review_agent.py`: optional OpenAI Responses API review agent with local fallback.
- `services/worker/aegis_worker/risk/manager.py`: deterministic approval gate with AI handoff validation.
- `services/worker/aegis_worker/mt5/client.py`: placeholder MT5 boundary for demo account integration.

If `OPENAI_API_KEY` is not set, the AI review agent returns a local fallback review so the worker can still run in demo scaffolding mode.


## Current Progress Note

For the latest team-facing architecture/progress summary, read:

```text
docs/TEAM_PROGRESS.md
```

Current MVP proof completed:

- Exness MT5 demo connection works through the local MT5 terminal.
- Demo orders have been placed successfully for EURUSDm and BTCUSDm.
- Dashboard reads live MT5 account and open-position data through the API.
- Worker has max-open-trade and duplicate-symbol safety gates.
- Strategy now uses symbol-specific spread filters and ATR-style stop/target sizing.


## Live Dashboard Update

The dashboard now uses a client-side live data flow instead of static server refresh. It polls the API every few seconds:

```text
GET /mt5/status
GET /mt5/advisory
```

This updates account balance, equity, floating P/L, open positions, and AI-ranked setups in-place.

## Database Groundwork

Initial Postgres schema is available at:

```text
infra/db/001_initial_schema.sql
```

It includes tables for users, MT5 accounts, bots, bot settings, trade signals, trades, trade journal entries, and bot events.

## Useful Commands

```powershell
npm run dev          # run API and web together
npm run dev:api      # run API only
npm run dev:web      # run dashboard only
npm run typecheck    # TypeScript checks
npm run build        # production build
npm run verify       # typecheck + build
npm run db:up        # start Postgres/Redis via Docker
npm run db:schema    # apply initial DB schema with psql
```

More setup detail:

```text
docs/runbooks/LOCAL_DEVELOPMENT.md
docs/GITHUB_READINESS.md
```
