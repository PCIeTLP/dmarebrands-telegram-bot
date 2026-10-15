from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any


def esc(value: Any) -> str:
    return (
        str("" if value is None else value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def money(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return f"${number:,.2f}"


def _relative(target_ms: float) -> str:
    diff = target_ms - time.time() * 1000
    future = diff > 0
    mins = round(abs(diff) / 60000)

    if mins < 1:
        return "just now"
    if mins < 60:
        return f"in {mins} min" if future else f"{mins} min ago"

    hours = round(mins / 60)
    if hours < 48:
        return f"in {hours}h" if future else f"{hours}h ago"

    days = round(hours / 24)
    return f"in {days} days" if future else f"{days} days ago"


def ago(value: Any) -> str:
    if not value:
        return "never"
    if isinstance(value, (int, float)):
        return _relative(float(value) * 1000)
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return _relative(parsed.timestamp() * 1000)
    except ValueError:
        return "unknown"


def until(seconds: Any) -> str:
    try:
        number = int(seconds)
    except (TypeError, ValueError):
        return "n/a"
    if number <= 0:
        return "n/a"
    return _relative(number * 1000)


def state_label(state: Any) -> str:
    return {"unused": "in stock", "active": "active", "expired": "expired"}.get(str(state), str(state))


def title(text: Any) -> str:
    return f"<b>{esc(text)}</b>"


def code(text: Any) -> str:
    return f"<code>{esc(text)}</code>"


def lines(*parts: Any) -> str:
    return "\n".join(str(p) for p in parts if p not in (None, "", False))


def clip(text: Any, limit: int) -> str:
    value = str(text or "")
    return f"{value[: limit - 1]}…" if len(value) > limit else value


def pair(label: str, value: Any) -> str:
    return f"{esc(label)}: <b>{esc(value)}</b>"


_TRUNCATED = "\n\n<i>… list truncated</i>"
_TAG = re.compile(r"<(/?)([a-z][\w-]*)[^>]*>", re.IGNORECASE)


def truncate(text: str, limit: int = 3800) -> str:
    if len(text) <= limit:
        return text
    room = limit - len(_TRUNCATED)
    line = text.rfind("\n", 0, room + 1)
    kept = text[:line] if line > room / 2 else re.sub(r"<[^>]*$|&[#\w]*$", "", text[:room])
    return _close_tags(kept) + _TRUNCATED


def _close_tags(html: str) -> str:
    still_open: list[str] = []
    for closing, name in _TAG.findall(html):
        if not closing:
            still_open.append(name)
        elif still_open:
            still_open.pop()
    return html + "".join(f"</{name}>" for name in reversed(still_open))
