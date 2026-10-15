from __future__ import annotations

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
