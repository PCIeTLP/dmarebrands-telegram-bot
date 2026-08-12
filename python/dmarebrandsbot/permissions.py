from __future__ import annotations

from telegram import Chat

from .config import SCOPES, Config


def scopes_for(user_id: int | None, user_scopes: dict[int, frozenset[str]]) -> frozenset[str]:
    if user_id is None:
        return frozenset()
    return user_scopes.get(int(user_id), frozenset())


def allows(granted: frozenset[str], needed: str) -> bool:
    return needed in granted


def describe(granted: frozenset[str]) -> str:
    if not granted:
        return "none"
    return ", ".join(scope for scope in SCOPES if scope in granted)


def denied_message(needed: str) -> str:
    return (
        "You are not allowed to do that. This command needs the "
        f"<code>{needed}</code> scope, which your account does not have."
    )


def chat_allowed(chat: Chat | None, config: Config) -> bool:
    if chat is None:
        return False
    if chat.type == Chat.PRIVATE:
        return True
    return chat.id in config.allowed_chats
