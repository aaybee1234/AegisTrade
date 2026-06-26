import { Router } from "express";
import { z } from "zod";

export const botsRouter = Router();

const botSettingsSchema = z.object({
  symbols: z.array(z.string()).default(["XAUUSD", "EURUSD"]),
  lotSize: z.number().positive().max(0.1).default(0.01),
  maxOpenTrades: z.number().int().positive().max(5).default(1),
  maxTradesPerDay: z.number().int().positive().max(20).default(5),
  dailyLossLimit: z.number().positive().default(25),
  minConfidence: z.number().min(0).max(1).default(0.65),
  maxSpreadPoints: z.number().positive().default(40)
});

botsRouter.get("/", (_req, res) => {
  res.json({
    bots: [
      {
        id: "demo-bot-1",
        name: "Aegis Demo Bot",
        status: "paused",
        mode: "demo"
      }
    ]
  });
});

botsRouter.post("/", (req, res) => {
  const settings = botSettingsSchema.parse(req.body.settings ?? {});

  res.status(201).json({
    id: "demo-bot-1",
    name: req.body.name ?? "Aegis Demo Bot",
    status: "paused",
    mode: "demo",
    settings
  });
});

botsRouter.patch("/:id/settings", (req, res) => {
  const settings = botSettingsSchema.parse(req.body);

  res.json({
    id: req.params.id,
    settings
  });
});

botsRouter.post("/:id/start", (req, res) => {
  res.json({
    id: req.params.id,
    status: "active",
    guardrail: "demo-only"
  });
});

botsRouter.post("/:id/stop", (req, res) => {
  res.json({
    id: req.params.id,
    status: "paused"
  });
});

