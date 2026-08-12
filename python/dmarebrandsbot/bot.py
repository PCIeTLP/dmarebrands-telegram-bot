from __future__ import annotations

import logging

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

from .api import ApiError, PartnerApi, friendly
from .config import Config
from .formatting import esc, lines, title
from .handlers import COMMANDS, MENU, Command
from .permissions import chat_allowed, denied_message, scopes_for
from .reply import handle_callback, send

log = logging.getLogger("dmarebrandsbot")


def build(config: Config) -> Application:
    api = PartnerApi(config.api_key, config.api_base)

    async def log_action(text: str) -> None:
        if not config.log_chat_id:
            return
        try:
            await application.bot.send_message(config.log_chat_id, text, parse_mode=ParseMode.HTML)
        except TelegramError:
            pass

    async def post_init(app: Application) -> None:
        try:
            me = await api.me()
            log.info(
                "Partner API connected as %s · balance $%s", me.get("username"), me.get("balance_usd")
            )
        except Exception as err:
            log.error("The partner API rejected the bot's key: %s", friendly(err))
            log.error("Fix DMAREBRANDS_API_KEY in your .env, then restart.")

        published = await app.bot.get_my_commands()
        if published:
            log.info("Command menu has %d entries", len(published))
        else:
            log.warning("Command menu is empty. Run: python scripts/register.py")

        log.info(
            "Serving %d commands to %d allowlisted user(s)", len(COMMANDS), len(config.user_scopes)
        )
        if not config.allowed_chats:
            log.info("Private chats only. Set ALLOWED_CHATS to use it in a group.")

    async def post_shutdown(app: Application) -> None:
        await api.close()

    application = (
        ApplicationBuilder()
        .token(config.token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.bot_data["config"] = config
    application.bot_data["api"] = api
    application.bot_data["log"] = log_action

    for command in COMMANDS:
        application.add_handler(CommandHandler(command.name, _wrap(command)))

    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(_on_error)

    return application


def _wrap(command: Command):
    async def runner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        config = context.application.bot_data["config"]

        if not chat_allowed(update.effective_chat, config):
            await send(
                update,
                "This bot is not set up for this chat. Message me privately, or ask the owner "
                "to add this chat to ALLOWED_CHATS.",
            )
            return

        granted = scopes_for(update.effective_user.id if update.effective_user else None, config.user_scopes)

        if command.scope and command.scope not in granted:
            await send(update, denied_message(command.scope))
            return

        await command.run(update, context)

    return runner


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    message = friendly(err)
    detail = ""

    if isinstance(err, ApiError) and err.request_id:
        detail = f"\nRequest id: <code>{esc(err.request_id)}</code>"
    if not isinstance(err, ApiError):
        log.exception("command failed", exc_info=err)

    if isinstance(update, Update) and update.effective_message:
        try:
            await send(update, lines(title("That did not work"), esc(message) + detail))
        except TelegramError:
            pass


def menu_commands() -> list[BotCommand]:
    return [BotCommand(name, description) for name, description in MENU]
