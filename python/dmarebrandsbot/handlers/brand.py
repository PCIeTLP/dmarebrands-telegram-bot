from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import code, lines, pair, title
from ..reply import request_key, send

BOOLS = {"true": True, "on": True, "yes": True, "false": False, "off": False, "no": False}
TEXT_FIELDS = ("name", "primary", "accent", "store_url")
FLAG_FIELDS = ("public_features", "public_guide")


def link_line(label: str, url: str | None, is_public: bool) -> str:
    if not url:
        return pair(label, "not until your menu domain is live")
    state = "public" if is_public else "sign in required"
    return pair(label, f"{state}\n{url}")


def view(b: dict[str, Any]) -> str:
    return lines(
        title(b.get("name") or "No brand name set"),
        "",
        pair("Brand colour", b.get("primary") or "not set"),
        pair("Second colour", b.get("accent") or "not set"),
        pair("Logo", "uploaded" if b.get("has_logo") else "none"),
        pair("Store link", b.get("store_url") or "not set"),
        "",
        link_line("Features", b.get("features_url"), bool(b.get("public_features"))),
        link_line("Setup guide", b.get("guide_url"), bool(b.get("public_guide"))),
    )


async def brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send(update, view(await context.application.bot_data["api"].brand()))


async def setbrand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.application.bot_data["api"]
    args = context.args or []
    field = (args[0] if args else "").strip().lower()
    value = " ".join(args[1:]).strip()

    if not field:
        await send(
            update,
            lines(
                "Usage:",
                code("/setbrand name Your Brand"),
                code("/setbrand primary #7c5cff"),
                code("/setbrand store_url https://yourbrand.com/store"),
                code("/setbrand public_guide on"),
                "",
                f"Fields: {', '.join(TEXT_FIELDS + FLAG_FIELDS)}",
            ),
        )
        return

    if field in FLAG_FIELDS:
        flag = BOOLS.get(value.lower())
        if flag is None:
            await send(update, f"Say on or off, for example {code(f'/setbrand {field} on')}")
            return
        await send(update, view(await api.update_brand({field: flag}, key=request_key(update))))
        return

    if field not in TEXT_FIELDS:
        await send(update, f"Unknown field. Try one of: {', '.join(TEXT_FIELDS + FLAG_FIELDS)}")
        return

    patch = {field: None if value == "" or value.lower() == "clear" else value}
    await send(update, view(await api.update_brand(patch, key=request_key(update))))
