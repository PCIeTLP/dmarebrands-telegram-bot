from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import ago, code, esc, lines, title, truncate
from ..reply import request_key, send

ACTIONS = {"test", "pause", "resume"}


def hook_line(h: dict) -> str:
    kind = "update notes" if h.get("kind") == "updates" else "status changes"
    state = "on" if h.get("enabled") else "paused"
    sent = f"last post {ago(h['last_sent_at'])}" if h.get("last_sent_at") else "nothing posted yet"
    return lines(
        f"{title('#' + str(h.get('id')) + ' ' + (h.get('label') or 'Unnamed webhook'))} · {kind} · {state}",
        f"{esc(', '.join(h.get('products') or []))} · {sent}",
        f"Last error: {esc(h['last_error'])}" if h.get("last_error") else "",
    )


async def webhooks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = await context.application.bot_data["api"].webhooks()
    rows = result.get("data") or []

    if not rows:
        await send(update, "No webhooks yet. Add one on the Webhooks page of the partner panel.")
        return

    await send(
        update,
        truncate(
            lines(title(f"Webhooks ({len(rows)} of {result.get('max', 10)})"), "", "\n\n".join(hook_line(h) for h in rows))
        ),
    )


async def webhook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = list(context.args or [])
    hook_id = int(args[0]) if args and args[0].isdigit() else 0
    action = (args[1] if len(args) > 1 else "").strip().lower()

    if hook_id < 1 or action not in ACTIONS:
        await send(
            update,
            f"Usage: {code('/webhook 7 test')}, {code('/webhook 7 pause')} or {code('/webhook 7 resume')}",
        )
        return

    api = context.application.bot_data["api"]

    if action == "test":
        result = await api.test_webhook(hook_id, key=request_key(update))
        if result.get("sent"):
            await send(update, lines(title("Test post sent"), f"Check the channel webhook #{hook_id} posts to."))
        else:
            paused = (
                f"The webhook has been paused. Fix it in Discord, then run {code(f'/webhook {hook_id} resume')}."
                if result.get("paused")
                else ""
            )
            await send(
                update,
                lines(title("Discord refused the test post"), esc(result.get("error") or "No reason given."), paused),
            )
        return

    on = action == "resume"
    hook = await api.set_webhook_enabled(hook_id, on, key=request_key(update))
    name = title(f"#{hook.get('id')} {hook.get('label') or 'Unnamed webhook'}")
    await send(update, f"{name} posts again." if on else f"{name} will not post until you resume it.")

    user = update.effective_user
    await context.application.bot_data["log"](
        f"{esc(user.username or user.id)} {'resumed' if on else 'paused'} webhook #{hook.get('id')}"
    )
