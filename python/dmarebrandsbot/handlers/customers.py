from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import ago, code, esc, lines, money, pair, title, truncate, until
from ..reply import confirm, send, send_private

KIND_LABEL = {
    "topup": "Top-up",
    "purchase": "Keys bought",
    "refund": "Refund",
    "adjust": "Adjustment",
}


def machine_lines(customer: dict) -> str:
    machines = customer.get("machines") or []
    if not machines:
        return "Nothing bound right now."
    return "\n".join(
        f"{esc(m['scope'])} — bound {ago(m.get('bound_at'))} · last seen {ago(m.get('last_seen'))}"
        for m in machines
    )


async def customers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    search = " ".join(context.args or []).strip() or None
    result = await context.application.bot_data["api"].list_customers(search=search, limit=25)
    rows = result.get("data") or []

    if not rows:
        await send(update, "No customers matched that.")
        return

    body = [title("Customers"), ""]
    for customer in rows:
        state = f"active until {until(customer['expires_at'])}" if customer.get("active") else "expired"
        machines = customer.get("machines") or []
        bound = f" · {len(machines)} machine(s)" if machines else ""
        body.append(
            f"{title(customer['username'])} (id {customer['id']}) — {state} · "
            f"{customer.get('keys', 0)} key(s){bound}"
        )
    body.extend(["", f"<i>{len(rows)} shown</i>"])

    await send_private(
        update, context, truncate(lines(*body)), "Sent you the customer list in a private message."
    )


async def customer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    try:
        customer_id = int(args[0])
    except (IndexError, ValueError):
        await send(update, "Usage: <code>/customer 1042</code>")
        return
    if customer_id < 1:
        await send(update, "Usage: <code>/customer 1042</code>")
        return

    found = await context.application.bot_data["api"].get_customer(customer_id)

    await send_private(
        update,
        context,
        lines(
            title(f"Customer {found['username']}"),
            "",
            pair("Id", found["id"]),
            pair("Access", "Active" if found.get("active") else "Expired"),
            pair("Keys redeemed", found.get("keys", 0)),
            pair("Product", found.get("product") or "none"),
            pair("Expires", until(found["expires_at"]) if found.get("expires_at") else "n/a"),
            pair("Joined", ago(found.get("created_at"))),
            "",
            title("Machines"),
            machine_lines(found),
        ),
        "Sent you the customer details in a private message.",
    )


async def resetkey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    wanted = (context.args or [""])[0].strip()

    if not wanted:
        await send(update, "Usage: <code>/resetkey DMA-XXXX-XXXX-XXXX-XXXX</code>")
        return

    found = await api.get_key(wanted)
    holder = found.get("customer")

    if not holder:
        await send(
            update,
            lines(
                title("Nobody to reset"),
                "That key has not been redeemed yet, so no machine is bound to it.",
            ),
        )
        return

    agreed = await confirm(
        update,
        lines(
            title("Confirm this reset"),
            "",
            f"This clears every hardware lock on {title(holder['username'])} (id {holder['id']}).",
            "They will be able to bind a new machine on their next launch.",
        ),
        confirm_label="Reset machine",
    )
    if not agreed:
        return

    result = await api.reset_by_key(wanted)
    cleared = result.get("cleared", 0)

    await send(
        update,
        lines(
            title("Machine reset"),
            f"Cleared {cleared} lock{'' if cleared == 1 else 's'} for {title(holder['username'])}.",
        ),
    )

    who = update.effective_user.username or update.effective_user.id
    await context.application.bot_data["log"](
        f"{esc(who)} reset HWID for {esc(holder['username'])} via key {code(wanted)}"
    )


async def resetuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    args = context.args or []
    try:
        customer_id = int(args[0])
    except (IndexError, ValueError):
        await send(update, "Usage: <code>/resetuser 1042</code>")
        return
    if customer_id < 1:
        await send(update, "Usage: <code>/resetuser 1042</code>")
        return

    found = await api.get_customer(customer_id)

    agreed = await confirm(
        update,
        lines(
            title("Confirm this reset"),
            "",
            f"This clears every hardware lock on {title(found['username'])} (id {found['id']}).",
            "They will be able to bind a new machine on their next launch.",
        ),
        confirm_label="Reset machine",
    )
    if not agreed:
        return

    result = await api.reset_by_customer(customer_id)
    cleared = result.get("cleared", 0)

    await send(
        update,
        lines(
            title("Machine reset"),
            f"Cleared {cleared} lock{'' if cleared == 1 else 's'} for {title(found['username'])}.",
        ),
    )

    who = update.effective_user.username or update.effective_user.id
    await context.application.bot_data["log"](
        f"{esc(who)} reset HWID for {esc(found['username'])} (id {customer_id})"
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    b = await context.application.bot_data["api"].balance()
    topup = b.get("topup") or {}

    await send(
        update,
        lines(
            title("Balance"),
            "",
            pair("Available", money(b.get("balance_usd"))),
            pair("Your discount", f"{b.get('discount_pct')}%"),
            "",
            f"Top up between {money(topup['min_usd'])} and {money(topup['max_usd'])} "
            f"at {esc(topup['url'])}"
            if topup
            else "Top up from the partner panel.",
        ),
    )


async def ledger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    try:
        limit = int(args[0]) if args else 10
    except ValueError:
        limit = -1
    if limit < 1 or limit > 25:
        await send(update, "Limit must be a whole number between 1 and 25.")
        return

    result = await context.application.bot_data["api"].ledger(limit)
    rows = result.get("data") or []

    if not rows:
        await send(update, "Nothing on the ledger yet.")
        return

    body = [title("Ledger"), ""]
    for entry in rows:
        amount = float(entry.get("amount_usd") or 0)
        sign = "+" if amount >= 0 else "−"
        label = KIND_LABEL.get(entry.get("kind"), entry.get("kind"))
        body.append(f"{sign}{money(abs(amount))[1:]} · {title(label)} · {ago(entry.get('created_at'))}")
        body.append(
            f"{esc(entry.get('note') or 'No note')} · balance after "
            f"{money(entry.get('balance_after_usd'))}"
        )
        body.append("")

    await send(update, truncate(lines(*body)))
