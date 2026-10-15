from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import ago, code, esc, lines, pair, title, truncate
from ..reply import request_key, send, send_file, send_private

REASON_LABEL = {
    "chargeback": "Chargeback",
    "dispute": "Payment dispute",
    "fraud": "Fraud report",
    "other": "Something else",
}

STATUS_LABEL = {
    "pending": "Waiting for approval",
    "approved": "Ready to download",
    "declined": "Declined",
}

ATTACH_LIMIT = 20 * 1024 * 1024


def found(summary: dict) -> str:
    return lines(
        f"{summary.get('website_sign_ins', 0)} website sign-ins · {summary.get('loader_sign_ins', 0)} loader sign-ins",
        f"{summary.get('downloads', 0)} downloads · {summary.get('game_sessions', 0)} game sessions",
        f"{summary.get('ip_addresses', 0)} IP addresses · {summary.get('machines', 0)} machines · "
        f"{summary.get('active_days', 0)} active days",
        f"First use {ago(summary['first_use'])} · last seen {ago(summary.get('last_seen'))}"
        if summary.get("first_use")
        else "",
    )


def status_text(r: dict) -> str:
    declined = f"\n{esc(r['decline_reason'])}" if r.get("status") == "declined" and r.get("decline_reason") else ""
    summary = f"\n{title('What we found')}\n{found(r['summary'])}" if r.get("summary") else ""
    return lines(
        title(f"Account info {r.get('ref')}"),
        "",
        pair("Status", STATUS_LABEL.get(r.get("status"), r.get("status"))),
        pair("Customer", (r.get("customer") or {}).get("username") or "unknown"),
        pair("Key", r.get("key")),
        pair("Reason", REASON_LABEL.get(r.get("reason"), r.get("reason"))),
        pair("Your reference", r["reference"]) if r.get("reference") else "",
        pair("Asked", ago(r.get("created_at"))),
        declined,
        summary,
    )


async def accountinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    ref = ((context.args or [""])[0]).strip().upper()

    if not ref:
        result = await api.list_account_info(limit=15)
        rows = result.get("data") or []
        if not rows:
            await send(
                update,
                f"No requests yet. Ask for one with {code('/requestinfo DMA-XXXX-XXXX-XXXX-XXXX chargeback')}.",
            )
            return
        blocks = [
            lines(
                f"{code(r.get('ref'))} {title((r.get('customer') or {}).get('username') or 'unknown')} · {code(r.get('key'))}",
                f"{esc(REASON_LABEL.get(r.get('reason'), r.get('reason')))} · "
                f"{esc(STATUS_LABEL.get(r.get('status'), r.get('status')))} · {ago(r.get('created_at'))}",
            )
            for r in rows
        ]
        await send_private(
            update,
            context,
            truncate(lines(title(f"Account info requests ({len(rows)})"), "", "\n\n".join(blocks))),
            "Sent you your requests in a private message.",
        )
        return

    r = await api.get_account_info(ref)
    text = status_text(r)
    download = r.get("download")

    if r.get("status") != "approved" or not download:
        await send_private(update, context, text, "Sent you the request in a private message.")
        return

    if int(download.get("bytes") or 0) > ATTACH_LIMIT:
        await send_private(
            update,
            context,
            lines(text, "", "The zip is too big to send here. Download it from the ticket in the partner panel."),
            "Sent you the request in a private message.",
        )
        return

    pack = await api.download_account_info(ref)
    caption = truncate(lines(text, "", f"SHA-256 {code(pack.get('sha256') or download.get('sha256'))}"), 1000)
    await send_file(update, context, pack["data"], pack["name"], caption, "Sent you the zip in a private message.")


async def requestinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = " ".join(context.args or [])
    head, _, note = raw.partition("|")
    parts = head.split()
    key = parts[0] if parts else ""
    reason = parts[1].lower() if len(parts) > 1 else ""
    reference = parts[2] if len(parts) > 2 else None

    if not key or reason not in REASON_LABEL:
        await send(
            update,
            lines(
                f"Usage: {code('/requestinfo DMA-XXXX-XXXX-XXXX-XXXX chargeback dp_12345 | anything we should know')}",
                "The reason is chargeback, dispute, fraud or other. The reference and note are optional.",
            ),
        )
        return

    made = await context.application.bot_data["api"].request_account_info(
        code=key,
        reason=reason,
        reference=reference,
        note=note.strip() or None,
        key=request_key(update),
    )
    who = (made.get("customer") or {}).get("username") or "unknown"

    await send(
        update,
        lines(
            title("Request sent"),
            f"We check every request before the zip is made. Check on it with {code('/accountinfo ' + str(made.get('ref')))}.",
            f"Our replies show up in {code('/ticket ' + str(made.get('ref')))}.",
            "",
            pair("Reference", made.get("ref")),
            pair("Customer", who),
        ),
    )

    user = update.effective_user
    await context.application.bot_data["log"](
        f"{esc(user.username or user.id)} asked for account info on {esc(who)} ({code(made.get('ref'))})"
    )
