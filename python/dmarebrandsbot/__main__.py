from __future__ import annotations

import logging

from telegram.error import InvalidToken

from .bot import build
from .config import load_config


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s", level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = load_config()
    application = build(config)

    try:
        application.run_polling(drop_pending_updates=True)
    except InvalidToken:
        print("\nTelegram rejected the token. Check TELEGRAM_TOKEN in your .env.\n")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
