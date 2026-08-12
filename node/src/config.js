import "dotenv/config";

const TOKEN_RE = /^\d{6,}:[A-Za-z0-9_-]{30,}$/;
const USER_ID_RE = /^\d{1,19}$/;
const CHAT_ID_RE = /^-?\d{1,19}$/;

export const SCOPES = [
  "account.read",
  "billing.read",
  "keys.read",
  "keys.buy",
  "keys.refund",
  "customers.read",
  "hwid.reset",
  "domains.read",
];

export const GROUPS = {
  USERS_ADMIN: SCOPES,
  USERS_KEYS: ["account.read", "keys.read", "keys.buy", "keys.refund", "customers.read"],
  USERS_HWID: ["hwid.reset", "keys.read", "customers.read"],
  USERS_BILLING: ["account.read", "billing.read"],
  USERS_READ: ["account.read", "keys.read", "customers.read", "domains.read"],
};

class ConfigError extends Error {}

function required(name) {
  const value = (process.env[name] ?? "").trim();
  if (!value) throw new ConfigError(`${name} is missing from your .env`);
  return value;
}

function idList(name, pattern, label) {
  const raw = (process.env[name] ?? "").trim();
  if (!raw) return [];
  const parts = raw
    .split(/[,\s]+/)
    .map((p) => p.trim())
    .filter(Boolean);

  const bad = parts.filter((p) => !pattern.test(p));
  if (bad.length) throw new ConfigError(`${name} contains invalid ${label}: ${bad.join(", ")}`);
  return parts;
}

function buildUserScopes() {
  const map = new Map();
  let total = 0;

  for (const [envName, scopes] of Object.entries(GROUPS)) {
    for (const userId of idList(envName, USER_ID_RE, "Telegram user IDs")) {
      total += 1;
      const current = map.get(userId) ?? new Set();
      for (const scope of scopes) current.add(scope);
      map.set(userId, current);
    }
  }

  if (!total) {
    throw new ConfigError(
      "No users configured. Set at least one of USERS_ADMIN, USERS_KEYS, USERS_HWID, USERS_BILLING or USERS_READ.\n" +
        "Message @userinfobot on Telegram to find your numeric user ID."
    );
  }

  return map;
}

function load() {
  const base = (process.env.DMAREBRANDS_API_BASE ?? "https://api.dmarebrands.st/v1").trim();

  let parsed;
  try {
    parsed = new URL(base);
  } catch {
    throw new ConfigError(`DMAREBRANDS_API_BASE is not a valid URL: "${base}"`);
  }
  if (parsed.protocol !== "https:" && parsed.hostname !== "localhost" && parsed.hostname !== "127.0.0.1") {
    throw new ConfigError("DMAREBRANDS_API_BASE must use https so your API key is never sent in the clear.");
  }

  const apiKey = required("DMAREBRANDS_API_KEY");
  if (!apiKey.startsWith("dmarebrands_live_")) {
    throw new ConfigError(
      'DMAREBRANDS_API_KEY does not look right. Partner keys start with "dmarebrands_live_". Create one at https://partners.dmarebrands.st/partners/api'
    );
  }

  const token = required("TELEGRAM_TOKEN");
  if (!TOKEN_RE.test(token)) {
    throw new ConfigError(
      'TELEGRAM_TOKEN does not look right. BotFather gives you something like "123456789:AAF...". Check you copied all of it.'
    );
  }

  const logChat = (process.env.LOG_CHAT_ID ?? "").trim();
  if (logChat && !CHAT_ID_RE.test(logChat)) {
    throw new ConfigError(`LOG_CHAT_ID must be a numeric chat ID, got "${logChat}"`);
  }

  return {
    token,
    apiKey,
    apiBase: base.replace(/\/+$/, ""),
    userScopes: buildUserScopes(),
    allowedChats: new Set(idList("ALLOWED_CHATS", CHAT_ID_RE, "chat IDs")),
    privateResults: (process.env.PRIVATE_RESULTS ?? "true").toLowerCase() !== "false",
    logChatId: logChat || null,
  };
}

export function loadConfig() {
  try {
    return load();
  } catch (err) {
    if (err instanceof ConfigError) {
      console.error(`\nConfiguration problem: ${err.message}\n`);
      console.error("Copy .env.example to .env and fill it in, then try again.\n");
      process.exit(1);
    }
    throw err;
  }
}
