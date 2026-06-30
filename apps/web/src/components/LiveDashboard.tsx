"use client";

import {
  Activity,
  AlertTriangle,
  Bot,
  CirclePause,
  PlugZap,
  RefreshCw,
  ShieldCheck,
  SlidersHorizontal,
  TrendingUp,
  WalletCards
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

type Account = {
  login?: string;
  server?: string;
  balance?: number;
  equity?: number;
  profit?: number;
  margin_free?: number;
  currency?: string;
  connected?: boolean;
  is_demo?: boolean;
  connection_error?: string;
};

type Position = {
  ticket: string;
  symbol: string;
  type: "BUY" | "SELL";
  volume: number;
  price_open: number;
  price_current: number;
  sl: number;
  tp: number;
  profit: number;
};

type DashboardModule = "main" | "live-life";

type Mt5Status = {
  account: Account;
  positions: Position[];
  summary: {
    open_positions: number;
    floating_pl: number;
  };
  daily: {
    opened: number;
    closed: number;
    wins: number;
    losses: number;
    win_rate: number;
    net_profit: number;
    remaining: number;
  };
  bot: {
    auto_trade_enabled: boolean;
    trading_environment?: string;
    trading_profile?: string;
    trading_portfolios?: string[];
    max_open_trades: number;
    max_daily_trades: number;
    max_risk_per_trade_usd: number;
    target_profit_per_trade_usd: number;
    max_daily_loss_usd: number;
    minimum_risk_reward: number;
    trade_cooldown_seconds: number;
    auto_scan_interval_seconds: number;
    news_refresh_seconds: number;
    ai_review_required: boolean;
    trading_symbols?: string[];
  };
};

type Setup = {
  symbol: string;
  rank_score: number;
  action: string;
  confidence: number;
  can_trade_now: boolean;
  veto_reasons: string[];
  explanation: string;
  warnings: string[];
  stop_loss_points: number;
  take_profit_points: number;
  portfolio?: string;
  strategy?: string;
  indicators?: Record<string, number>;
  news_risk?: string;
  news_summary?: string;
  research_source_count?: number;
  headlines?: Array<{ title?: string; source?: string; published_at?: string }>;
  crypto_trending?: Array<{ name?: string; symbol?: string; market_cap_rank?: number }>;
};

type AiActivity = {
  configured: boolean;
  configured_model?: string | null;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  skipped_reviews: number;
  updated_at?: string;
  last_call?: {
    status: string;
    symbol: string;
    latency_ms: number;
    request_id?: string | null;
    response_id?: string | null;
    response_model?: string | null;
    usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number };
    error?: string | null;
  } | null;
};
type Advisory = {
  setups: Setup[];
  environment?: string;
  portfolios?: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
const EMPTY_STATUS: Mt5Status = {
  account: { connected: false, is_demo: true, connection_error: "Waiting for first sync." },
  positions: [],
  summary: { open_positions: 0, floating_pl: 0 },
  daily: { opened: 0, closed: 0, wins: 0, losses: 0, win_rate: 0, net_profit: 0, remaining: 100 },
  bot: { auto_trade_enabled: false, max_open_trades: 1, max_daily_trades: 100, max_risk_per_trade_usd: 0.5, target_profit_per_trade_usd: 0.75, max_daily_loss_usd: 2, minimum_risk_reward: 1.5, trade_cooldown_seconds: 300, auto_scan_interval_seconds: 300, news_refresh_seconds: 900, ai_review_required: true }
};

const rules = [
  "Demo account required",
  "Configured simultaneous trade limit",
  "Skip duplicate symbol positions",
  "Cooldown after each bot entry",
  "Spread filter before entry",
  "Broker-calculated dollar risk before every order",
  "Daily loss kill switch",
  "AI review cannot bypass risk rules"
];

function money(value = 0, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2
  }).format(value);
}

function advisoryForPosition(position: Position) {
  if (position.profit > 0.5) {
    return "Profit is positive; consider tightening risk or watching for reversal.";
  }
  if (position.profit < -0.5) {
    return "Loss is building; respect SL and avoid adding to the position.";
  }
  return "Position is near flat; monitor spread, SL distance, and trend confirmation.";
}

async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return response.json();
}

