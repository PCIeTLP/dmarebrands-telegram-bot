from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import ago, code, esc, lines, pair, title, truncate
from ..reply import send

STATUSES = ("all", "open", "answered", "resolved", "closed")


def line(t: dict[str, Any]) -> str:
    unread = " · unread reply" if t.get("unread") else ""
    return lines(
        f"{code(t.get('ref'))} {esc(t.get('subject'))}",
        f"{t.get('status')} · {t.get('priority')} · {t.get('messages')} message(s){unread}",
        f"Last activity {ago(t.get('last_message_at'))}",
    )


async def tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    wanted = ((context.args or ["all"])[0]).strip().lower()
    if wanted not in STATUSES:
        await send(update, f"Status must be one of: {', '.join(STATUSES)}")
        return

    result = await context.application.bot_data["api"].list_tickets(status=wanted)
    rows = result.get("tickets") or []
    if not rows:
        await send(update, "No tickets match that.")
        return

    await send(
        update,
        truncate(lines(title(f"Tickets ({len(rows)})"), "", "\n\n".join(line(t) for t in rows))),
    )


async def ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ref = ((context.args or [""])[0]).strip().upper()
    if not ref:
        await send(update, f"Usage: {code('/ticket TKT-8H2QMD')}")
        return

    t = await context.application.bot_data["api"].get_ticket(ref)
    thread = "\n\n".join(
        f"{title('You' if m.get('role') == 'partner' else 'Support')} {ago(m.get('created_at'))}\n{esc(m.get('body'))}"
        for m in (t.get("thread") or [])
    )

    await send(
        update,
        truncate(
            lines(
                title(f"{t.get('ref')} {esc(t.get('subject'))}"),
                f"{t.get('status')} · {t.get('priority')} · {t.get('category')}",
                "",
                thread or "No messages yet.",
            )
        ),
    )


async def newticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = " ".join(context.args or [])
    subject, _, body = raw.partition("|")

    if not subject.strip() or not body.strip():
        await send(
            update,
            f"Usage: {code('/newticket Key not activating | They redeemed it but nothing happened')}",
        )
        return

    made = await context.application.bot_data["api"].create_ticket(
        subject=subject.strip(), body=body.strip()
    )
    await send(
        update,
        lines(
            title("Ticket opened"),
            f"{code(made.get('ref'))} {esc(made.get('subject') or '')}",
            f"Read it with {code('/ticket ' + str(made.get('ref')))}",
        ),
    )


async def replyticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    ref = (args[0] if args else "").strip().upper()
    body = " ".join(args[1:]).strip()
    if not ref or not body:
        await send(update, f"Usage: {code('/replyticket TKT-8H2QMD One more thing')}")
        return

    t = await context.application.bot_data["api"].reply_ticket(ref, body)
    await send(
        update,
        lines(title("Reply sent"), pair("Ticket", t.get("ref") or ref), pair("Messages", t.get("messages", "more"))),
    )


async def closeticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ref = ((context.args or [""])[0]).strip().upper()
    if not ref:
        await send(update, f"Usage: {code('/closeticket TKT-8H2QMD')}")
        return

    closed = await context.application.bot_data["api"].close_ticket(ref)
    await send(update, lines(title("Ticket closed"), pair("Ticket", closed.get("ref") or ref)))


async def activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    try:
        wanted = int(args[0])
    except (IndexError, ValueError):
        wanted = 15
    limit = max(1, min(wanted, 200))

    result = await context.application.bot_data["api"].activity(limit=limit)
    events = result.get("events") or []
    if not events:
        await send(update, "Nothing has happened yet.")
        return

    listed = []
    for e in events:
        actor = (e.get("actor") or {}).get("username")
        target = (e.get("target") or {}).get("username")
        who = f" by {esc(actor)}" if actor else ""
        about = f" · {esc(target)}" if target else ""
        listed.append(f"{code(e.get('action'))}{who}{about}\n{ago(e.get('created_at'))}")

    await send(update, truncate(lines(title("Recent activity"), "", "\n\n".join(listed))))
