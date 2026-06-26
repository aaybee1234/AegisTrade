import { Router } from "express";
import { z } from "zod";
import { createMt5Account, getUserByToken, listMt5Accounts } from "../store.js";

export const accountsRouter = Router();

const mt5AccountSchema = z.object({
  label: z.string().min(1).max(80).default("Exness MT5"),
  login: z.string().min(3).max(32),
  password: z.string().min(1).max(160),
  server: z.string().min(3).max(80),
  accountType: z.enum(["demo", "live"]).default("demo")
});

accountsRouter.use((req, res, next) => {
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : undefined;
  const user = getUserByToken(token);
  if (!user) {
    res.status(401).json({ error: "Not authenticated." });
    return;
  }
  res.locals.user = user;
  next();
});

accountsRouter.get("/", (_req, res) => {
  res.json({ accounts: listMt5Accounts(res.locals.user.id) });
});

accountsRouter.post("/", (req, res) => {
  const input = mt5AccountSchema.parse(req.body);
  const account = createMt5Account({ userId: res.locals.user.id, ...input });
  res.status(201).json({ account });
});
