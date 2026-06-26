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

type Mt5Status = {
  account: Account;
  positions: Position[];
  summary: {
    open_positions: number;
    floating_pl: number;
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
};

type Advisory = {
  setups: Setup[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";
const EMPTY_STATUS: Mt5Status = {
  account: { connected: false, is_demo: true, connection_error: "Waiting for first sync." },
  positions: [],
  summary: { open_positions: 0, floating_pl: 0 }
};

const rules = [
  "Demo account required",
  "Maximum 2 open trades in MVP",
  "Skip duplicate symbol positions",
  "Spread filter before entry",
  "Symbol-specific ATR-style stops",
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

export function LiveDashboard() {
  const [status, setStatus] = useState<Mt5Status>(EMPTY_STATUS);
  const [advisory, setAdvisory] = useState<Advisory>({ setups: [] });
  const [lastSync, setLastSync] = useState<string>("Not synced yet");
  const [syncError, setSyncError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [closingTicket, setClosingTicket] = useState<string | null>(null);

  const account = status.account;
  const currency = account.currency ?? "USD";
  const connected = Boolean(account.connected);

  const sync = useCallback(async () => {
    setIsSyncing(true);
    try {
      const [nextStatus, nextAdvisory] = await Promise.all([
        fetchJson<Mt5Status>("/mt5/status"),
        fetchJson<Advisory>("/mt5/advisory")
      ]);
      setStatus(nextStatus);
      setAdvisory(nextAdvisory);
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

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={24} />
          <span>AegisTrade</span>
        </div>
        <nav className="navList" aria-label="Main navigation">
          <a className="active">Dashboard</a>
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
            <p className="eyebrow">Live demo trading console</p>
            <h1>Aegis Demo Bot</h1>
          </div>
          <div className="actions">
            <button className="iconButton" aria-label="Open bot settings" title="Settings">
              <SlidersHorizontal size={18} />
            </button>
            <button className="secondary" onClick={() => void sync()} disabled={isSyncing}>
              <RefreshCw size={18} />
              {isSyncing ? "Syncing" : "Sync Now"}
            </button>
            <button className="primary">
              <Bot size={18} />
              Start Bot
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
            <strong className="paused"><CirclePause size={18} /> Paused</strong>
            <small>Safety gate active</small>
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
                <p className="sectionLabel">Live AI advisory</p>
                <h2>Ranked Setups</h2>
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
                      <strong>{setup.symbol}</strong>
                      <span>{setup.explanation}</span>
                      {setup.veto_reasons.length > 0 ? <span>Veto: {setup.veto_reasons.join(" ")}</span> : null}
                    </div>
                    <div className="signalMeta">
                      <b className={setup.can_trade_now ? "buy" : "hold"}>{setup.action}</b>
                      <span>{setup.rank_score}</span>
                      <small>{setup.can_trade_now ? "Ranked setup" : "Vetoed"}</small>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>

          <div className="panel accentPanel">
            <div className="panelHeader">
              <div>
                <p className="sectionLabel">AI layer</p>
                <h2>Review Agent</h2>
              </div>
              <TrendingUp size={19} />
            </div>
            <p className="panelText">
              The model reviews strategy signals and writes explanations. Hard-coded risk checks still decide whether a demo order is allowed.
            </p>
            <div className="inlineNotice">
              <AlertTriangle size={16} />
              This page is live: account, positions, P/L, and setup ranking sync from MT5 through the API.
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}
