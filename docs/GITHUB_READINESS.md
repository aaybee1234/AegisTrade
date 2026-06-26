# GitHub Readiness

## Current State

AegisTrade is ready to create an initial GitHub repository as an MVP/prototype codebase once secrets are kept out of git.

## Before First Push

Run:

```powershell
cd D:\AegisTrade
rg "OPENAI_KEY_PREFIX|YOUR_REAL_PASSWORD|YOUR_REAL_LOGIN" -n --glob "!.env" --glob "!node_modules/**" --glob "!.next/**"
npm run typecheck
npm run build
```

Do not commit:

```text
.env
node_modules/
apps/web/.next/
services/worker/__pycache__/
```

`.gitignore` already covers these generated/private files.

## Suggested First Commit

```powershell
git init
git add .
git status --short
git commit -m "Initial AegisTrade MVP"
git branch -M main
git remote add origin <your-new-repo-url>
git push -u origin main
```

## Repo Description

Demo-first AI-assisted trading automation and journaling platform for Exness MT5.

## MVP Completion Estimate

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

## Next Milestones

1. Persist advisory, signal, risk, order, and journal events to Postgres.
2. Add Start/Stop bot control backed by a worker scheduler.
3. Add auth and user account management.
4. Add settings UI for symbols, risk limits, and model mode.
5. Add subscription/trial screens after the core demo workflow is stable.
