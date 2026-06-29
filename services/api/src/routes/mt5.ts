import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { Router } from "express";

const execFileAsync = promisify(execFile);
export const mt5Router = Router();

const routeDir = path.dirname(fileURLToPath(import.meta.url));
const apiRoot = path.resolve(routeDir, "..", "..");
const projectRoot = path.resolve(apiRoot, "..", "..");
const workerCwd = path.join(projectRoot, "services", "worker");

const defaultAccountId = process.env.SINGLE_USER_ACCOUNT_ID ?? "primary";
type LogStream = "app" | "trade" | "ai";
const logStreams = new Set<LogStream>(["app", "trade", "ai"]);

function accountLogsDir(accountId = defaultAccountId) {
  return path.join(accountRuntimeDir(accountId), "logs");
}

function parseLimit(value: unknown) {
  const parsed = Number(value ?? 100);
  if (!Number.isFinite(parsed)) return 100;
  return Math.max(1, Math.min(500, Math.trunc(parsed)));
}

async function appendApiLog(event: Record<string, unknown>, accountId = defaultAccountId) {
  const logsDir = accountLogsDir(accountId);
  await mkdir(logsDir, { recursive: true });
  const payload = { ts: new Date().toISOString(), stream: "app", source: "api", ...event };
  await appendFile(path.join(logsDir, "app.jsonl"), JSON.stringify(payload) + "\n", "utf8");
}

async function readLogStream(stream: LogStream, limit: number, accountId = defaultAccountId) {
  const content = await readFile(path.join(accountLogsDir(accountId), `${stream}.jsonl`), "utf8");
  return content
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(-limit)
    .map((line) => JSON.parse(line));
}


function safeAccountId(value: string) {
  if (!/^[a-zA-Z0-9_-]+$/.test(value)) {
    throw new Error("Invalid account id");
  }
  return value;
}

function accountRuntimeDir(accountId = defaultAccountId) {
  return path.join(projectRoot, "runtime", "accounts", safeAccountId(accountId));
}

async function readRuntimeJson<T>(name: string, accountId = defaultAccountId): Promise<T> {
  const content = await readFile(path.join(accountRuntimeDir(accountId), name), "utf8");
  return JSON.parse(content) as T;
}

async function queueCommand(command: Record<string, unknown>, accountId = defaultAccountId) {
  const id = randomUUID();
  const commandsDir = path.join(accountRuntimeDir(accountId), "commands");
  await mkdir(commandsDir, { recursive: true });
  await writeFile(path.join(commandsDir, `${id}.json`), JSON.stringify(command), "utf8");
  return id;
}

async function runWorkerJson(moduleName: string, args: string[] = []) {
  const { stdout } = await execFileAsync("python", ["-m", moduleName, ...args], {
    cwd: workerCwd,
    timeout: 45_000,
    windowsHide: true
  });
  return JSON.parse(stdout);
}

async function statusWithDevelopmentFallback() {
  try {
    return await readRuntimeJson<any>("status.json");
  } catch (runtimeError) {
    if (process.env.NODE_ENV === "development") {
      return runWorkerJson("aegis_worker.status_json");
    }
    throw runtimeError;
  }
}

mt5Router.post("/control", async (req, res) => {
  const expectedToken = process.env.SINGLE_USER_CONTROL_TOKEN;
  const suppliedToken = req.header("x-aegis-control-token");
  if (!expectedToken) {
    res.status(503).json({ error: "Single-user control endpoint is disabled." });
    return;
  }
  if (suppliedToken !== expectedToken) {
    res.status(401).json({ error: "Invalid control token." });
    return;
  }
  if (typeof req.body?.enabled !== "boolean") {
    res.status(400).json({ error: "enabled must be a boolean." });
    return;
  }

  try {
    const commandId = await queueCommand({ type: "set_auto_trade", enabled: req.body.enabled });
    await appendApiLog({ event: "control_queued", command_id: commandId, auto_trade_enabled: req.body.enabled });
    res.status(202).json({
      ok: true,
      queued: true,
      auto_trade_enabled: req.body.enabled,
      command_id: commandId
    });
  } catch (error) {
    res.status(503).json({ ok: false, error: error instanceof Error ? error.message : "Trading control unavailable" });
  }
});
mt5Router.post("/cycle", async (req, res) => {
  const expectedToken = process.env.SINGLE_USER_CONTROL_TOKEN;
  const suppliedToken = req.header("x-aegis-control-token");
  if (!expectedToken) {
    res.status(503).json({ error: "Single-user control endpoint is disabled." });
    return;
  }
  if (suppliedToken !== expectedToken) {
    res.status(401).json({ error: "Invalid control token." });
    return;
  }

  try {
    const forceExecute = req.body?.force_execute === true;
    const commandId = await queueCommand({ type: "run_cycle", force_execute: forceExecute });
    await appendApiLog({ event: "cycle_queued", command_id: commandId, forced_test_cycle: forceExecute });
    res.status(202).json({ ok: true, queued: true, command_id: commandId, forced_test_cycle: forceExecute });
  } catch (error) {
    res.status(503).json({ ok: false, error: error instanceof Error ? error.message : "Trading cycle unavailable" });
  }
});

