import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
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
    const commandId = await queueCommand({ type: "run_cycle" });
    res.status(202).json({ ok: true, queued: true, command_id: commandId });
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
    res.status(202).json({ closed: false, queued: true, ticket: req.params.ticket, command_id: commandId });
  } catch (error) {
    res.status(503).json({
      closed: false,
      ticket: req.params.ticket,
      error: error instanceof Error ? error.message : "MT5 close-position unavailable"
    });
  }
});
