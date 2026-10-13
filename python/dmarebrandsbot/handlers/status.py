from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import esc, lines, pair, title
from ..reply import send

HEADLINE = {
    "undetected": "Up and safe to use",
    "updating": "Updating",
    "offline": "Temporarily offline",
    "detected": "Detected, tell people to stop",
    "discontinued": "Discontinued",
}


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    wanted = (context.args or [""])[0].strip() or None
    result = await context.application.bot_data["api"].status(wanted)
    rows = result.get("products") or []

    if not rows:
        await send(update, "No products came back.")
        return

    blocks = []
    for p in rows:
        head = HEADLINE.get(p.get("status"), p.get("status"))
        blocks.append(
            lines(
                title(f"{p.get('label') or ''}: {head}"),
                "In beta." if p.get("beta") else "",
                "Keys are frozen, so nobody is losing time." if p.get("frozen") else "",
                "" if p.get("sellable") else "This one cannot be sold any more.",
                esc(p["message"]) if p.get("message") else "",
                pair("Changed", p.get("updated_at") or "unknown"),
            )
        )

    await send(update, "\n\n".join(blocks))


async def updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    wanted = (context.args or [""])[0].strip() or None
    result = await context.application.bot_data["api"].updates(wanted)
    build = result.get("current_build")
    notes = (result.get("updates") or [])[:5]

    body = [
        title(f"Game updates · {result.get('game') or wanted or 'rust'}"),
        pair("Current build", build["buildid"]) if build else "No build information yet.",
        pair("Seen", build["at"]) if build and build.get("at") else "",
        pair("Usual gap", f"{result['average_gap_days']} days") if result.get("average_gap_days") else "",
    ]
    if notes:
        body.append("")
        body.append(title("Recent notes"))
        body.extend(f"{esc(n['title'])}\n{esc(n['url'])}" for n in notes)

    await send(update, lines(*body))
