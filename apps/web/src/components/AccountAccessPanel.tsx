"use client";

import { KeyRound, Link2, LogIn, UserPlus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type User = { id: string; email: string };
type Mt5Account = {
  id: string;
  label: string;
  login: string;
  server: string;
  accountType: "demo" | "live";
  status: string;
};

async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error ?? `${path} returned ${response.status}`);
  }
  return response.json();
}

export function AccountAccessPanel() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [accounts, setAccounts] = useState<Mt5Account[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("aegistrade_token");
    if (!savedToken) return;
    setToken(savedToken);
    void apiJson<{ user: User }>("/auth/me", { headers: { Authorization: `Bearer ${savedToken}` } })
      .then((result) => setUser(result.user))
      .catch(() => window.localStorage.removeItem("aegistrade_token"));
  }, []);

  useEffect(() => {
    if (!token) return;
    void apiJson<{ accounts: Mt5Account[] }>("/accounts", { headers: { Authorization: `Bearer ${token}` } })
      .then((result) => setAccounts(result.accounts))
      .catch((error) => setMessage(error instanceof Error ? error.message : "Could not load accounts."));
  }, [token]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await apiJson<{ token: string; user: User }>(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") })
      });
      window.localStorage.setItem("aegistrade_token", result.token);
      setToken(result.token);
      setUser(result.user);
      setMessage("Signed in. You can connect an Exness MT5 account now.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Authentication failed.");
    }
  }

  async function submitAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const form = new FormData(event.currentTarget);
    try {
      const result = await apiJson<{ account: Mt5Account }>("/accounts", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          label: form.get("label"),
          login: form.get("login"),
          password: form.get("password"),
          server: form.get("server"),
          accountType: form.get("accountType")
        })
      });
      setAccounts((current) => [result.account, ...current.filter((account) => account.id !== result.account.id)]);
      setMessage("MT5 account profile saved. Worker allocation is the next step for true multi-user execution.");
      event.currentTarget.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save MT5 account.");
    }
  }

  return (
    <section className="accountAccess">
      <div className="panelHeader">
        <div>
          <p className="sectionLabel">Multi-user access</p>
          <h2>{user ? `Signed in as ${user.email}` : "Login or create account"}</h2>
        </div>
        <KeyRound size={19} />
      </div>

      {!user ? (
        <form className="accessForm" onSubmit={(event) => void submitAuth(event)}>
          <input name="email" type="email" placeholder="Email" required />
          <input name="password" type="password" placeholder="Password" minLength={8} required />
          <div className="segmentedActions">
            <button className={mode === "login" ? "primary" : "secondary"} type="submit" onClick={() => setMode("login")}><LogIn size={16} />Login</button>
            <button className={mode === "register" ? "primary" : "secondary"} type="submit" onClick={() => setMode("register")}><UserPlus size={16} />Register</button>
          </div>
        </form>
      ) : (
        <div className="accountGrid">
          <form className="accessForm" onSubmit={(event) => void submitAccount(event)}>
            <input name="label" placeholder="Account label" defaultValue="Exness demo" required />
            <input name="login" placeholder="MT5 login" required />
            <input name="password" type="password" placeholder="MT5 password" required />
            <input name="server" placeholder="Server, e.g. Exness-MT5Trial16" required />
            <select name="accountType" defaultValue="demo">
              <option value="demo">Demo</option>
              <option value="live">Live - disabled until compliance review</option>
            </select>
            <button className="primary" type="submit"><Link2 size={16} />Save MT5 Account</button>
          </form>
          <div className="accountList">
            {accounts.length === 0 ? <span>No saved MT5 accounts yet.</span> : accounts.map((account) => (
              <div key={account.id}>
                <strong>{account.label}</strong>
                <span>{account.login} on {account.server}</span>
                <small>{account.accountType} / {account.status}</small>
              </div>
            ))}
          </div>
        </div>
      )}
      {message ? <div className="inlineNotice">{message}</div> : null}
    </section>
  );
}
