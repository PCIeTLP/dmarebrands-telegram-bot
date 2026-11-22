from __future__ import annotations

from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import ago, code, esc, lines, money, pair, title, truncate, until
from ..reply import request_key, send, send_private

STATE_LABEL = {
    "waiting": "Waiting for payment",
    "confirming": "Payment seen, confirming",
    "partially_paid": "Part paid",
    "paid": "Paid, crediting now",
    "credited": "On your balance",
    "expired": "Expired",
    "failed": "Failed",
    "refunded": "Refunded",
}


def payment_text(t: dict, heading: str) -> str:
    pay = t.get("pay") or {}
    state = t.get("state")
    if state in ("waiting", "partially_paid"):
        amount = f"{pay.get('amount') or '?'} {str(pay.get('currency') or '').upper()}"
        detail = lines(
            "",
            f"Send exactly {title(amount)} to",
            code(pay.get("address") or "no address yet"),
            f"Memo or tag: {code(pay['extra_id'])}. The payment needs it." if pay.get("extra_id") else "",
            f"Expires {until(t['expires_at'])}." if t.get("expires_at") else "",
            f"Or pay on the checkout page, with a QR code: {esc(t.get('checkout_url'))}",
        )
    elif state == "credited":
        detail = "\nThe money is on your balance."
    else:
        detail = ""
    return lines(
        title(heading),
        "",
        pair("Amount", money(t.get("amount_usd"))),
        pair("State", STATE_LABEL.get(state, state)),
        pair("Reference", t.get("ref")),
        detail,
    )


async def topup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    args = list(context.args or [])
    try:
        amount = float(args[0]) if args else None
    except ValueError:
        amount = None
    coin = (args[1] if len(args) > 1 else "").strip().lower()

    if amount is None or not coin:
        try:
            result = await api.coins()
        except Exception:
            result = {}
        popular = ", ".join(code(c["code"]) for c in (result.get("data") or []) if c.get("popular"))
        await send(
            update,
            lines(
                f"Usage: {code('/topup 100 usdttrc20')}",
                f"Between {money(result.get('min_usd', 20))} and {money(result.get('max_usd', 10000))}.",
                f"Popular coins: {popular}" if popular else "",
            ),
        )
        return

    t = await api.start_topup(round(amount, 2), coin, key=request_key(update))
    await send_private(
        update,
        context,
        payment_text(t, "Top-up opened"),
        f"Top-up of {money(t.get('amount_usd'))} opened. Payment details sent privately.",
        f"Top-up of {money(t.get('amount_usd'))} opened, but I could not message you the payment details.\n"
        f"Open a chat with me and press <b>Start</b>, then run {code('/topups ' + str(t.get('ref')))} there.",
    )

    user = update.effective_user
    currency = str((t.get("pay") or {}).get("currency") or coin).upper()
    await context.application.bot_data["log"](
        f"{esc(user.username or user.id)} opened a {money(t.get('amount_usd'))} top-up in {esc(currency)}"
    )


async def topups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    ref = ((context.args or [""])[0]).strip().upper()

    if ref:
        t = await api.get_topup(ref)
        await send_private(update, context, payment_text(t, f"Top-up {t.get('ref')}"), "Sent you the top-up in a private message.")
        return

    result = await api.topups(10)
    rows = result.get("data") or []
    if not rows:
        await send(update, f"No top-ups yet. Start one with {code('/topup 100 usdttrc20')}.")
        return

    listed = [
        f"{code(t.get('ref'))} - {money(t.get('amount_usd'))} · {esc(STATE_LABEL.get(t.get('state'), t.get('state')))} · "
        f"{esc(str((t.get('pay') or {}).get('currency') or '').upper())} · {ago(t.get('created_at'))}"
        for t in rows
    ]
    await send_private(
        update,
        context,
        truncate(lines(title("Recent top-ups"), "", *listed)),
        "Sent you your top-ups in a private message.",
    )


def invoice_state(inv: dict) -> str:
    if inv.get("status") == "paid":
        return "Paid"
    if inv.get("stock_locked"):
        return "Keys locked"
    if inv.get("overdue"):
        return "Due"
    return "Unpaid"


def day(value: object) -> str:
    return esc(str(value)[:10]) if value else "?"


def last_day(value: object) -> str:
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00")) - timedelta(seconds=1)
    except ValueError:
        return "?"
    return moment.strftime("%Y-%m-%d")


async def invoices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    number = ((context.args or [""])[0]).strip().upper()

    if number:
        inv = await api.get_invoice(number)
        used = [line for line in inv.get("lines") or [] if line.get("kind") == "usage"]
        listed = (
            "\n".join(
                f"{line.get('qty')} × {esc(line.get('duration') or '')} {esc(line.get('product') or '')} at "
                f"{money(line.get('unit_usd'))} · {money(abs(float(line.get('amount_usd') or 0)))}"
                for line in used
            )
            if used
            else "No keys used in this period."
        )
        await send_private(
            update,
            context,
            truncate(
                lines(
                    title(f"Invoice {inv.get('number')}"),
                    "",
                    pair("Amount", money(inv.get("amount_usd"))),
                    pair("Paid", money(inv.get("paid_usd"))),
                    pair("Still due", money(inv.get("due_usd"))),
                    pair("Period", f"{day(inv.get('period_start'))} to {last_day(inv.get('period_end'))}"),
                    pair("State", invoice_state(inv)),
                    "",
                    listed,
                )
            ),
            "Sent you the invoice in a private message.",
        )
        return

    result = await api.invoices(limit=12)
    rows = result.get("data") or []
    if not rows:
        await send(update, "No invoices yet.")
        return

    listed_rows = [
        f"{code(inv.get('number'))} - {day(inv.get('period_start'))} to {last_day(inv.get('period_end'))} · "
        f"{money(inv.get('amount_usd'))} · {invoice_state(inv)}"
        + (f" · {money(inv.get('due_usd'))} due" if inv.get("status") == "open" else "")
        for inv in rows
    ]
    await send_private(
        update,
        context,
        truncate(lines(title("Invoices"), "", *listed_rows)),
        "Sent you your invoices in a private message.",
    )


async def payinvoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    args = list(context.args or [])
    number = (args[0] if args else "").strip().upper()
    coin = (args[1] if len(args) > 1 else "").strip().lower()
    try:
        amount = float(args[2]) if len(args) > 2 else None
    except ValueError:
        amount = -1.0

    if not number or not coin or (amount is not None and amount <= 0):
        await send(
            update,
            lines(
                f"Usage: {code('/payinvoice INV-202611-K7QD usdttrc20')}",
                "Add an amount, from 20, to pay part of it.",
            ),
        )
        return

    t = await api.pay_invoice(number, coin, key=request_key(update), amount_usd=round(amount, 2) if amount else None)
    await send_private(
        update,
        context,
        payment_text(t, f"Payment for {number}"),
        f"Payment of {money(t.get('amount_usd'))} opened. Payment details sent privately.",
        f"Payment of {money(t.get('amount_usd'))} opened, but I could not message you the payment details.\n"
        f"Open a chat with me and press <b>Start</b>, then run {code('/invoices ' + number)} there.",
    )

    user = update.effective_user
    await context.application.bot_data["log"](
        f"{esc(user.username or user.id)} opened a {money(t.get('amount_usd'))} payment for invoice {esc(number)}"
    )
