import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { Router } from "express";

const execFileAsync = promisify(execFile);
export const mt5Router = Router();

const workerCwd = path.resolve(process.cwd(), "..", "worker");

async function runWorkerJson(moduleName: string, args: string[] = []) {
  const { stdout } = await execFileAsync("python", ["-m", moduleName, ...args], {
    cwd: workerCwd,
    timeout: 45_000,
    windowsHide: true
  });

  return JSON.parse(stdout);
}

async function closeMt5Position(ticket: string) {
  try {
    return await runWorkerJson("aegis_worker.close_position_json", [ticket]);
  } catch (error: any) {
    const stdout = error?.stdout;
    if (stdout) {
      return JSON.parse(stdout);
    }
    throw error;
  }
}

mt5Router.get("/symbols", (_req, res) => {
  res.json({
    symbols: ["XAUUSDm", "EURUSDm", "GBPUSDm", "USDJPYm", "BTCUSDm"]
  });
});

mt5Router.get("/status", async (_req, res) => {
  try {
    const status = await runWorkerJson("aegis_worker.status_json");
    res.json(status);
  } catch (error) {
    res.status(503).json({
      account: {
        connected: false,
        is_demo: true,
        connection_error: error instanceof Error ? error.message : "MT5 status unavailable"
      },
      positions: [],
      summary: {
        open_positions: 0,
        floating_pl: 0
      }
    });
  }
});

mt5Router.get("/positions", async (_req, res) => {
  try {
    const status = await runWorkerJson("aegis_worker.status_json");
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
    const advisory = await runWorkerJson("aegis_worker.advisory_json");
    res.json(advisory);
  } catch (error) {
    res.status(503).json({
      setups: [],
      error: error instanceof Error ? error.message : "MT5 advisory unavailable"
    });
  }
});

mt5Router.get("/accounts/:id/status", async (req, res) => {
  try {
    const status = await runWorkerJson("aegis_worker.status_json");
    res.json({ id: req.params.id, ...status.account });
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
    const result = await closeMt5Position(req.params.ticket);
    res.status(result.closed ? 200 : 400).json(result);
  } catch (error) {
    res.status(503).json({
      closed: false,
      ticket: req.params.ticket,
      error: error instanceof Error ? error.message : "MT5 close-position unavailable"
    });
  }
});
