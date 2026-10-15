from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telegram import Bot
from telegram.error import TelegramError

from dmarebrandsbot.api import PartnerApi, friendly
from dmarebrandsbot.config import GROUPS, SCOPES, load_config
from dmarebrandsbot.handlers import COMMANDS, MENU

problems = 0


def ok(label: str, detail: str = "") -> None:
    print(f"  PASS  {label}" + (f"  ({detail})" if detail else ""))


def bad(label: str, detail: str = "") -> None:
    global problems
    problems += 1
    print(f"  FAIL  {label}" + (f"  ({detail})" if detail else ""))


async def main() -> int:
    print("\nchecking your .env")
    config = load_config()
    ok("env parsed", f"{len(config.user_scopes)} allowlisted user(s)")

    print("\nchecking the partner API")
    api = PartnerApi(config.api_key, config.api_base)
    try:
        me = await api.me()
        ok("API key works", f"{me.get('username')}, balance ${me.get('balance_usd')}")
    except Exception as err:
        bad("API key rejected", friendly(err))
    finally:
        await api.close()

    print("\nchecking Telegram")
    bot = Bot(config.token)
    try:
        async with bot:
            me = await bot.get_me()
            ok("token works", f"@{me.username}")

            published = await bot.get_my_commands()
            if published:
                ok("command menu published", f"{len(published)} entries")
            else:
                bad("command menu is empty", "run: python scripts/register.py")

            if config.log_chat_id:
                try:
                    await bot.get_chat(config.log_chat_id)
                    ok("log chat reachable", str(config.log_chat_id))
                except TelegramError:
                    bad("log chat unreachable", "the bot must be a member of LOG_CHAT_ID")
    except TelegramError as err:
        bad("token rejected", str(err))

    print("\nchecking permission wiring")
    covered: set[str] = set()
    for scopes in config.user_scopes.values():
        covered.update(scopes)

    for command in COMMANDS:
        if not command.scope:
            ok(f"/{command.name} is open to everyone")
        elif command.scope in covered:
            ok(f"/{command.name} usable", command.scope)
        else:
            bad(f"/{command.name} is unreachable", f"nobody has {command.scope}")

    unknown = sorted(s for s in covered if s not in SCOPES)
    if unknown:
        bad("unknown scopes granted", ", ".join(unknown))

    missing = [c.name for c in COMMANDS if c.name != "start" and c.name not in {m[0] for m in MENU}]
    if missing:
        bad("commands missing from the menu", ", ".join(missing))
    else:
        ok("every command is in the menu")

    print("\nwho can do what")
    for group, scopes in GROUPS.items():
        ids = [
            str(user_id)
            for user_id, granted in config.user_scopes.items()
            if all(scope in granted for scope in scopes)
        ]
        print(f"  {group:<15} {', '.join(ids) if ids else '(none)'}")

    print("\nchat policy")
    if config.allowed_chats:
        print(f"  private chats + groups: {', '.join(str(c) for c in config.allowed_chats)}")
    else:
        print("  private chats only (set ALLOWED_CHATS to allow a group)")
    print(f"  results sent privately: {'yes' if config.private_results else 'no'}")

    print("\nEverything looks good.\n" if problems == 0 else f"\n{problems} problem(s) to fix.\n")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
