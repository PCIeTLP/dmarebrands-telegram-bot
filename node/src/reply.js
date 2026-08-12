import { InlineKeyboard } from "grammy";

const CONFIRM_TIMEOUT_MS = 60_000;
const pending = new Map();

export async function send(ctx, text, extra = {}) {
  return ctx.reply(text, { parse_mode: "HTML", link_preview_options: { is_disabled: true }, ...extra });
}

export async function sendPrivate(ctx, text, publicNote) {
  const config = ctx.dmarebrands.config;
  const isPrivate = ctx.chat?.type === "private";

  if (isPrivate || !config.privateResults) {
    return send(ctx, text);
  }

  try {
    await ctx.api.sendMessage(ctx.from.id, text, {
      parse_mode: "HTML",
      link_preview_options: { is_disabled: true },
    });
    return send(ctx, publicNote ?? "Sent you the details in a private message.");
  } catch {
    return send(
      ctx,
      "I could not message you privately, so I am not posting this in the group.\n" +
        "Open a chat with me and press <b>Start</b>, then run the command again."
    );
  }
}

export function confirmKeyboard(id, confirmLabel) {
  return new InlineKeyboard()
    .text(confirmLabel, `ok:${id}`)
    .text("Cancel", `no:${id}`);
}

export async function confirm(ctx, { text, confirmLabel }) {
  const id = `${ctx.from.id}:${Date.now()}`;
  const message = await send(ctx, text, { reply_markup: confirmKeyboard(id, confirmLabel) });

  return new Promise((resolve) => {
    const timer = setTimeout(async () => {
      pending.delete(id);
      await ctx.api
        .editMessageText(message.chat.id, message.message_id, `${text}\n\n<i>Timed out. Nothing was done.</i>`, {
          parse_mode: "HTML",
        })
        .catch(() => {});
      resolve({ ok: false, timedOut: true, message });
    }, CONFIRM_TIMEOUT_MS);

    pending.set(id, {
      userId: ctx.from.id,
      settle(answer) {
        clearTimeout(timer);
        pending.delete(id);
        resolve({ ok: answer, timedOut: false, message });
      },
    });
  });
}

export async function handleCallback(ctx) {
  const data = ctx.callbackQuery?.data ?? "";
  const [verb, ...rest] = data.split(":");
  const id = rest.join(":");
  const waiting = pending.get(id);

  if (!waiting) {
    await ctx.answerCallbackQuery({ text: "That prompt has expired. Run the command again." });
    return;
  }
  if (waiting.userId !== ctx.from.id) {
    await ctx.answerCallbackQuery({ text: "That confirmation is not yours." });
    return;
  }

  await ctx.answerCallbackQuery();
  await ctx.editMessageReplyMarkup({ reply_markup: undefined }).catch(() => {});
  waiting.settle(verb === "ok");
}

export function clearPending() {
  pending.clear();
}
