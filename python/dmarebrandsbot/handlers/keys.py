from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import code, esc, lines, money, pair, state_label, title, truncate, until
from ..reply import confirm, send, send_private

FILTERS = {"all", "unused", "active", "expired"}


def key_line(key: dict) -> str:
    customer = key.get("customer")
    owner = f" · {esc(customer['username'])}" if customer else ""
    expiry = f" · expires {until(key['expires_at'])}" if key.get("expires_at") else ""
    return (
        f"{code(key['code'])} - {state_label(key.get('state'))} · "
        f"{key.get('days')}d {esc(key.get('product'))}{owner}{expiry}"
    )


async def keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = list(context.args or [])
    chosen = "all"
    if args and args[0].lower() in FILTERS:
        chosen = args[0].lower()
        args = args[1:]
    search = " ".join(args).strip() or None

    result = await context.application.bot_data["api"].list_keys(
        filter=chosen, search=search, limit=25
    )
    rows = result.get("data") or []

    if not rows:
        await send(update, "No keys matched that.")
        return

    body = lines(
        title(f"Keys - {'everything' if chosen == 'all' else state_label(chosen)}"),
        "",
        *[key_line(key) for key in rows],
        "",
        f"<i>{len(rows)} shown</i>",
    )
    await send_private(update, context, truncate(body), "Sent you the key list in a private message.")


async def key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    wanted = (context.args or [""])[0].strip()
    if not wanted:
        await send(update, "Usage: <code>/key DMA-XXXX-XXXX-XXXX-XXXX</code>")
        return

    found = await context.application.bot_data["api"].get_key(wanted)
    customer = found.get("customer")

    await send_private(
        update,
        context,
        lines(
            title(f"Key {found['code']}"),
            "",
            pair("State", state_label(found.get("state"))),
            pair("Product", f"{found.get('days')}d {found.get('product')}"),
            pair("Cost", money(found.get("cost_usd"))),
            pair("Redeemed", until(found["redeemed_at"]) if found.get("redeemed_at") else "not yet"),
            pair("Expires", until(found["expires_at"]) if found.get("expires_at") else "n/a"),
            pair("Customer", f"{customer['username']} (id {customer['id']})") if customer else "",
        ),
        "Sent you the key details in a private message.",
    )


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    args = list(context.args or [])
    plan_id = (args[0] if args else "").strip()

    if not plan_id:
        await send(update, "Usage: <code>/buy rust-30 2</code>\nRun /plans to see the ids.")
        return

    try:
        count = int(args[1]) if len(args) > 1 else 1
    except ValueError:
        count = -1
    if count < 1 or count > 25:
        await send(update, "Count must be a whole number between 1 and 25.")
        return

    plan_list = await api.plans()
    chosen = next((p for p in plan_list.get("data") or [] if p["id"] == plan_id), None)
    if chosen is None:
        await send(
            update,
            f"There is no plan called {code(plan_id)}. Run /plans to see what is available.",
        )
        return

    total = round(float(chosen["your_price_usd"]) * count, 2)
    balance = await api.balance()
    available = float(balance.get("balance_usd") or 0)

    if available < total:
        await send(
            update,
            lines(
                title("Not enough balance"),
                f"{count} × {esc(chosen['label'])} costs {money(total)} but the account "
                f"only has {money(available)}.",
            ),
        )
        return

    agreed = await confirm(
        update,
        context,
        lines(
            title("Confirm this purchase"),
            "",
            f"{count} × {esc(chosen['label'])} ({chosen['days']} days)",
            f"{money(chosen['your_price_usd'])} each · {money(total)} total",
            f"Balance after: {money(available - total)}",
        ),
        confirm_label=f"Buy for {money(total)}",
    )

    if not agreed:
        return

    bought = await api.buy_keys(
        plan_id, count, f"telegram:{update.effective_chat.id}:{update.effective_message.message_id}"
    )
    codes = [k["code"] for k in bought.get("data") or []]
    plural = "" if len(codes) == 1 else "s"
    summary = f"Bought {len(codes)} key{plural} for {money(bought.get('spent_usd'))}"

    await send_private(
        update,
        context,
        lines(
            title(f"Bought {len(codes)} key{plural}"),
            "",
            "\n".join(code(c) for c in codes),
            "",
            pair("Spent", money(bought.get("spent_usd"))),
            pair("Balance", money(bought.get("balance_usd"))),
        ),
        f"{summary}. Codes sent privately.",
        fail_note=(
            f"{summary}, but I could not message you the codes.\n"
            "Open a chat with me and press <b>Start</b>, then run /keys unused there. Do not buy again."
        ),
    )

    who = update.effective_user.username or update.effective_user.id
    await context.application.bot_data["log"](
        f"{esc(who)} bought {len(codes)} × {esc(chosen['label'])} for {money(bought.get('spent_usd'))}"
    )


async def refund(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    wanted = (context.args or [""])[0].strip()

    if not wanted:
        await send(update, "Usage: <code>/refund DMA-XXXX-XXXX-XXXX-XXXX</code>")
        return

    found = await api.get_key(wanted)
    if found.get("state") != "unused":
        await send(
            update,
            lines(
                title("Cannot refund that"),
                "Only keys still in stock can be refunded. That one has already been redeemed.",
            ),
        )
        return

    agreed = await confirm(
        update,
        context,
        lines(
            title("Confirm this refund"),
            "",
            f"{code(found['code'])} - {found['days']}d {esc(found['product'])}",
            f"This destroys the key and puts {money(found.get('cost_usd'))} back on the balance.",
            "It cannot be undone and the code stops working immediately.",
        ),
        confirm_label=f"Refund {money(found.get('cost_usd'))}",
        sensitive=True,
    )

    if not agreed:
        return

    result = await api.refund_key(wanted)
    refunded = f"Refunded 1 key for {money(result.get('refunded_usd'))}"
    await send_private(
        update,
        context,
        lines(
            title("Refunded"),
            f"{code(result['code'])} is gone.",
            "",
            pair("Returned", money(result.get("refunded_usd"))),
            pair("Balance", money(result.get("balance_usd"))),
        ),
        f"{refunded}. Details sent privately.",
        fail_note=f"{refunded}. I could not message you the details privately.",
    )

    who = update.effective_user.username or update.effective_user.id
    await context.application.bot_data["log"](
        f"{esc(who)} refunded {code(result['code'])} for {money(result.get('refunded_usd'))}"
    )
