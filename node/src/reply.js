import { InlineKeyboard } from "grammy";

const CONFIRM_TIMEOUT_MS = 60_000;
const HTML = { parse_mode: "HTML", link_preview_options: { is_disabled: true } };
const pending = new Map();
let lastPromptId = Date.now();
const NO_PRIVATE_CHAT =
  "I could not message you privately, so I am not posting this in the group.\n" +
  "Open a chat with me and press <b>Start</b>, then run the command again.";

export async function send(ctx, text, extra = {}) {
  return ctx.reply(text, { ...HTML, ...extra });
}

function keepPrivate(ctx) {
  return ctx.chat?.type !== "private" && ctx.dmarebrands.config.privateResults;
}

// Sends `text` to the user's private chat and leaves `note` in the group. Returns the private
// message, or null after posting `failNote` when the bot cannot message the user.
async function sendDirect(ctx, text, note, { extra = {}, failNote = NO_PRIVATE_CHAT } = {}) {
  let message;
  try {
    message = await ctx.api.sendMessage(ctx.from.id, text, { ...HTML, ...extra });
  } catch {
    await send(ctx, failNote);
    return null;
  }
  // The private message is already out, so losing the group note must not undo it.
  await send(ctx, note).catch(() => {});
  return message;
}

// `failNote` replaces the "run the command again" advice for results of something already done.
export async function sendPrivate(ctx, text, publicNote, failNote) {
  if (!keepPrivate(ctx)) return send(ctx, text);
  return sendDirect(ctx, text, publicNote ?? "Sent you the details in a private message.", { failNote });
}

export function confirmKeyboard(id, confirmLabel) {
  return new InlineKeyboard()
    .text(confirmLabel, `ok:${id}`)
    .text("Cancel", `no:${id}`);
}

export async function confirm(ctx, { text, confirmLabel, sensitive = false }) {
  const id = `${ctx.from.id}:${++lastPromptId}`;
  const privately = sensitive && keepPrivate(ctx);
  const extra = { reply_markup: confirmKeyboard(id, confirmLabel) };

  // Listen before the prompt goes out, so a quick press is not turned away as expired.
  const pressed = new Promise((settle) => pending.set(id, { userId: ctx.from.id, settle }));
  let message = null;
  try {
    message = privately
      ? await sendDirect(ctx, text, "Sent you a confirmation in a private message.", { extra })
      : await send(ctx, text, extra);
  } finally {
    if (!message) pending.delete(id);
  }
  if (!message) return { ok: false, cancelled: false };

  let timer;
  const expired = new Promise((resolve) => {
    timer = setTimeout(resolve, CONFIRM_TIMEOUT_MS, null);
  });
  const answer = await Promise.race([pressed, expired]);
  clearTimeout(timer);
  pending.delete(id);

  // Show the outcome on the prompt itself when the caller's reply will not land next to it.
  const outcome = answer === null ? "Timed out" : privately && !answer ? "Cancelled" : null;
  if (outcome) {
    await ctx.api
      .editMessageText(message.chat.id, message.message_id, `${text}\n\n<i>${outcome}. Nothing was done.</i>`, {
        parse_mode: "HTML",
      })
      .catch(() => {});
  }
  // A cancel on a private prompt is acknowledged there, so the caller must not repeat it in the group.
  return { ok: answer === true, cancelled: answer === false && !privately };
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

  // Settle first, so the waiting command does not sit behind these two Telegram calls.
  pending.delete(id);
  waiting.settle(verb === "ok");
  ctx.editMessageReplyMarkup({ reply_markup: undefined }).catch(() => {});
  await ctx.answerCallbackQuery();
}

export function clearPending() {
  pending.clear();
}
