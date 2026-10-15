from __future__ import annotations

from typing import Any, Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import ago, code, esc, lines, money, pair, state_label, title, truncate, until
from ..reply import confirm, request_key, send, send_private

KIND_LABEL = {
    "topup": "Top-up",
    "purchase": "Keys bought",
    "refund": "Refund",
    "adjust": "Adjustment",
}


def product_lines(customer: dict) -> str:
    rows = customer.get("products") or []
    if not rows:
        return "none"
    return "\n".join(
        f"{esc(p['product'])} · "
        + (f"active until {until(p['expires_at'])}" if p.get("active") else "expired")
        for p in rows
    )


def machine_lines(customer: dict) -> str:
    machines = customer.get("machines") or []
    if not machines:
        return "Nothing bound right now."
    return "\n".join(
        f"{esc(m['scope'])} - bound {ago(m.get('bound_at'))} · last seen {ago(m.get('last_seen'))}"
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
            f"{title(customer['username'])} (id {customer['id']}) · {state} · "
            f"{customer.get('keys', 0)} key(s){bound}"
        )
    body.extend(["", f"<i>{len(rows)} shown</i>"])

    await send_private(
        update, context, truncate(lines(*body)), "Sent you the customer list in a private message."
    )


USAGE_CUSTOMER = (
    "Usage: <code>/customer 1042</code>, <code>/customer theirname</code> or "
    "<code>/customer DMA-XXXX-XXXX-XXXX-XXXX</code>"
)


async def customer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ref = (context.args or [""])[0].strip()
    if not ref:
        await send(update, USAGE_CUSTOMER)
        return

    found = await context.application.bot_data["api"].get_customer(ref)

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
            title("Products"),
            product_lines(found),
            "",
            title("Machines"),
            machine_lines(found),
        ),
        "Sent you the customer details in a private message.",
    )


async def _confirm_reset(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    customer: dict,
    reset: Callable[[], Awaitable[dict[str, Any]]],
) -> bool:
    agreed = await confirm(
        update,
        context,
        lines(
            title("Confirm this reset"),
            "",
            f"This clears every hardware lock on {title(customer['username'])} (id {customer['id']}).",
            "They will be able to bind a new machine on their next launch.",
        ),
        confirm_label="Reset machine",
        sensitive=True,
    )
    if not agreed:
        return False

    result = await reset()
    cleared = result.get("cleared", 0)

    await send_private(
        update,
        context,
        lines(
            title("Machine reset"),
            f"Cleared {cleared} lock{'' if cleared == 1 else 's'} for {title(customer['username'])}.",
        ),
        "Machine reset. Details sent privately.",
        fail_note="Machine reset. I could not message you the details privately.",
    )
    return True


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

    if not await _confirm_reset(update, context, holder, lambda: api.reset_by_key(wanted, key=request_key(update))):
        return

    who = update.effective_user.username or update.effective_user.id
    await context.application.bot_data["log"](
        f"{esc(who)} reset HWID for {esc(holder['username'])} via key {code(wanted)}"
    )


async def resetuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    ref = (context.args or [""])[0].strip()
    if not ref:
        await send(
            update,
            "Usage: <code>/resetuser 1042</code>, <code>/resetuser theirname</code> or "
            "<code>/resetuser DMA-XXXX-XXXX-XXXX-XXXX</code>",
        )
        return

    found = await api.get_customer(ref)

    if not await _confirm_reset(update, context, found, lambda: api.reset_by_customer(found["id"], key=request_key(update))):
        return

    who = update.effective_user.username or update.effective_user.id
    await context.application.bot_data["log"](
        f"{esc(who)} reset HWID for {esc(found['username'])} (id {found['id']})"
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


async def customerkeys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ref = ((context.args or [""])[0]).strip()
    if not ref:
        await send(update, "Usage: <code>/customerkeys theirname</code> or <code>/customerkeys DMA-XXXX-XXXX-XXXX-XXXX</code>")
        return

    result = await context.application.bot_data["api"].customer_keys(ref)
    rows = result.get("data") or []
    who = (result.get("customer") or {}).get("username") or ref

    if not rows:
        await send(update, f"{esc(who)} has no keys from you.")
        return

    listed = []
    for k in rows:
        expiry = f" · expires {until(k['expires_at'])}" if k.get("expires_at") else ""
        listed.append(f"{code(k.get('code'))} - {state_label(k.get('state'))} · {k.get('days')}d {esc(k.get('product'))}{expiry}")

    plural = "" if len(rows) == 1 else "s"
    body = lines(title(f"Keys for {who}"), "", *listed, "", f"<i>{len(rows)} key{plural}</i>")
    await send_private(update, context, truncate(body), "Sent you their keys in a private message.")


async def online(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = await context.application.bot_data["api"].online()
    rows = result.get("data") or []

    if not rows:
        await send(update, "Nobody is online right now.")
        return

    listed = []
    for c in rows:
        playing = c.get("playing") or []
        menu = c.get("menu") or []
        if playing:
            doing = f"in {esc(', '.join(playing))}"
        else:
            doing = f"menu open ({esc(', '.join(menu))})" if menu else "menu open"
        listed.append(f"{title(c.get('username'))} · {doing} · since {ago(c.get('online_since'))}")

    body = lines(title(f"Online now ({len(rows)})"), "", *listed, "", f"<i>{result.get('playing', 0)} in game</i>")
    await send_private(update, context, truncate(body), "Sent you who is online in a private message.")
