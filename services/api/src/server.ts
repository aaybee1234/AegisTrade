import cors from "cors";
import dotenv from "dotenv";
import { existsSync } from "node:fs";
import path from "node:path";
import express from "express";
import { botsRouter } from "./routes/bots.js";
import { mt5Router } from "./routes/mt5.js";

const envCandidates = [
  path.resolve(process.cwd(), ".env"),
  path.resolve(process.cwd(), "..", "..", ".env")
];
const envPath = envCandidates.find((candidate) => existsSync(candidate));
dotenv.config(envPath ? { path: envPath } : undefined);

const app = express();
const port = Number(process.env.API_PORT ?? 4000);

app.use(cors());
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({
    ok: true,
    service: "aegistrade-api",
    mode: "demo-only"
  });
});

app.use("/bots", botsRouter);
app.use("/mt5", mt5Router);

app.listen(port, () => {
  console.log(`AegisTrade API listening on http://localhost:${port}`);
});
