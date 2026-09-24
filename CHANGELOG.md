# Changelog

## 2026-09-24

Confirm buttons work again, and refunds and resets stay out of group chats.

- Confirmation buttons work again. The bot handled one update at a time, so a command that
  waited for its own Confirm press never saw it and timed out after a minute. Commands now
  run alongside incoming updates, and the press is answered straight away.
- `/keys buy` now waits out a purchase that is still running. The API answers a retry that
  arrives before the first request finishes with `409 in_progress`, and the bot resends the
  same `reference` after the `Retry-After` it gets (up to a minute) instead of reporting a
  failure. If it is still unresolved after that, the bot says so and points at
  `/keys unused` rather than inviting a second purchase.
- `/refund`, `/resetkey` and `/resetuser` keep key codes and customer details out of
  groups. With `PRIVATE_RESULTS` on, the confirmation and the result go to your private
  chat and the group only sees a short note. If the bot cannot message you, nothing is done.
- Long lists no longer break mid-tag. Truncation cuts at a line break where it can and
  never leaves half an HTML tag or entity behind, so a long `/tickets list` still renders.
- Names and links with `&`, `<` or `>` no longer show up double escaped in `/brand`,
  `/tickets` and `/status`.
- The Python client URL-encodes key codes, customer refs and ticket refs in request paths,
  so a customer named `a?b` or `../stats` reaches the right endpoint. Node already did.
- `/start` and `/help` are titled "Partner bot".
- A machine reset by customer no longer throws in Node after the reset has gone through.

## 2026-09-14

Buying is now safe to retry.

- `/keys buy` sends the chat and message id as the `reference` on `POST /keys`, which the
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
