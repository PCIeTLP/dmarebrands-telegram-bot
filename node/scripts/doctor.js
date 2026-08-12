import { Bot } from "grammy";
import { loadConfig, GROUPS, SCOPES } from "../src/config.js";
import { COMMANDS, MENU } from "../src/commands/index.js";
import { PartnerApi, friendly } from "../src/api.js";

let problems = 0;
const ok = (l, d = "") => console.log(`  PASS  ${l}${d ? `  (${d})` : ""}`);
const bad = (l, d = "") => { problems += 1; console.log(`  FAIL  ${l}${d ? `  (${d})` : ""}`); };

console.log("\nchecking your .env");
const config = loadConfig();
ok("env parsed", `${config.userScopes.size} allowlisted user(s)`);

console.log("\nchecking the partner API");
const api = new PartnerApi(config);
try {
  const me = await api.me();
  ok("API key works", `${me.username}, balance $${me.balance_usd}, ${me.discount_pct}% off`);
} catch (err) {
  bad("API key rejected", friendly(err));
}

console.log("\nchecking Telegram");
const bot = new Bot(config.token);
try {
  const me = await bot.api.getMe();
  ok("token works", `@${me.username}`);
  if (!me.can_read_all_group_messages && config.allowedChats.size) {
    ok("privacy mode is on", "commands still reach the bot, that is fine");
  }
} catch (err) {
  bad("token rejected", err?.description ?? err?.message ?? String(err));
}

try {
  const published = await bot.api.getMyCommands();
  if (published.length) ok("command menu published", `${published.length} entries`);
  else bad("command menu is empty", "run: npm run register");
} catch (err) {
  bad("could not read the command menu", err?.description ?? String(err));
}

if (config.logChatId) {
  try {
    await bot.api.getChat(config.logChatId);
    ok("log chat reachable", config.logChatId);
  } catch {
    bad("log chat unreachable", "the bot must be a member of LOG_CHAT_ID");
  }
}

console.log("\nchecking permission wiring");
const covered = new Set();
for (const scopes of config.userScopes.values()) for (const scope of scopes) covered.add(scope);

for (const command of COMMANDS) {
  if (!command.scope) ok(`/${command.name} is open to everyone`);
  else if (covered.has(command.scope)) ok(`/${command.name} usable`, command.scope);
  else bad(`/${command.name} is unreachable`, `nobody has ${command.scope}`);
}

const unknown = [...covered].filter((s) => !SCOPES.includes(s));
if (unknown.length) bad("unknown scopes granted", unknown.join(", "));

const missing = COMMANDS.filter((c) => c.name !== "start" && !MENU.some((m) => m.command === c.name));
if (missing.length) bad("commands missing from the menu", missing.map((c) => c.name).join(", "));
else ok("every command is in the menu");

console.log("\nwho can do what");
for (const [group, scopes] of Object.entries(GROUPS)) {
  const ids = [...config.userScopes.entries()]
    .filter(([, granted]) => scopes.every((s) => granted.has(s)))
    .map(([id]) => id);
  console.log(`  ${group.padEnd(15)} ${ids.length ? ids.join(", ") : "(none)"}`);
}

console.log("\nchat policy");
console.log(config.allowedChats.size
  ? `  private chats + groups: ${[...config.allowedChats].join(", ")}`
  : "  private chats only (set ALLOWED_CHATS to allow a group)");
console.log(`  results sent privately: ${config.privateResults ? "yes" : "no"}`);

console.log(problems === 0 ? "\nEverything looks good.\n" : `\n${problems} problem(s) to fix.\n`);
process.exitCode = problems === 0 ? 0 : 1;
