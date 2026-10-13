from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

CONFIRM_TIMEOUT_SECONDS = 60
NO_PRIVATE_CHAT = (
    "I could not message you privately, so I am not posting this in the group.\n"
    "Open a chat with me and press <b>Start</b>, then run the command again."
)


@dataclass
class Pending:
    user_id: int
    future: asyncio.Future


_pending: dict[str, Pending] = {}
_prompt_ids = itertools.count(int(time.time() * 1000))


async def send(update: Update, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    return await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )


def _keep_private(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return update.effective_chat.type != "private" and context.application.bot_data["config"].private_results


async def _send_direct(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    note: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    fail_note: str = NO_PRIVATE_CHAT,
) -> Message | None:
    """Send text to the user's private chat and leave note in the group.

    Returns the private message, or None after posting fail_note when the bot cannot
    message the user.
    """
    try:
        message = await context.bot.send_message(
            update.effective_user.id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
    except TelegramError:
        await send(update, fail_note)
        return None
    try:
        await send(update, note)
    except TelegramError:
        pass  # The private message is already out, so losing the group note must not undo it.
    return message


async def send_private(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    public_note: str,
    fail_note: str = NO_PRIVATE_CHAT,
):
    """fail_note replaces the "run the command again" advice for results of something already done."""
    if not _keep_private(update, context):
        return await send(update, text)
    return await _send_direct(update, context, text, public_note, fail_note=fail_note)


def confirm_keyboard(token: str, confirm_label: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(confirm_label, callback_data=f"ok:{token}"),
            InlineKeyboardButton("Cancel", callback_data=f"no:{token}"),
        ]]
    )


async def confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    confirm_label: str,
    *,
    sensitive: bool = False,
) -> bool:
    user_id = update.effective_user.id
    token = f"{user_id}:{next(_prompt_ids)}"
    privately = sensitive and _keep_private(update, context)
    keyboard = confirm_keyboard(token, confirm_label)

    # Listen before the prompt goes out, so a quick press is not turned away as expired.
    future: asyncio.Future = asyncio.get_running_loop().create_future()
    _pending[token] = Pending(user_id=user_id, future=future)
    try:
        if privately:
            message = await _send_direct(
                update, context, text, "Sent you a confirmation in a private message.", keyboard
            )
        else:
            message = await send(update, text, keyboard)
        if message is None:
            return False

        try:
            agreed = await asyncio.wait_for(future, timeout=CONFIRM_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            await _mark(message, text, "Timed out")
            return False
        if not agreed and privately:
            await _mark(message, text, "Cancelled")
        return agreed
    finally:
        _pending.pop(token, None)


async def _mark(message: Message, text: str, outcome: str) -> None:
    """Show the outcome on the prompt itself, where the user acted."""
    try:
        await message.edit_text(f"{text}\n\n<i>{outcome}. Nothing was done.</i>", parse_mode=ParseMode.HTML)
    except TelegramError:
        pass


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    verb, _, token = data.partition(":")
    waiting = _pending.get(token)

    if waiting is None:
        await query.answer("That prompt has expired. Run the command again.")
        return
    if waiting.user_id != query.from_user.id:
        await query.answer("That confirmation is not yours.")
        return

    # Settle first, so the waiting command does not sit behind these two Telegram calls.
    if not waiting.future.done():
        waiting.future.set_result(verb == "ok")
    # The press already counted, so a failure here must not tell the user it did not work.
    try:
        await query.answer()
    except TelegramError:
        pass
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except TelegramError:
        pass


def clear_pending() -> None:
    for entry in _pending.values():
        if not entry.future.done():
            entry.future.cancel()
    _pending.clear()