export function LiveDashboard({ module = "main" }: { module?: DashboardModule }) {
  const [status, setStatus] = useState<Mt5Status>(EMPTY_STATUS);
  const [advisory, setAdvisory] = useState<Advisory>({ setups: [] });
  const [aiActivity, setAiActivity] = useState<AiActivity>({ configured: false, total_requests: 0, successful_requests: 0, failed_requests: 0, skipped_reviews: 0, last_call: null });
  const [lastSync, setLastSync] = useState<string>("Not synced yet");
  const [syncError, setSyncError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [closingTicket, setClosingTicket] = useState<string | null>(null);
  const [isRunningCycle, setIsRunningCycle] = useState(false);
  const [isChangingTrading, setIsChangingTrading] = useState(false);

  const account = status.account;
  const currency = account.currency ?? "USD";
  const connected = Boolean(account.connected);
  const isLiveLifeModule = module === "live-life";
  const visiblePortfolios = status.bot.trading_portfolios ?? advisory.portfolios ?? [];
  const moduleTitle = isLiveLifeModule ? "Live Life Lab" : "Aegis Demo Bot";
  const moduleEyebrow = isLiveLifeModule ? "OpenAI-free demo trading module" : "Live demo trading console";
  const setupTitle = isLiveLifeModule ? "Live Life Setups" : "Ranked Setups";
  const setupLabel = isLiveLifeModule ? "Local strategy scanner" : "Live AI advisory";

  const sync = useCallback(async () => {
    setIsSyncing(true);
    try {
      const [nextStatus, nextAdvisory, nextAiActivity] = await Promise.all([
        fetchJson<Mt5Status>("/mt5/status"),
        fetchJson<Advisory>("/mt5/advisory"),
        fetchJson<AiActivity>("/mt5/ai-activity")
      ]);
      setStatus(nextStatus);
      setAdvisory(nextAdvisory);
      setAiActivity(nextAiActivity);
      setLastSync(new Date().toLocaleTimeString());
      setSyncError(null);
    } catch (error) {
      setSyncError(error instanceof Error ? error.message : "Live sync failed");
    } finally {
      setIsSyncing(false);
    }
  }, []);

  useEffect(() => {
    void sync();
    const id = window.setInterval(() => {
      void sync();
    }, 3000);
    return () => window.clearInterval(id);
  }, [sync]);

  const sortedSetups = useMemo(() => {
    return [...advisory.setups].sort((a, b) => b.rank_score - a.rank_score);
  }, [advisory.setups]);

  async function closePosition(ticket: string) {
    setClosingTicket(ticket);
    try {
      await fetchJson(`/mt5/positions/${ticket}`, { method: "DELETE" });
    } catch (error) {
      setSyncError(error instanceof Error ? error.message : "Close request failed");
    } finally {
      setClosingTicket(null);
      await sync();
    }
  }

  function getControlToken() {
    let token = window.sessionStorage.getItem("aegis-control-token");
    if (!token) {
      token = window.prompt("Enter SINGLE_USER_CONTROL_TOKEN from C:\\AegisTrade\\.env") ?? "";
      if (token) window.sessionStorage.setItem("aegis-control-token", token);
    }
    return token;
  }

  async function setTradingEnabled(enabled: boolean) {
    const token = getControlToken();
    if (!token) return;

    setIsChangingTrading(true);
    try {
      await fetchJson("/mt5/control", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-aegis-control-token": token
        },
        body: JSON.stringify({ enabled })
      });
      setStatus((current) => ({
        ...current,
        bot: { ...current.bot, auto_trade_enabled: enabled }
      }));
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
    } catch (error) {
      window.sessionStorage.removeItem("aegis-control-token");
      setSyncError(error instanceof Error ? error.message : "Trading control failed");
    } finally {
      setIsChangingTrading(false);
      await sync();
    }
  }

  async function runAgentCycle() {
    const token = getControlToken();
    if (!token) return;

    setIsRunningCycle(true);
    try {
      await fetchJson("/mt5/cycle", {
        method: "POST",
        headers: { "content-type": "application/json", "x-aegis-control-token": token },
        body: JSON.stringify({ force_execute: true })
      });
    } catch (error) {
      window.sessionStorage.removeItem("aegis-control-token");
      setSyncError(error instanceof Error ? error.message : "Agent cycle failed");
    } finally {
      setIsRunningCycle(false);
      await sync();
    }
  }

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={24} />
          <span>AegisTrade</span>
        </div>
        <nav className="navList" aria-label="Main navigation">
          <a href="/" className={!isLiveLifeModule ? "active" : undefined}>Dashboard</a>
          <a href="/live-life" className={isLiveLifeModule ? "active" : undefined}>Live Life</a>
          <a>Signals</a>
          <a>Trades</a>
          <a>Journal</a>
          <a href="/guide">Guide</a>
          <a>Settings</a>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">{moduleEyebrow}</p>
            <h1>{moduleTitle}</h1>
          </div>
          <div className="actions">
            <button className="iconButton" aria-label="Open bot settings" title="Settings">
              <SlidersHorizontal size={18} />
            </button>
            <button className="secondary" onClick={() => void sync()} disabled={isSyncing}>
              <RefreshCw size={18} />
              {isSyncing ? "Syncing" : "Sync Now"}
            </button>
            <label className={connected ? "toggleControl" : "toggleControl disabled"}>
              <input
                type="checkbox"
                checked={status.bot.auto_trade_enabled}
                onChange={(event) => void setTradingEnabled(event.target.checked)}
                disabled={!connected || isChangingTrading}
              />
              <span className="toggleTrack"><span /></span>
              <strong>{isChangingTrading ? "Updating" : "Auto trading"}</strong>
            </label>
            <button className="primary" onClick={() => void runAgentCycle()} disabled={isRunningCycle || !connected}>
              <Bot size={18} />
              {isRunningCycle ? "Running" : "Force Test Cycle"}
            </button>
          </div>
        </header>

        <section className={connected ? "connectionBand connected" : "connectionBand"} aria-label="Connection status">
          <div className="connectionIcon">
            <PlugZap size={22} />
          </div>
          <div>
            <strong>{connected ? "Exness MT5 connected" : "Exness MT5 is not connected"}</strong>
            <span>
              {connected
                ? `${account.login} on ${account.server} - last sync ${lastSync}`
                : account.connection_error ?? syncError ?? "Open MT5 and check the worker connection."}
            </span>
          </div>
          <span className={connected ? "statusPill ok" : "statusPill warning"}>{connected ? "Live demo" : "Setup needed"}</span>
        </section>

        {syncError ? <div className="inlineNotice"><AlertTriangle size={16} />{syncError}</div> : null}

        <section className="metrics" aria-label="Account metrics">
          <div className="metric liveMetric">
            <span>Balance</span>
            <strong>{money(account.balance, currency)}</strong>
            <small>{account.is_demo ? "Demo account" : "Account type unknown"}</small>
          </div>
          <div className="metric liveMetric">
            <span>Equity</span>
            <strong>{money(account.equity, currency)}</strong>
            <small>Polls MT5 every 3 seconds</small>
          </div>
          <div className="metric liveMetric">
            <span>Floating P/L</span>
            <strong className={(status.summary.floating_pl ?? 0) >= 0 ? "positive" : "negative"}>{money(status.summary.floating_pl, currency)}</strong>
            <small>{status.summary.open_positions} open positions</small>
          </div>
          <div className="metric">
            <span>Bot status</span>
            <strong className={status.bot.auto_trade_enabled ? "positive" : "paused"}><CirclePause size={18} /> {status.bot.auto_trade_enabled ? "Automatic" : "Advisory"}</strong>
            <small>{status.bot.trading_profile === "live_life" ? "Live Life local profile" : "Guarded AI profile"} / {status.bot.max_open_trades} positions</small>
            <small>{money(status.bot.max_risk_per_trade_usd)} max estimated loss / {money(status.bot.target_profit_per_trade_usd)} target</small>
            <small>Environment: {status.bot.trading_environment ?? "main"}</small>
            <small>Portfolios: {visiblePortfolios.join(", ") || "custom symbols"}</small>
            <small>Scanning: {(status.bot.trading_symbols ?? []).join(", ") || "default symbols"}</small>
          </div>
          <div className="metric liveMetric">
            <span>Today</span>
            <strong>{status.daily.closed} / {status.bot.max_daily_trades}</strong>
            <small>{money(status.bot.max_daily_loss_usd)} daily loss lock</small>
          </div>
          <div className="metric liveMetric">
            <span>Measured win rate</span>
            <strong>{status.daily.win_rate.toFixed(1)}%</strong>
            <small>{status.daily.wins} wins / {status.daily.losses} losses, {money(status.daily.net_profit, currency)} net</small>
          </div>
        </section>

        <section className="contentGrid">
          <div className="panel signalsPanel">
            <div className="panelHeader">
              <div>
                <p className="sectionLabel">Exness positions</p>
                <h2>Open Trades</h2>
              </div>
              <Activity size={19} />
            </div>
            <div className="positionsTable">
              <div className="positionsHead">
                <span>Symbol</span>
                <span>Side</span>
                <span>Volume</span>
                <span>Open</span>
                <span>SL / TP</span>
                <span>P/L</span>
                <span>Advisory</span>
                <span>Action</span>
              </div>
              {status.positions.length === 0 ? (
                <div className="emptyState">No open Exness demo positions. Ranked setups continue updating live.</div>
              ) : (
                status.positions.map((position) => (
                  <div className="positionRow" key={position.ticket}>
                    <strong>{position.symbol}</strong>
                    <span className={position.type === "BUY" ? "buy" : "sell"}>{position.type}</span>
                    <span>{position.volume}</span>
                    <span>{position.price_open}</span>
                    <span>{position.sl} / {position.tp}</span>
                    <span className={position.profit >= 0 ? "positive" : "negative"}>{money(position.profit, currency)}</span>
                    <span className="advisoryText">{advisoryForPosition(position)}</span>
                    <button className="dangerButton" onClick={() => void closePosition(position.ticket)} disabled={closingTicket === position.ticket}>
                      {closingTicket === position.ticket ? "Closing" : "Close"}
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panelHeader">
              <div>
                <p className="sectionLabel">Guardrails</p>
                <h2>Risk Rules</h2>
              </div>
              <ShieldCheck size={19} />
            </div>
            <ul className="rules aiRules">
              <li>AI can veto trades.</li>
              <li>AI can explain trades.</li>
              <li>AI can rank setups.</li>
              <li>AI cannot bypass risk rules.</li>
            </ul>
            <ul className="rules">
              {rules.map((rule) => <li key={rule}>{rule}</li>)}
            </ul>
          </div>

          <div className="panel">
            <div className="panelHeader">
              <div>
                <p className="sectionLabel">{setupLabel}</p>
                <h2>{setupTitle}</h2>
              </div>
              <WalletCards size={19} />
            </div>
            <div className="signalList compact">
              {sortedSetups.length === 0 ? (
                <article className="signal">
                  <div className="signalMain">
                    <strong>No advisory data</strong>
                    <span>MT5 advisory is unavailable or still loading.</span>
                  </div>
                </article>
              ) : (
                sortedSetups.map((setup) => (
                  <article className="signal" key={setup.symbol}>
                    <div className="signalMain">
                      <strong>{setup.symbol} {setup.portfolio ? <small className="portfolioBadge">{setup.portfolio}</small> : null}</strong>
                      <span>{setup.explanation}</span>
                      <span>{isLiveLifeModule ? "Local review" : "News risk"}: {setup.news_risk ?? "UNKNOWN"} - {setup.news_summary ?? "No AI/news summary yet."}</span>
                      {setup.indicators ? <span>RSI {setup.indicators.rsi14 ?? "n/a"} / spread {setup.indicators.spread_points ?? "n/a"} / ATR {setup.indicators.atr_points ?? "n/a"}</span> : null}
                      {setup.headlines && setup.headlines.length > 0 ? <span>Research: {setup.headlines.map((headline) => headline.source).filter(Boolean).join(", ")}</span> : null}
                      {setup.veto_reasons.length > 0 ? <span>Veto: {setup.veto_reasons.join(" ")}</span> : null}
                    </div>
                    <div className="signalMeta">
                      <b className={setup.can_trade_now ? "buy" : "hold"}>{setup.action}</b>
                      <span>{setup.rank_score}</span>
                      <small>{setup.can_trade_now ? "Ranked setup" : "Vetoed"}</small>
                      <small>{setup.research_source_count ?? 0} sources</small>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>

          <div className="panel accentPanel">
            <div className="panelHeader">
              <div>
                <p className="sectionLabel">{isLiveLifeModule ? "Local layer" : "AI layer"}</p>
                <h2>{isLiveLifeModule ? "Live Life Review" : "Review Agent"}</h2>
              </div>
              <TrendingUp size={19} />
            </div>
            <p className="panelText">
              {isLiveLifeModule
                ? "Live Life bypasses OpenAI while testing demo execution. The deterministic scanner ranks setups, then hard-coded risk checks decide whether a demo order is allowed."
                : "The model reviews strategy signals and writes explanations. Hard-coded risk checks still decide whether a demo order is allowed. News and project research can only veto or reduce confidence; it cannot create trades."}
            </p>
            <ul className="rules">
              <li>Provider: {isLiveLifeModule ? "Local deterministic review" : "OpenAI Responses API"}</li>
              <li>Configured model: {isLiveLifeModule ? "Bypassed for this module" : aiActivity.configured_model ?? "Not configured"}</li>
              <li>Requests: {aiActivity.total_requests} total / {aiActivity.successful_requests} successful / {aiActivity.failed_requests} failed</li>
              <li>Last review: {isLiveLifeModule ? "Local Live Life review" : aiActivity.last_call ? `${aiActivity.last_call.status} for ${aiActivity.last_call.symbol} in ${aiActivity.last_call.latency_ms} ms` : "No request recorded"}</li>
              <li>Tokens: {isLiveLifeModule ? 0 : aiActivity.last_call?.usage?.total_tokens ?? 0}</li>
              <li>Request ID: {isLiveLifeModule ? "Not used" : aiActivity.last_call?.request_id ?? aiActivity.last_call?.response_id ?? "Unavailable"}</li>
            </ul>
            <div className="inlineNotice">
              <AlertTriangle size={16} />
              {aiActivity.last_call?.error ?? "AI telemetry is live. Model output remains advisory and cannot bypass risk rules."}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}
