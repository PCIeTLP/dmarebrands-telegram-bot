from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

TOKEN_RE = re.compile(r"^\d{6,}:[A-Za-z0-9_-]{30,}$")
USER_ID_RE = re.compile(r"^\d{1,19}$")
CHAT_ID_RE = re.compile(r"^-?\d{1,19}$")

SCOPES = (
    "account.read",
    "billing.read",
    "keys.read",
    "keys.buy",
    "keys.refund",
    "customers.read",
    "hwid.reset",
    "domains.read",
)

GROUPS: dict[str, tuple[str, ...]] = {
    "USERS_ADMIN": SCOPES,
    "USERS_KEYS": ("account.read", "keys.read", "keys.buy", "keys.refund", "customers.read"),
    "USERS_HWID": ("hwid.reset", "keys.read", "customers.read"),
    "USERS_BILLING": ("account.read", "billing.read"),
    "USERS_READ": ("account.read", "keys.read", "customers.read", "domains.read"),
}

TOKEN_PREFIX = "dmarebrands_live_"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    token: str
    api_key: str
    api_base: str
    user_scopes: dict[int, frozenset[str]] = field(default_factory=dict)
    allowed_chats: frozenset[int] = frozenset()
    private_results: bool = True
    log_chat_id: int | None = None


def _required(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise ConfigError(f"{name} is missing from your .env")
    return value


def _id_list(name: str, pattern: re.Pattern[str], label: str) -> list[int]:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return []
    parts = [p for p in re.split(r"[,\s]+", raw) if p]
    bad = [p for p in parts if not pattern.match(p)]
    if bad:
        raise ConfigError(f"{name} contains invalid {label}: {', '.join(bad)}")
    return [int(p) for p in parts]


def _build_user_scopes() -> dict[int, frozenset[str]]:
    collected: dict[int, set[str]] = {}
    total = 0

    for env_name, scopes in GROUPS.items():
        for user_id in _id_list(env_name, USER_ID_RE, "Telegram user IDs"):
            total += 1
            collected.setdefault(user_id, set()).update(scopes)

    if total == 0:
        raise ConfigError(
            "No users configured. Set at least one of USERS_ADMIN, USERS_KEYS, USERS_HWID, "
            "USERS_BILLING or USERS_READ.\n"
            "Message @userinfobot on Telegram to find your numeric user ID."
        )

    return {user_id: frozenset(scopes) for user_id, scopes in collected.items()}


def _load() -> Config:
    base = (os.environ.get("DMAREBRANDS_API_BASE") or "https://api.dmarebrands.st/v1").strip()
    parsed = urlparse(base)
    if not parsed.scheme or not parsed.netloc:
        raise ConfigError(f"DMAREBRANDS_API_BASE is not a valid URL: {base!r}")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ConfigError("DMAREBRANDS_API_BASE must use https so your API key is never sent in the clear.")

    api_key = _required("DMAREBRANDS_API_KEY")
    if not api_key.startswith(TOKEN_PREFIX):
        raise ConfigError(
            f"DMAREBRANDS_API_KEY does not look right. Partner keys start with {TOKEN_PREFIX!r}. "
            "Create one at https://partners.dmarebrands.st/partners/api"
        )

    token = _required("TELEGRAM_TOKEN")
    if not TOKEN_RE.match(token):
        raise ConfigError(
            'TELEGRAM_TOKEN does not look right. BotFather gives you something like "123456789:AAF...". '
            "Check you copied all of it."
        )

    log_chat = (os.environ.get("LOG_CHAT_ID") or "").strip()
    if log_chat and not CHAT_ID_RE.match(log_chat):
        raise ConfigError(f"LOG_CHAT_ID must be a numeric chat ID, got {log_chat!r}")

    return Config(
        token=token,
        api_key=api_key,
        api_base=base.rstrip("/"),
        user_scopes=_build_user_scopes(),
        allowed_chats=frozenset(_id_list("ALLOWED_CHATS", CHAT_ID_RE, "chat IDs")),
        private_results=(os.environ.get("PRIVATE_RESULTS") or "true").lower() != "false",
        log_chat_id=int(log_chat) if log_chat else None,
    )


def load_config() -> Config:
    try:
        return _load()
    except ConfigError as err:
        print(f"\nConfiguration problem: {err}\n", file=sys.stderr)
        print("Copy .env.example to .env and fill it in, then try again.\n", file=sys.stderr)
        raise SystemExit(1) from err
