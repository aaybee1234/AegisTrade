import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export type UserRecord = {
  id: string;
  email: string;
  passwordHash: string;
  createdAt: string;
};

export type SessionRecord = {
  tokenHash: string;
  userId: string;
  createdAt: string;
  expiresAt: string;
};

export type Mt5AccountRecord = {
  id: string;
  userId: string;
  label: string;
  login: string;
  server: string;
  accountType: "demo" | "live";
  encryptedPassword: string;
  status: "pending" | "connected" | "error";
  createdAt: string;
  updatedAt: string;
};

type StoreData = {
  users: UserRecord[];
  sessions: SessionRecord[];
  mt5Accounts: Mt5AccountRecord[];
};

const dataDir = process.env.DATA_DIR ?? path.resolve(process.cwd(), "data");
const storePath = path.join(dataDir, "aegistrade-store.json");
const secret = process.env.APP_SECRET ?? "aegistrade-local-dev-secret-change-me";

function ensureStore(): StoreData {
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  if (!fs.existsSync(storePath)) {
    const initial: StoreData = { users: [], sessions: [], mt5Accounts: [] };
    fs.writeFileSync(storePath, JSON.stringify(initial, null, 2));
    return initial;
  }

  return JSON.parse(fs.readFileSync(storePath, "utf8")) as StoreData;
}

function saveStore(data: StoreData) {
  fs.writeFileSync(storePath, JSON.stringify(data, null, 2));
}

function hash(value: string) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function passwordHash(password: string, salt = crypto.randomBytes(16).toString("hex")) {
  const derived = crypto.scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${derived}`;
}

function verifyPassword(password: string, stored: string) {
  const [salt, expected] = stored.split(":");
  if (!salt || !expected) return false;
  const actual = crypto.scryptSync(password, salt, 64).toString("hex");
  return crypto.timingSafeEqual(Buffer.from(actual, "hex"), Buffer.from(expected, "hex"));
}

function encryptionKey() {
  return crypto.createHash("sha256").update(secret).digest();
}

export function encryptSecret(value: string) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", encryptionKey(), iv);
  const encrypted = Buffer.concat([cipher.update(value, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return `${iv.toString("base64")}:${tag.toString("base64")}:${encrypted.toString("base64")}`;
}

export function decryptSecret(value: string) {
  const [ivRaw, tagRaw, encryptedRaw] = value.split(":");
  if (!ivRaw || !tagRaw || !encryptedRaw) return "";
  const decipher = crypto.createDecipheriv("aes-256-gcm", encryptionKey(), Buffer.from(ivRaw, "base64"));
  decipher.setAuthTag(Buffer.from(tagRaw, "base64"));
  return Buffer.concat([decipher.update(Buffer.from(encryptedRaw, "base64")), decipher.final()]).toString("utf8");
}

export function createUser(email: string, password: string) {
  const data = ensureStore();
  const normalizedEmail = email.trim().toLowerCase();
  if (data.users.some((user) => user.email === normalizedEmail)) {
    throw new Error("Email is already registered.");
  }

  const user: UserRecord = {
    id: crypto.randomUUID(),
    email: normalizedEmail,
    passwordHash: passwordHash(password),
    createdAt: new Date().toISOString()
  };
  data.users.push(user);
  saveStore(data);
  return user;
}

export function authenticateUser(email: string, password: string) {
  const data = ensureStore();
  const user = data.users.find((candidate) => candidate.email === email.trim().toLowerCase());
  if (!user || !verifyPassword(password, user.passwordHash)) {
    return null;
  }
  return user;
}

export function createSession(userId: string) {
  const data = ensureStore();
  const token = crypto.randomBytes(32).toString("base64url");
  const session: SessionRecord = {
    tokenHash: hash(token),
    userId,
    createdAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 14).toISOString()
  };
  data.sessions = data.sessions.filter((item) => new Date(item.expiresAt).getTime() > Date.now());
  data.sessions.push(session);
  saveStore(data);
  return token;
}

export function getUserByToken(token: string | undefined) {
  if (!token) return null;
  const data = ensureStore();
  const tokenHash = hash(token);
  const session = data.sessions.find((item) => item.tokenHash === tokenHash && new Date(item.expiresAt).getTime() > Date.now());
  if (!session) return null;
  return data.users.find((user) => user.id === session.userId) ?? null;
}

export function listMt5Accounts(userId: string) {
  const data = ensureStore();
  return data.mt5Accounts
    .filter((account) => account.userId === userId)
    .map(({ encryptedPassword, ...safeAccount }) => safeAccount);
}

export function createMt5Account(input: {
  userId: string;
  label: string;
  login: string;
  password: string;
  server: string;
  accountType: "demo" | "live";
}) {
  const data = ensureStore();
  const now = new Date().toISOString();
  const account: Mt5AccountRecord = {
    id: crypto.randomUUID(),
    userId: input.userId,
    label: input.label.trim() || `${input.server} ${input.login}`,
    login: input.login.trim(),
    server: input.server.trim(),
    accountType: input.accountType,
    encryptedPassword: encryptSecret(input.password),
    status: "pending",
    createdAt: now,
    updatedAt: now
  };
  data.mt5Accounts = data.mt5Accounts.filter(
    (existing) => !(existing.userId === input.userId && existing.login === account.login && existing.server === account.server)
  );
  data.mt5Accounts.push(account);
  saveStore(data);
  const { encryptedPassword, ...safeAccount } = account;
  return safeAccount;
}
