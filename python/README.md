# dmarebrands Telegram bot for Python

[python-telegram-bot](https://python-telegram-bot.org) v22 on Python 3.10 or newer. See the
[main README](../README.md) for the command list, the permission model and how Telegram's lack
of ephemeral replies is handled.

## Install

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`, then:

```bash
python scripts/doctor.py         # checks your token, API key, allowlist and menu
python scripts/register.py       # publishes the command menu to Telegram
python -m dmarebrandsbot         # runs the bot
```

`scripts/doctor.py` is the fastest way to find a setup mistake. It verifies the bot token, calls
the partner API with your key, and warns about any command nobody on the allowlist can reach.

## Scripts

| | |
|---|---|
| `python -m dmarebrandsbot` | Run the bot |
| `python scripts/register.py` | Publish the command menu |
| `python scripts/register.py --clear` | Remove the command menu |
| `python scripts/doctor.py` | Check the whole setup and report problems |

The menu is a convenience for users typing `/`. Permissions are checked on every command
whether or not the menu is published.

## Running it for real

With systemd:

```ini
[Unit]
Description=dmarebrands Telegram bot
After=network-online.target

[Service]
WorkingDirectory=/opt/dmarebrands-telegram-bot/python
ExecStart=/opt/dmarebrands-telegram-bot/python/.venv/bin/python -m dmarebrandsbot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Layout

```
dmarebrandsbot/
  __main__.py       entrypoint, python -m dmarebrandsbot
  bot.py            application wiring, chat and permission gates, error handling
  config.py         .env parsing and validation, user to scope mapping
  api.py            partner API client, retries, rate limits
  permissions.py    scope resolution and chat policy
  formatting.py     HTML escaping, money, relative times
  reply.py          private replies, confirmation buttons
  handlers/         one module per group of commands
scripts/
  register.py       publish or clear the command menu
  doctor.py         setup checks
```

## Adding a command

Write an async handler in `dmarebrandsbot/handlers/`, then add a `Command(...)` entry to the
`COMMANDS` tuple in `handlers/__init__.py` and run `python scripts/register.py`.

Set the scope to `None` for a command anyone may run. Everything written into a message must go
through `esc()` from `formatting.py` - Telegram parses HTML, so an unescaped customer username
would break the message or inject formatting.
