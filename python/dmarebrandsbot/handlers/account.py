from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import ago, code, esc, lines, money, pair, title
from ..permissions import describe, scopes_for
from ..reply import send


async def account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    me = await context.application.bot_data["api"].me()
    brand = me.get("brand") or {}
    stats = me.get("stats") or {}

    await send(
        update,
        lines(
            title(f"Partner account: {me.get('username')}"),
            f"Trading as {esc(brand['name'])}" if brand.get("name") else "No brand name set yet.",
            "",
            pair("Balance", money(me.get("balance_usd"))),
            pair("Discount", f"{me.get('discount_pct')}%"),
            pair("Customers", stats.get("customers", 0)),
            pair("Keys in stock", stats.get("keys_unused", 0)),
            pair("Keys active", stats.get("keys_active", 0)),
            pair("Spent all time", money(stats.get("spent_usd"))),
            f"\nStore: {esc(brand['store_url'])}" if brand.get("store_url") else "",
        ),
    )


async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = await context.application.bot_data["api"].plans()
    rows = result.get("data") or []

    if not rows:
        await send(update, "No plans are available right now.")
        return

    body = [title("Plans"), ""]
    for plan in rows:
        body.append(f"{title(plan['product'] + ' · ' + plan['label'])} {code(plan['id'])}")
        body.append(
            f"{plan['days']} days · {money(plan['your_price_usd'])} for you · "
            f"list {money(plan['list_price_usd'])} · you save {money(plan['saving_usd'])}"
        )
        body.append("")

    await send(update, lines(*body))


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    s, week = await asyncio.gather(api.stats(), api.stats_daily(7), return_exceptions=True)
    if isinstance(s, BaseException):
        raise s
    totals = week.get("totals") if isinstance(week, dict) else None
    recent = (
        f"\n{title('Last 7 days')}\n{totals.get('redeemed', 0)} redeemed · {totals.get('new_customers', 0)} new customers · "
        f"{money(totals.get('spent_usd'))} spent · up to {totals.get('peak_players', 0)} players a day"
        if totals
        else ""
    )
    await send(
        update,
        lines(
            title("Stats"),
            "",
            pair("Keys issued", s.get("keys_total", 0)),
            pair("In stock", s.get("keys_unused", 0)),
            pair("Active", s.get("keys_active", 0)),
            pair("Expired", s.get("keys_expired", 0)),
            pair("Customers", s.get("customers", 0)),
            pair("Live customers", s.get("live_customers", 0)),
            pair("Online now", f"{s.get('online_now', 0)} · {s.get('playing_now', 0)} in game"),
            pair("Balance", money(s.get("balance_usd"))),
            pair("Spent all time", money(s.get("spent_usd"))),
            pair("HWID resets (30d)", s.get("hwid_resets_30d", 0)),
            pair("Unread tickets", s.get("tickets_unread", 0)),
            recent,
        ),
    )


async def domains(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = await context.application.bot_data["api"].domains()
    rows = result.get("data") or []
    target = result.get("cname_target")

    if not rows:
        await send(
            update,
            lines(
                "No domains set up yet.",
                "Add one at https://partners.dmarebrands.st/partners/branding",
                f"Point a CNAME at {code(target or 'the target shown in the panel')}.",
            ),
        )
        return

    body = [title("Your domains"), ""]
    for domain in rows:
        state = (
            "Live"
            if domain.get("live")
            else f"Not live yet ({esc(domain.get('status'))} / ssl {esc(domain.get('ssl_status'))})"
        )
        body.append(f"{title(domain['hostname'])} - {esc(domain['kind'])}")
        body.append(state)
        if domain.get("checked_at"):
            body.append(f"Checked {ago(domain['checked_at'])}")
        if domain.get("last_error"):
            body.append(esc(domain["last_error"]))
        body.append("")

    if target:
        body.append(f"CNAME target: {code(target)}")

    await send(update, lines(*body))


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.application.bot_data["config"]
    granted = scopes_for(update.effective_user.id, config.user_scopes)

    await send(
        update,
        lines(
            title("Your access"),
            "",
            f"Telegram user ID: {code(update.effective_user.id)}",
            f"Scopes: {code(describe(granted))}"
            if granted
            else "You are not on this bot's allowlist, so every command will be refused.\n"
            "Ask whoever runs it to add your user ID.",
        ),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from . import COMMANDS

    config = context.application.bot_data["config"]
    granted = scopes_for(update.effective_user.id, config.user_scopes)

    usable = [c for c in COMMANDS if not c.scope or c.scope in granted]
    blocked = [c for c in COMMANDS if c.scope and c.scope not in granted]

    body = [title("Partner bot"), ""]
    if usable:
        body.append(title("You can use"))
        body.extend(
            f"/{c.name}{' ' + esc(c.args) if c.args else ''} - {esc(c.description)}" for c in usable
        )
    if blocked:
        body.append("")
        body.append(title("Not available to you"))
        body.extend(f"/{c.name} - {esc(c.description)}" for c in blocked)

    await send(update, lines(*body))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.application.bot_data["config"]
    granted = scopes_for(update.effective_user.id, config.user_scopes)

    if not granted:
        await send(
            update,
            lines(
                title("Partner bot"),
                "",
                "You are not on the allowlist yet.",
                f"Your Telegram user ID is {code(update.effective_user.id)} - "
                "give that to whoever runs this bot.",
            ),
        )
        return

    await help_command(update, context)
