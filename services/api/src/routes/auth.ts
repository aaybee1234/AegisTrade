import { Router } from "express";
import { z } from "zod";
import { authenticateUser, createSession, createUser, getUserByToken } from "../store.js";

export const authRouter = Router();

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(120)
});

function publicUser(user: { id: string; email: string; createdAt: string }) {
  return { id: user.id, email: user.email, createdAt: user.createdAt };
}

authRouter.post("/register", (req, res) => {
  const credentials = credentialsSchema.parse(req.body);
  try {
    const user = createUser(credentials.email, credentials.password);
    const token = createSession(user.id);
    res.status(201).json({ token, user: publicUser(user) });
  } catch (error) {
    res.status(409).json({ error: error instanceof Error ? error.message : "Registration failed." });
  }
});

authRouter.post("/login", (req, res) => {
  const credentials = credentialsSchema.parse(req.body);
  const user = authenticateUser(credentials.email, credentials.password);
  if (!user) {
    res.status(401).json({ error: "Invalid email or password." });
    return;
  }

  const token = createSession(user.id);
  res.json({ token, user: publicUser(user) });
});

authRouter.get("/me", (req, res) => {
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : undefined;
  const user = getUserByToken(token);
  if (!user) {
    res.status(401).json({ error: "Not authenticated." });
    return;
  }

  res.json({ user: publicUser(user) });
});
