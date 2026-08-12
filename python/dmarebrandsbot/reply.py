from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

CONFIRM_TIMEOUT_SECONDS = 60


@dataclass
class Pending:
    user_id: int
    future: asyncio.Future


_pending: dict[str, Pending] = {}


async def send(update: Update, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    return await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )


async def send_private(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, public_note: str):
    config = context.application.bot_data["config"]
    is_private = update.effective_chat.type == "private"

    if is_private or not config.private_results:
        return await send(update, text)

    try:
        await context.bot.send_message(
            update.effective_user.id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return await send(update, public_note)
    except TelegramError:
        return await send(
            update,
            "I could not message you privately, so I am not posting this in the group.\n"
            "Open a chat with me and press <b>Start</b>, then run the command again.",
        )


def confirm_keyboard(token: str, confirm_label: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(confirm_label, callback_data=f"ok:{token}"),
            InlineKeyboardButton("Cancel", callback_data=f"no:{token}"),
        ]]
    )


async def confirm(update: Update, text: str, confirm_label: str) -> bool:
    user_id = update.effective_user.id
    token = f"{user_id}:{int(time.time() * 1000)}"
    message = await send(update, text, confirm_keyboard(token, confirm_label))

    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    _pending[token] = Pending(user_id=user_id, future=future)

    try:
        return await asyncio.wait_for(future, timeout=CONFIRM_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        try:
            await message.edit_text(
                f"{text}\n\n<i>Timed out. Nothing was done.</i>", parse_mode=ParseMode.HTML
            )
        except TelegramError:
            pass
        return False
    finally:
        _pending.pop(token, None)


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

    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except TelegramError:
        pass

    if not waiting.future.done():
        waiting.future.set_result(verb == "ok")


def clear_pending() -> None:
    for entry in _pending.values():
        if not entry.future.done():
            entry.future.cancel()
    _pending.clear()
