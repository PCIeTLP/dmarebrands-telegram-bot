from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telegram import Bot
from telegram.error import InvalidToken, TelegramError

from dmarebrandsbot.bot import menu_commands
from dmarebrandsbot.config import load_config


async def main() -> int:
    clear = "--clear" in sys.argv
    config = load_config()
    bot = Bot(config.token)

    try:
        async with bot:
            if clear:
                await bot.delete_my_commands()
                print("Removed the command menu.")
                return 0

            menu = menu_commands()
            await bot.set_my_commands(menu)
            print(f"Published {len(menu)} commands to the Telegram menu:")
            for entry in menu:
                print(f"  /{entry.command}")
            print("\nThe menu is a hint only. Permissions are still checked on every command.")
            return 0
    except InvalidToken:
        print("\nCould not update the menu. Telegram rejected the token. Check TELEGRAM_TOKEN.")
        return 1
    except TelegramError as err:
        print(f"\nCould not update the menu. {err}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
