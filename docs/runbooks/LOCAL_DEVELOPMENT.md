# Local Development Runbook

## Prerequisites

- Windows machine or Windows VPS
- Node.js 20+
- Python 3.14 currently tested on this machine
- MetaTrader 5 x64 installed and logged into the Exness MT5 demo account
- Exness demo MT5 credentials in `D:\AegisTrade\.env`
- Optional: Docker Desktop for Postgres/Redis

## Install

```powershell
cd D:\AegisTrade
npm install
```

Python worker dependency currently required for MT5:

```powershell
cd D:\AegisTrade\services\worker
python -m pip install -r requirements.txt
```

## Environment

Private file, not committed:

```text
D:\AegisTrade\.env
```

Required keys:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_REASONING_MODEL=gpt-4.1
EXNESS_DEMO_LOGIN=
EXNESS_DEMO_PASSWORD=
EXNESS_DEMO_SERVER=
```

## Run App

Recommended:

```powershell
cd D:\AegisTrade
npm run dev
```

Separate processes:

```powershell
npm run dev:api
npm run dev:web
```

Open:

```text
http://localhost:3000
http://localhost:3000/guide
```

## Verify

```powershell
npm run typecheck
npm run build
cd D:\AegisTrade\services\worker
python -m aegis_worker.status_json
python -m aegis_worker.advisory_json
```

## Database

Start Postgres/Redis:

```powershell
npm run db:up
```

Apply schema when `psql` is available and `DATABASE_URL` is set:

```powershell
npm run db:schema
```

Schema file:

```text
infra/db/001_initial_schema.sql
```

## Live Dashboard Flow

The dashboard is now a client-side live console. It polls:

```text
GET http://localhost:4000/mt5/status
GET http://localhost:4000/mt5/advisory
```

every few seconds, then updates account stats, P/L, open positions, and ranked setups in-place.

## Safety Note

`python -m aegis_worker.status_json` and `python -m aegis_worker.advisory_json` are read-only.

`python -m aegis_worker` can place demo trades if risk checks pass.
