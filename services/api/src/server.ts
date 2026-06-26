import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import { botsRouter } from "./routes/bots.js";
import { mt5Router } from "./routes/mt5.js";

dotenv.config();

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

