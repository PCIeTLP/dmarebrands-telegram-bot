# dmarebrands Telegram bot — Node.js

[grammY](https://grammy.dev) on Node 20 or newer. See the [main README](../README.md) for the
command list, the permission model and how Telegram's lack of ephemeral replies is handled.

## Install

```bash
cd node
npm install
cp .env.example .env
```

Fill in `.env`, then:

```bash
npm run doctor     # checks your token, API key, allowlist and menu
npm run register   # publishes the command menu to Telegram
npm start          # runs the bot
```

`npm run doctor` is the fastest way to find a setup mistake. It verifies the bot token, calls
the partner API with your key, and warns about any command nobody on the allowlist can reach.

## Scripts

| | |
|---|---|
| `npm start` | Run the bot |
| `npm run register` | Publish the command menu |
| `npm run unregister` | Remove the command menu |
| `npm run doctor` | Check the whole setup and report problems |
| `npm run typecheck` | Resolve every module and check syntax |

The menu is a convenience for users typing `/`. Permissions are checked on every command
whether or not the menu is published.

## Running it for real

```bash
npm install -g pm2
pm2 start src/index.js --name dmarebrands-telegram-bot
pm2 save
```

## Layout

```
src/
  index.js          bot wiring, chat and permission gates, error handling
  config.js         .env parsing and validation, user to scope mapping
  api.js            partner API client, retries, rate limits
  permissions.js    scope resolution and chat policy
  format.js         HTML escaping, money, relative times
  reply.js          private replies, confirmation buttons
  commands/         one module per group of commands
scripts/
  register.js       publish or clear the command menu
  doctor.js         setup checks
```

## Adding a command

Add an object to a module in `src/commands/` with `{ name, description, scope, run }`, list it
in `src/commands/index.js`, and run `npm run register`.

Set `scope` to `null` for a command anyone may run. Everything written into a message must go
through `esc()` from `format.js` — Telegram parses HTML, so an unescaped customer username would
break the message or inject formatting.
