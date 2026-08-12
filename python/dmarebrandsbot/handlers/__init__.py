from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from . import account as account_mod
from . import customers as customers_mod
from . import keys as keys_mod

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    scope: str | None
    run: Handler
    args: str = ""


COMMANDS: tuple[Command, ...] = (
    Command("start", "Get started", None, account_mod.start),
    Command("help", "List every command", None, account_mod.help_command),
    Command("account", "Partner account, brand and headline numbers", "account.read", account_mod.account),
    Command("plans", "Every plan you can buy, with your discounted price", "account.read", account_mod.plans),
    Command("stats", "Keys issued, active, expired and customers", "account.read", account_mod.stats),
    Command("balance", "Partner balance and how to top it up", "billing.read", customers_mod.balance),
    Command("ledger", "Recent movements on the partner balance", "billing.read", customers_mod.ledger, "[limit]"),
    Command(
        "keys",
        "List keys you have issued",
        "keys.read",
        keys_mod.keys,
        "[all|unused|active|expired] [search]",
    ),
    Command("key", "Look up a single key", "keys.read", keys_mod.key, "<code>"),
    Command("buy", "Buy new keys against the partner balance", "keys.buy", keys_mod.buy, "<plan> [count]"),
    Command("refund", "Refund an unredeemed key back to your balance", "keys.refund", keys_mod.refund, "<code>"),
    Command(
        "customers",
        "List the people who redeemed your keys",
        "customers.read",
        customers_mod.customers,
        "[search]",
    ),
    Command("customer", "Look up one customer by id", "customers.read", customers_mod.customer, "<id>"),
    Command(
        "resetkey",
        "Clear a customer's hardware lock, found by key code",
        "hwid.reset",
        customers_mod.resetkey,
        "<code>",
    ),
    Command(
        "resetuser",
        "Clear a customer's hardware lock, found by customer id",
        "hwid.reset",
        customers_mod.resetuser,
        "<id>",
    ),
    Command("domains", "Your white-label domains and whether they are live", "domains.read", account_mod.domains),
    Command("whoami", "Show what this bot will let you do", None, account_mod.whoami),
)

BY_NAME = {command.name: command for command in COMMANDS}

MENU = [(c.name, c.description[:256]) for c in COMMANDS if c.name != "start"]
