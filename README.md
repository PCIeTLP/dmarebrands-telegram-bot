# dmarebrands Telegram bot

**Built for partners of [dmarebrands.st](https://dmarebrands.st).** If you resell dmarebrands
keys, this lets you run the whole operation from Telegram: buy keys, refund unsold stock, reset
a customer's hardware lock, top up your balance and pull a customer's account history for a
chargeback without opening the partner panel.

You need a partner account and an API key to use it. Everything it does goes through the
[Partner API](https://partners.dmarebrands.st/partners/api/docs), so it can only ever touch keys
you issued and the customers who redeemed them.

Two complete implementations, same commands, same permission model. Pick whichever stack you
already run:

| | |
|---|---|
| [`node/`](node) | Node.js 20+, [grammY](https://grammy.dev) |
| [`python/`](python) | Python 3.10+, [python-telegram-bot](https://python-telegram-bot.org) v22 |

There is a [Discord version](https://github.com/PCIeTLP/dmarebrands-discord-bot) too.

## Commands

| Command | What it does | Scope needed |
|---|---|---|
| `/account` | Partner account, brand and headline numbers | `account.read` |
| `/plans` | Every plan with your discounted price | `account.read` |
| `/stats` | Keys, customers, who is online and the last 7 days | `account.read` |
| `/balance` | Available balance and how to top up | `billing.read` |
| `/ledger [limit]` | Recent movements on the balance | `billing.read` |
| `/topup <amount> <coin>` | Open a crypto payment for your balance. Without arguments it lists popular coins | `billing.topup` |
| `/topups [ref]` | Your recent top-ups, or where one stands | `billing.read` |
| `/keys [filter] [search]` | Keys you have issued | `keys.read` |
| `/key <code>` | One key, including who redeemed it | `keys.read` |
| `/buy <plan> [count]` | Mint new keys against your balance | `keys.buy` |
| `/refund <code>` | Destroy an unsold key, money back | `keys.refund` |
| `/redemptions [limit]` | The latest keys your customers redeemed | `keys.read` |
| `/customers [search]` | Everyone who redeemed your keys | `customers.read` |
| `/customer <id\|username\|key>` | One customer and their machines | `customers.read` |
| `/customerkeys <id\|username\|key>` | Every key you sold one customer | `customers.read` |
| `/online` | Your customers who are online right now | `customers.read` |
| `/resetkey <code>` | Clear their hardware lock, by key | `hwid.reset` |
| `/resetuser <id\|username\|key>` | Clear their hardware lock | `hwid.reset` |
| `/requestinfo <key> <reason> [reference] [\| note]` | Ask for a customer's account history, for chargebacks and disputes | `accountinfo.request` |
| `/accountinfo [ref]` | Your requests, or one of them with its zip once it is approved | `accountinfo.read` |
| `/domains` | Your white-label domains and DNS state | `domains.read` |
| `/status [product]` | Whether a product is up, and whether keys are frozen | `status.read` |
| `/updates [product]` | Latest build and recent patch notes for rust, wardogs or deadlock | `status.read` |
| `/changelog [product] [en\|ru\|zh]` | What changed in each loader and product release | `status.read` |
| `/brand` | Your branding and public page links | `brand.read` |
| `/setbrand <field> <value>` | Change one branding field | `brand.write` |
| `/webhooks` | Your Discord webhooks for status changes and update notes | `brand.read` |
| `/webhook <id> <test\|pause\|resume>` | Send a test post, or pause and resume a webhook | `brand.write` |
| `/tickets [status]` | Your support threads | `tickets.read` |
| `/ticket <ref>` | One thread with its messages, which also marks it read | `tickets.read` |
| `/newticket <subject> \| <message>` | Open a support ticket | `tickets.write` |
| `/replyticket <ref> <message>` | Reply to a thread | `tickets.write` |
| `/closeticket <ref>` | Close a thread | `tickets.write` |
| `/activity [limit]` | Recent activity on your account | `activity.read` |
| `/whoami` | What the bot will let *you* do | none |
| `/help` | Every command, split by what you can use | none |

Anything that spends or destroys money shows you the exact amount and waits for you to press a
confirm button. Only the person who ran the command can press it.

## Permissions

Telegram has no roles, so access is an **allowlist of numeric user IDs** across six groups. A
user gets the union of every group they appear in, so you can stack them.

```dotenv
USERS_ADMIN=111111111
USERS_KEYS=222222222
USERS_HWID=333333333,444444444
USERS_BILLING=555555555
USERS_SUPPORT=777777777
USERS_READ=666666666
```

| Group | Grants |
|---|---|
| `USERS_ADMIN` | everything |
| `USERS_KEYS` | buy, refund, read keys and customers |
| `USERS_HWID` | reset hardware locks, read keys and customers |
| `USERS_BILLING` | balance, ledger and top-ups |
| `USERS_SUPPORT` | product status, tickets, account info requests, read customers |
| `USERS_READ` | read-only across the board |

**To give someone nothing but HWID resets, put them in `USERS_HWID` and nowhere else.** They can
look up a key or customer to find who they are resetting, and clear the lock. They cannot see
your balance, cannot buy, cannot refund.

Anyone not on a list gets nothing at all. They can still run `/whoami`, which tells them their
user ID so they can ask you for access. Message [@userinfobot](https://t.me/userinfobot) to find
a numeric ID.

## Telegram has no ephemeral replies

This is the one real difference from the Discord version, and it matters: a Discord bot can
reply so that only you see it. Telegram cannot. Anything posted in a group is visible to
everyone in that group, forever.

So the bot handles key codes carefully:

- **In a private chat** it just replies. That is already private.
- **In a group** anything containing key codes, customer details, payment details or an account
  info zip is sent to you in a direct message instead, and the group only sees a short note like *"Bought 1 key for $28.00. Codes
  sent privately."*
- **If the DM fails** because you have never started a chat with the bot, it posts nothing and
  tells you to open one. It will not fall back to the group.

Set `PRIVATE_RESULTS=false` if you would rather everything stay in the channel.

By default the bot **only works in private chats**. To use it in a group, add that group's chat
ID to `ALLOWED_CHATS`. It refuses every other chat, so someone adding it to a random group
achieves nothing.

## Setting up the bot

1. Message [@BotFather](https://t.me/BotFather) and send `/newbot`. Follow the prompts.
2. Copy the token it gives you into `TELEGRAM_TOKEN`. Never commit this.
3. Message [@userinfobot](https://t.me/userinfobot) to get your numeric user ID, and put it in
   `USERS_ADMIN`.
4. If you want it in a group, add the bot to the group, then get the group's chat ID (it starts
   with `-100`) and put it in `ALLOWED_CHATS`.
5. Run the register script so the commands appear in Telegram's menu.

The menu is only a hint for users. Permissions are checked on every single command regardless of
what the menu shows.

## Getting an API key

You need a dmarebrands partner account. In the partner panel go to
[API](https://partners.dmarebrands.st/partners/api), create a key, and copy it into
`DMAREBRANDS_API_KEY`. It is shown once and never again.

Not a partner yet? Ask in the [dmarebrands](https://dmarebrands.st) store.

An API key is your whole partner account and **it can spend your balance**. Treat the `.env`
like a password file. If it leaks, revoke it in the panel. That takes effect on the next
request.

## Security notes

- Private chats only, unless you explicitly allow a group.
- Key codes never reach a group chat, even when the DM fails.
- Confirmation buttons only accept a press from the person who ran the command, and expire after
  60 seconds.
- Set `LOG_CHAT_ID` to have every purchase, refund and reset posted to a channel. Useful when
  several staff share one partner account.
- Every message is sent as escaped HTML, so a customer username can never inject formatting.
- Every command that changes something sends an `Idempotency-Key` made from the chat and message.
  If the connection drops and the bot sends it again, the API answers with the first result
  instead of doing the work twice.

## Licence

MIT. See [LICENSE](LICENSE).