mt5Router.get("/symbols", (_req, res) => {
  res.json({ symbols: ["XAUUSDm", "EURUSDm", "GBPUSDm", "USDJPYm", "BTCUSDm"] });
});

mt5Router.get("/status", async (_req, res) => {
  try {
    res.json(await statusWithDevelopmentFallback());
  } catch (error) {
    res.status(503).json({
      account: {
        connected: false,
        is_demo: true,
        connection_error: "Interactive MT5 worker snapshot is unavailable."
      },
      positions: [],
      summary: { open_positions: 0, floating_pl: 0 },
      error: error instanceof Error ? error.message : "MT5 status unavailable"
    });
  }
});

mt5Router.get("/positions", async (_req, res) => {
  try {
    const status = await statusWithDevelopmentFallback();
    res.json({ positions: status.positions, summary: status.summary });
  } catch (error) {
    res.status(503).json({
      positions: [],
      summary: { open_positions: 0, floating_pl: 0 },
      error: error instanceof Error ? error.message : "MT5 positions unavailable"
    });
  }
});

mt5Router.get("/advisory", async (_req, res) => {
  try {
    res.json(await readRuntimeJson("advisory.json"));
  } catch (error) {
    if (process.env.NODE_ENV === "development") {
      try {
        res.json(await runWorkerJson("aegis_worker.advisory_json"));
        return;
      } catch {
        // Use the standard unavailable response below.
      }
    }
    res.status(503).json({ setups: [], error: error instanceof Error ? error.message : "MT5 advisory unavailable" });
  }
});


mt5Router.get("/logs", async (req, res) => {
  const limit = parseLimit(req.query.limit);
  const requested = typeof req.query.stream === "string" ? req.query.stream : "all";
  try {
    if (requested !== "all") {
      if (!logStreams.has(requested as LogStream)) {
        res.status(400).json({ error: "stream must be app, trade, ai, or all" });
        return;
      }
      const entries = await readLogStream(requested as LogStream, limit);
      res.json({ stream: requested, entries });
      return;
    }

    const groups = await Promise.allSettled([
      readLogStream("app", limit),
      readLogStream("trade", limit),
      readLogStream("ai", limit)
    ]);
    const entries = groups
      .flatMap((group) => group.status === "fulfilled" ? group.value : [])
      .sort((a, b) => String(a.ts).localeCompare(String(b.ts)))
      .slice(-limit);
    res.json({ stream: "all", entries });
  } catch (error) {
    res.status(503).json({ entries: [], error: error instanceof Error ? error.message : "Logs unavailable" });
  }
});

mt5Router.get("/ai-activity", async (_req, res) => {
  try {
    res.json(await readRuntimeJson("ai_activity.json"));
  } catch (error) {
    res.status(503).json({
      configured: Boolean(process.env.OPENAI_API_KEY),
      configured_model: process.env.OPENAI_MODEL ?? null,
      total_requests: 0,
      successful_requests: 0,
      failed_requests: 0,
      skipped_reviews: 0,
      last_call: null,
      error: error instanceof Error ? error.message : "AI activity unavailable"
    });
  }
});
mt5Router.get("/accounts/:id/status", async (req, res) => {
  try {
    const status = await readRuntimeJson<any>("status.json", req.params.id);
    res.json({ id: req.params.id, ...status.account, bridge: status.bridge });
  } catch (error) {
    res.status(503).json({
      id: req.params.id,
      connected: false,
      accountType: "demo",
      message: error instanceof Error ? error.message : "MT5 worker unavailable"
    });
  }
});

mt5Router.delete("/positions/:ticket", async (req, res) => {
  try {
    const commandId = await queueCommand({ type: "close_position", ticket: req.params.ticket });
    await appendApiLog({ event: "close_position_queued", command_id: commandId, ticket: req.params.ticket });
    res.status(202).json({ closed: false, queued: true, ticket: req.params.ticket, command_id: commandId });
  } catch (error) {
    res.status(503).json({
      closed: false,
      ticket: req.params.ticket,
      error: error instanceof Error ? error.message : "MT5 close-position unavailable"
    });
  }
});
