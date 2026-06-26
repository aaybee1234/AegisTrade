CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mt5_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  login TEXT NOT NULL,
  server TEXT NOT NULL,
  account_type TEXT NOT NULL DEFAULT 'demo',
  encrypted_password TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(login, server)
);

CREATE TABLE IF NOT EXISTS bots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  mt5_account_id UUID REFERENCES mt5_accounts(id),
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'paused',
  mode TEXT NOT NULL DEFAULT 'demo',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bot_settings (
  bot_id UUID PRIMARY KEY REFERENCES bots(id),
  symbols TEXT[] NOT NULL DEFAULT ARRAY['EURUSDm','BTCUSDm','XAUUSDm'],
  lot_size NUMERIC(12, 4) NOT NULL DEFAULT 0.01,
  max_open_trades INTEGER NOT NULL DEFAULT 2,
  max_trades_per_day INTEGER NOT NULL DEFAULT 5,
  daily_loss_limit NUMERIC(12, 2) NOT NULL DEFAULT 25,
  min_confidence NUMERIC(4, 2) NOT NULL DEFAULT 0.65,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trade_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bot_id UUID REFERENCES bots(id),
  symbol TEXT NOT NULL,
  action TEXT NOT NULL,
  confidence NUMERIC(4, 2) NOT NULL,
  rank_score NUMERIC(8, 2),
  reason TEXT NOT NULL,
  ai_review JSONB,
  risk_decision JSONB,
  approved BOOLEAN NOT NULL DEFAULT false,
  rejection_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bot_id UUID REFERENCES bots(id),
  signal_id UUID REFERENCES trade_signals(id),
  mt5_ticket TEXT UNIQUE,
  symbol TEXT NOT NULL,
  action TEXT NOT NULL,
  lot_size NUMERIC(12, 4) NOT NULL,
  entry_price NUMERIC(18, 6),
  stop_loss NUMERIC(18, 6),
  take_profit NUMERIC(18, 6),
  status TEXT NOT NULL DEFAULT 'open',
  profit NUMERIC(12, 2) NOT NULL DEFAULT 0,
  opened_at TIMESTAMPTZ,
  closed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trade_journal (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trade_id UUID REFERENCES trades(id),
  summary TEXT NOT NULL,
  lesson TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bot_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bot_id UUID REFERENCES bots(id),
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trade_signals_bot_created ON trade_signals(bot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_bot_status ON trades(bot_id, status);
CREATE INDEX IF NOT EXISTS idx_bot_events_bot_created ON bot_events(bot_id, created_at DESC);
