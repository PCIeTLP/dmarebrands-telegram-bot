# Changelog

## v1.3.3

Keys can now last hours or minutes as well as days, and the bot shows the real length.

- Key lines in `/keys`, `/key`, `/buy`, `/redemptions` and `/customerkeys` read the API's new
  `duration` field, so a one-hour key shows as `1h` instead of `0d`. Day keys look the same as
  before. If the API is older and has no `duration`, the bot falls back to the day count.

The commands themselves did not change, so upgrading is a pull and a restart.

## v1.3.2

Accounts with more than one brand can pick the one the bot works for, and support threads and
activity stay out of group chats.

- `BRAND_ID` in `.env` picks which of your brands the bot works for. Every request sends it as
  `brand_id`, the account info zip download included. Leave it empty to keep using your first
  brand. The startup log, the doctor script and `/account` show the brand in use, and a
  `BRAND_ID` that is not one of your brands is reported as that instead of as a bad API key.
- A key code, customer ref or ticket ref with a `/` or `\` in it no longer reaches a different
  endpoint. The bot answers "Nothing matched that." without calling the API, and
  `/customerkeys` only lists keys when the API names the customer they belong to.
- `USERS_HWID` no longer grants `keys.read`, which let it see your unsold key codes with
  `/keys unused`. Resets look up the key or customer themselves, so `/resetkey`, `/resetuser`
  and `/customer` work as before. `/keys`, `/key` and `/redemptions` now need `USERS_KEYS` or
  `USERS_READ`.
- In a group, `/tickets`, `/ticket`, `/activity` and the answer to `/requestinfo` go to you in a
  private message, the same as key codes. Ticket subjects and threads can hold key codes and
  customer names, and the activity feed names customers. If the private message fails after
  `/requestinfo`, the group is told the request went through and to run `/accountinfo <ref>` in
  a private chat, so nobody sends it twice.
- `/ticket` shows the newest messages of a long thread instead of the oldest, and says how many
  earlier ones it left out. It marks the ticket read only once everything since your last message
  has reached you in full. If a reply does not fit, the ticket stays unread and the bot points you
  to the partner panel, and it also stays unread when the private message fails. Before, a long
  first message pushed the latest reply out of view and the ticket was marked read anyway.
- The Node bot skips commands sent while it was offline, the way the Python bot always has.
  Before, a `/setbrand` or `/topup` sent during downtime ran once the bot came back, on top of
  anything changed in the meantime.
- The Python bot ignores edited commands, the way the Node bot always has. Editing an old
  `/resetuser` message ran it again under the first message's request key, so the API replayed
  the old answer and nothing was reset.

The command menu did not change, so upgrading is a pull and a restart.

## 2026-10-21

Deadlock is public, so the bot covers it the way it covers Rust and Wardogs.

- `/updates deadlock` shows Deadlock's latest build and Valve's recent patch notes.
- `/status`, `/plans`, `/buy` and `/changelog` take their products from the API, so
  Deadlock shows up there without any change on your side.
- Status webhooks can include Deadlock now. Webhooks you already have keep the products they
  had, so tick Deadlock under Products in the partner panel if you want it there too.
- A one-day gap between builds reads `1 day` instead of `1 days`. Deadlock ships far more
  often than the other games, so it is the usual case there.

## 2026-10-15

Top-ups, account info for chargebacks, release notes and webhooks, and every change is now
safe to retry.

- `/topup 100 usdttrc20` opens a crypto payment for your balance and shows the exact amount to
  send, the address, any memo or tag the coin needs and a link to the checkout page. Without
  arguments it lists the popular coins. `/topups` lists your recent top-ups and
  `/topups <ref>` shows where one stands. Starting one needs the new `billing.topup` scope,
  which `USERS_BILLING` now includes.
- `/requestinfo` asks for the account history of whoever redeemed a key, for a chargeback or
  a dispute. `/accountinfo` lists your requests, and `/accountinfo <ref>` shows where one
  stands and sends the zip once it is approved. They need the new `accountinfo.request` and
  `accountinfo.read` scopes, both part of `USERS_SUPPORT`.
- `/changelog [product] [en|ru|zh]` shows what changed in the loader and each product.
- `/webhooks` lists your Discord webhooks, and `/webhook <id> test|pause|resume` sends a test
  post, pauses one or turns it back on.
- `/redemptions` lists the latest keys your customers redeemed, `/online` shows who is online
  right now and `/customerkeys` lists every key you sold one customer.
- `/stats` adds live customers, who is online, unread tickets and a line for the last 7 days.
- `/ticket` marks the thread read, the same as opening it in the partner panel.
- In a group, payment details, customer lists and account info zips go to you in a private
  message, the same as key codes.
- Refunds, resets, tickets, replies, branding changes, top-ups and account info requests send
  an `Idempotency-Key` built from the chat and message. A retry after a dropped connection
  gets the first result back instead of doing the work twice, and a request that is still
  running is waited out for up to a minute, the way `/buy` already was.
- A `429` with a `Retry-After` longer than 30 seconds, such as the limit on opening tickets,
  is reported straight away instead of being retried into the same limit.
- The Python bot reads `USERS_SUPPORT` and gives `USERS_KEYS`, `USERS_HWID` and `USERS_READ`
  the same scopes as the Node bot. Before, anyone listed only in `USERS_SUPPORT` got nothing
  in Python, and the other three groups could not see product status.

## 2026-10-13

A failed private message no longer invites a second purchase, and confirmations cannot be
mixed up.

- If `/buy` goes through but the bot cannot message you the codes, the group is told the
  purchase went through, to open a private chat and run `/keys unused` there, and not to
  buy again. Before, it said to run the command again, which bought a second batch.
  `/refund`, `/resetkey` and `/resetuser` say the action was done in the same situation.
- Two confirmations started in the same millisecond, for example when a restart replays a
  backlog, no longer share an id. Pressing one could run the other command.
- A confirmation listens for its button before it is sent, so a quick press is no longer
  turned away as expired. If the short note in the group fails to send, the private prompt
  still works.
- Pressing Cancel on a private prompt is acknowledged on that prompt instead of in the
  group.
- A button press reaches the waiting command straight away instead of after two Telegram
  calls. If Telegram then fails to acknowledge the press, Python no longer tells you it did
  not work after the action has already run.
- Once the API has answered a `/buy` with `in_progress`, a later timeout, dropped
  connection, 5xx, 429 or unreadable error page no longer reads as "try again". The bot
  keeps pointing at `/keys unused`. The wait also stops at its minute instead of sleeping
  past it.
- `Retry-After` values like `1.5` or an HTTP date no longer make Python give up or Node
  retry without waiting.
- A key code, customer ref or ticket ref of `.` or `..` no longer reaches a different
  endpoint, and the Python client keeps `;`, `&` and similar characters encoded the way
  Node does.
- Long single-line messages, such as a ticket thread, are no longer cut through an emoji or
  inside a closing tag, which Telegram rejected.
- A ticket without a subject, or a product without a label, shows blank again instead of
  `null`, `None` or `undefined`.
- Older entries here used the Discord command names. They now say `/buy`, `/tickets` and
  `/ticket`.

## 2026-09-24

Confirm buttons work again, and refunds and resets stay out of group chats.

- Confirmation buttons work again. The bot handled one update at a time, so a command that
  waited for its own Confirm press never saw it and timed out after a minute. Commands now
  run alongside incoming updates, and the press is answered straight away.
- `/buy` now waits out a purchase that is still running. The API answers a retry that
  arrives before the first request finishes with `409 in_progress`, and the bot resends the
  same `reference` after the `Retry-After` it gets (up to a minute) instead of reporting a
  failure. If it is still unresolved after that, the bot says so and points at
  `/keys unused` rather than inviting a second purchase.
- `/refund`, `/resetkey` and `/resetuser` keep key codes and customer details out of
  groups. With `PRIVATE_RESULTS` on, the confirmation and the result go to your private
  chat and the group only sees a short note. If the bot cannot message you, nothing is done.
- Long lists no longer break mid-tag. Truncation cuts at a line break where it can and
  never leaves half an HTML tag or entity behind, so a long `/tickets` list or `/ticket`
  thread still renders.
- Names and links with `&`, `<` or `>` no longer show up double escaped in `/brand`,
  `/ticket` and `/status`.
- The Python client URL-encodes key codes, customer refs and ticket refs in request paths,
  so a customer named `a?b` or `../stats` reaches the right endpoint. Node already did.
- `/start` and `/help` are titled "Partner bot".
- A machine reset by customer no longer throws in Node after the reset has gone through.

## 2026-09-14

Buying is now safe to retry.

- `/buy` sends the chat and message id as the `reference` on `POST /keys`, which the
  API now treats as an idempotency key. If the connection drops after the batch was
  minted, the bot retries and gets the same keys back instead of a second batch and a
  second charge.
- Because of that, the client retries `POST /keys` on 5xx and network errors the same way
  it already retried GETs. Other commands are unchanged.

## 2026-09-13

Wardogs is public, so the bot stops assuming every game is Rust.

- `/updates [product]` takes a game, `rust` or `wardogs`, and says which one it is showing.
- `/plans` prefixes every row with its product, so the Rust and Wardogs month plans no
  longer look identical.
- `/customers` and `/customer` now carry a `products` list from the API, one entry per
  product you sold that customer, alongside the summary fields.

## 2026-08-26

Caught the bot up with the six endpoint groups the Partner API just gained.

### New commands

- `/status [product]` shows whether a product is up, updating or detected, and whether
  customer keys are frozen. While a product is frozen nobody loses time, which is the
  question support gets asked most, so it is called out on its own line.
- `/updates` shows the current Rust build, roughly how often builds land, and the last few
  patch notes.
- `/brand` and `/setbrand <field> <value>` read and change your name, colours, store link and
  the two public page toggles, one field at a time.
- `/tickets`, `/ticket`, `/newticket`, `/replyticket` and `/closeticket` cover support threads
  end to end, so you can answer us without leaving Telegram.
- `/activity [limit]` is the same event feed as the Activity page, handy pointed at a log
  channel.

### Changed

- `/customer` and `/resetuser` take an id, a username, or any key code you sold
  them. Prefix with `id:`, `username:` or `key:` if a name could be read as something else.
  Looking someone up by key works even after that key expired.

### Permissions

Six new scopes: `status.read`, `brand.read`, `brand.write`, `tickets.read`, `tickets.write`,
`activity.read`. There is a new `USERS_SUPPORT` group for people who answer tickets and need
to see product status, but have no business near your balance. Existing groups keep what they
had and pick up `status.read`.

Nothing here changes an existing command's behaviour, so upgrading is just a pull and a
re-register.
