import { Bot, GrammyError, HttpError } from "grammy";
import { loadConfig } from "./config.js";
import { ApiError, PartnerApi, friendly } from "./api.js";
import { BY_NAME, COMMANDS } from "./commands/index.js";
import { allows, chatAllowed, deniedMessage, scopesFor } from "./permissions.js";
import { esc, title, lines } from "./format.js";
import { handleCallback, send } from "./reply.js";

const config = loadConfig();
const api = new PartnerApi(config);
const bot = new Bot(config.token);

async function logAction(text) {
  if (!config.logChatId) return;
  try {
    await bot.api.sendMessage(config.logChatId, text, { parse_mode: "HTML" });
  } catch {}
}

bot.use(async (ctx, next) => {
  ctx.dmarebrands = { config, api };
  await next();
});

bot.on("callback_query:data", handleCallback);

async function runCommand(command, ctx) {
  if (!chatAllowed(ctx.chat, config)) {
    await send(
      ctx,
      "This bot is not set up for this chat. Message me privately, or ask the owner to add this chat to ALLOWED_CHATS."
    );
    return;
  }

  const granted = scopesFor(ctx.from?.id, config.userScopes);

  if (command.scope && !allows(granted, command.scope)) {
    await send(ctx, deniedMessage(command.scope));
    return;
  }

  const args = (ctx.match ?? "").trim().split(/\s+/).filter(Boolean);

  try {
    await command.run({ ctx, api, config, granted, args, commands: COMMANDS, log: logAction });
  } catch (err) {
    const message = friendly(err);
    const detail = err instanceof ApiError && err.requestId ? `\nRequest id: <code>${esc(err.requestId)}</code>` : "";

    if (!(err instanceof ApiError)) {
      console.error(`[/${command.name}]`, err);
    }

    await send(ctx, lines(title("That did not work"), esc(message) + detail)).catch(() => {});
  }
}

for (const command of COMMANDS) {
  bot.command(command.name, (ctx) => {
    runCommand(command, ctx).catch((err) => console.error(`[/${command.name}]`, err));
  });
}

bot.catch((err) => {
  const e = err.error;
  if (e instanceof GrammyError) console.error("telegram rejected a request:", e.description);
  else if (e instanceof HttpError) console.error("could not reach telegram:", e.message);
  else console.error("bot error:", e);
});

process.on("unhandledRejection", (err) => console.error("unhandled rejection", err));

async function main() {
  try {
    const me = await api.me();
    console.log(`Partner API connected as ${me.username} · balance $${me.balance_usd}`);
  } catch (err) {
    console.error(`\nThe partner API rejected the bot's key: ${friendly(err)}`);
    console.error("Fix DMAREBRANDS_API_KEY in your .env, then restart.\n");
  }

  await bot.start({
    onStart: (info) => {
      console.log(`Logged in as @${info.username}`);
      console.log(`Serving ${BY_NAME.size} commands to ${config.userScopes.size} allowlisted user(s)`);
      if (!config.allowedChats.size) {
        console.log("Private chats only. Set ALLOWED_CHATS to use it in a group.");
      }
    },
  });
}

main().catch((err) => {
  console.error(`\nCould not start: ${err?.message ?? err}`);
  console.error("Check TELEGRAM_TOKEN in your .env.\n");
  process.exit(1);
});
