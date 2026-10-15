from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from . import account as account_mod
from . import accountinfo as accountinfo_mod
from . import billing as billing_mod
from . import customers as customers_mod
from . import keys as keys_mod
from . import status as status_mod
from . import brand as brand_mod
from . import support as support_mod
from . import webhooks as webhooks_mod

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
        "topup",
        "Add money to the partner balance with crypto",
        "billing.topup",
        billing_mod.topup,
        "<amount> <coin>",
    ),
    Command(
        "topups",
        "Your recent top-ups, or one of them by reference",
        "billing.read",
        billing_mod.topups,
        "[ref]",
    ),
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
    Command("redemptions", "The latest keys your customers redeemed", "keys.read", keys_mod.redemptions, "[limit]"),
    Command(
        "customers",
        "List the people who redeemed your keys",
        "customers.read",
        customers_mod.customers,
        "[search]",
    ),
    Command(
        "customer",
        "Look up one customer by id, username or a key they redeemed",
        "customers.read",
        customers_mod.customer,
        "<id|username|key>",
    ),
    Command(
        "customerkeys",
        "Every key you sold one customer",
        "customers.read",
        customers_mod.customerkeys,
        "<id|username|key>",
    ),
    Command("online", "Your customers who are online right now", "customers.read", customers_mod.online),
    Command(
        "resetkey",
        "Clear a customer's hardware lock, found by key code",
        "hwid.reset",
        customers_mod.resetkey,
        "<code>",
    ),
    Command(
        "resetuser",
        "Clear a customer's hardware lock, found by id, username or key",
        "hwid.reset",
        customers_mod.resetuser,
        "<id|username|key>",
    ),
    Command(
        "accountinfo",
        "Your account info requests, or one of them with its zip",
        "accountinfo.read",
        accountinfo_mod.accountinfo,
        "[ref]",
    ),
    Command(
        "requestinfo",
        "Ask for a customer's account history, for chargebacks and disputes",
        "accountinfo.request",
        accountinfo_mod.requestinfo,
        "<key> <chargeback|dispute|fraud|other> [reference] [| note]",
    ),
    Command("domains", "Your white-label domains and whether they are live", "domains.read", account_mod.domains),
    Command(
        "status",
        "Whether a product is up, and whether customer keys are frozen",
        "status.read",
        status_mod.status,
        "[product]",
    ),
    Command(
        "updates",
        "The latest game build and the recent patch notes",
        "status.read",
        status_mod.updates,
        "[product]",
    ),
    Command(
        "changelog",
        "What changed in the latest loader and product releases",
        "status.read",
        status_mod.changelog,
        "[product] [en|ru|zh]",
    ),
    Command(
        "brand",
        "Your branding and the links to your public pages",
        "brand.read",
        brand_mod.brand,
    ),
    Command(
        "setbrand",
        "Change your branding, one field at a time",
        "brand.write",
        brand_mod.setbrand,
        "<field> <value>",
    ),
    Command(
        "webhooks",
        "Your Discord webhooks for status changes and update notes",
        "brand.read",
        webhooks_mod.webhooks,
    ),
    Command(
        "webhook",
        "Test, pause or resume one of your webhooks",
        "brand.write",
        webhooks_mod.webhook,
        "<id> <test|pause|resume>",
    ),
    Command("tickets", "List your support threads", "tickets.read", support_mod.tickets, "[status]"),
    Command("ticket", "Read one support thread", "tickets.read", support_mod.ticket, "<ref>"),
    Command(
        "newticket",
        "Open a support ticket",
        "tickets.write",
        support_mod.newticket,
        "<subject> | <message>",
    ),
    Command(
        "replyticket",
        "Reply to one of your support threads",
        "tickets.write",
        support_mod.replyticket,
        "<ref> <message>",
    ),
    Command(
        "closeticket",
        "Close a support thread you no longer need",
        "tickets.write",
        support_mod.closeticket,
        "<ref>",
    ),
    Command(
        "activity",
        "Recent activity on your partner account",
        "activity.read",
        support_mod.activity,
        "[limit]",
    ),
    Command("whoami", "Show what this bot will let you do", None, account_mod.whoami),
)

BY_NAME = {command.name: command for command in COMMANDS}

MENU = [(c.name, c.description[:256]) for c in COMMANDS if c.name != "start"]
