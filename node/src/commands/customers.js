import { ago, code, esc, lines, money, pair, stateLabel, title, truncate, until } from "../format.js";
import { confirm, requestKey, send, sendPrivate } from "../reply.js";

function productLines(customer) {
  const list = customer.products ?? [];
  if (!list.length) return "none";
  return list
    .map((p) => `${esc(p.product)} · ${p.active ? `active until ${until(p.expires_at)}` : "expired"}`)
    .join("\n");
}

function machineLines(customer) {
  if (!customer.machines?.length) return "Nothing bound right now.";
  return customer.machines
    .map((m) => `${esc(m.scope)} - bound ${ago(m.bound_at)} · last seen ${ago(m.last_seen)}`)
    .join("\n");
}

export const customers = {
  name: "customers",
  description: "List the people who redeemed your keys",
  args: "[search]",
  scope: "customers.read",
  async run({ ctx, api, args }) {
    const search = args.join(" ").trim() || undefined;
    const result = await api.listCustomers({ search, limit: 25 });
    const rows = result.data ?? [];

    if (!rows.length) {
      await send(ctx, "No customers matched that.");
      return;
    }

    const body = lines(
      title("Customers"),
      "",
      ...rows.map((c) => {
        const state = c.active ? `active until ${until(c.expires_at)}` : "expired";
        const bound = c.machines?.length ? ` · ${c.machines.length} machine(s)` : "";
        return `${title(c.username)} (id ${c.id}) · ${state} · ${c.keys} key(s)${bound}`;
      }),
      "",
      `<i>${rows.length} shown</i>`
    );

    await sendPrivate(ctx, truncate(body), "Sent you the customer list in a private message.");
  },
};

export const customer = {
  name: "customer",
  description: "Look up one customer by id, username or a key they redeemed",
  args: "<id|username|key>",
  scope: "customers.read",
  async run({ ctx, api, args }) {
    const ref = (args[0] ?? "").trim();
    if (!ref) {
      await send(
        ctx,
        "Usage: <code>/customer 1042</code>, <code>/customer theirname</code> or <code>/customer DMA-XXXX-XXXX-XXXX-XXXX</code>"
      );
      return;
    }

    const found = await api.getCustomer(ref);
    await sendPrivate(
      ctx,
      lines(
        title(`Customer ${found.username}`),
        "",
        pair("Id", found.id),
        pair("Access", found.active ? "Active" : "Expired"),
        pair("Keys redeemed", found.keys),
        pair("Product", found.product ?? "none"),
        pair("Expires", found.expires_at ? until(found.expires_at) : "n/a"),
        pair("Joined", ago(found.created_at)),
        "",
        title("Products"),
        productLines(found),
        "",
        title("Machines"),
        machineLines(found)
      ),
      "Sent you the customer details in a private message."
    );
  },
};

async function confirmReset(ctx, customer, reset) {
  const answer = await confirm(ctx, {
    text: lines(
      title("Confirm this reset"),
      "",
      `This clears every hardware lock on ${title(customer.username)} (id ${customer.id}).`,
      "They will be able to bind a new machine on their next launch."
    ),
    confirmLabel: "Reset machine",
    sensitive: true,
  });

  if (!answer.ok) {
    if (answer.cancelled) await send(ctx, "Cancelled. Nothing was cleared.");
    return false;
  }

  const result = await reset();
  await sendPrivate(
    ctx,
    lines(
      title("Machine reset"),
      `Cleared ${result.cleared} lock${result.cleared === 1 ? "" : "s"} for ${title(customer.username)}.`
    ),
    "Machine reset. Details sent privately.",
    "Machine reset. I could not message you the details privately."
  );
  return true;
}

export const resetkey = {
  name: "resetkey",
  description: "Clear a customer's hardware lock, found by key code",
  args: "<code>",
  scope: "hwid.reset",
  async run({ ctx, api, args, log }) {
    const wanted = (args[0] ?? "").trim();
    if (!wanted) {
      await send(ctx, `Usage: <code>/resetkey DMA-XXXX-XXXX-XXXX-XXXX</code>`);
      return;
    }

    const found = await api.getKey(wanted);
    if (!found.customer) {
      await send(
        ctx,
        lines(title("Nobody to reset"), "That key has not been redeemed yet, so no machine is bound to it.")
      );
      return;
    }

    if (!(await confirmReset(ctx, found.customer, () => api.resetByKey(wanted, requestKey(ctx))))) return;
    await log(
      `${esc(ctx.from.username ?? ctx.from.id)} reset HWID for ${esc(found.customer.username)} via key ${code(wanted)}`
    );
  },
};

export const resetuser = {
  name: "resetuser",
  description: "Clear a customer's hardware lock, found by id, username or key",
  args: "<id|username|key>",
  scope: "hwid.reset",
  async run({ ctx, api, args, log }) {
    const ref = (args[0] ?? "").trim();
    if (!ref) {
      await send(
        ctx,
        "Usage: <code>/resetuser 1042</code>, <code>/resetuser theirname</code> or <code>/resetuser DMA-XXXX-XXXX-XXXX-XXXX</code>"
      );
      return;
    }

    const found = await api.getCustomer(ref);
    if (!(await confirmReset(ctx, found, () => api.resetByCustomer(found.id, requestKey(ctx))))) return;
    await log(`${esc(ctx.from.username ?? ctx.from.id)} reset HWID for ${esc(found.username)} (id ${found.id})`);
  },
};

export const customerkeys = {
  name: "customerkeys",
  description: "Every key you sold one customer",
  args: "<id|username|key>",
  scope: "customers.read",
  async run({ ctx, api, args }) {
    const ref = (args[0] ?? "").trim();
    if (!ref) {
      await send(ctx, "Usage: <code>/customerkeys theirname</code> or <code>/customerkeys DMA-XXXX-XXXX-XXXX-XXXX</code>");
      return;
    }

    const result = await api.customerKeys(ref);
    const rows = result.data ?? [];
    const who = result.customer?.username ?? ref;

    if (!rows.length) {
      await send(ctx, `${esc(who)} has no keys from you.`);
      return;
    }

    await sendPrivate(
      ctx,
      truncate(
        lines(
          title(`Keys for ${who}`),
          "",
          ...rows.map((key) => {
            const expiry = key.expires_at ? ` · expires ${until(key.expires_at)}` : "";
            return `${code(key.code)} - ${stateLabel(key.state)} · ${key.days}d ${esc(key.product)}${expiry}`;
          }),
          "",
          `<i>${rows.length} key${rows.length === 1 ? "" : "s"}</i>`
        )
      ),
      "Sent you their keys in a private message."
    );
  },
};

export const online = {
  name: "online",
  description: "Your customers who are online right now",
  scope: "customers.read",
  async run({ ctx, api }) {
    const result = await api.online();
    const rows = result.data ?? [];

    if (!rows.length) {
      await send(ctx, "Nobody is online right now.");
      return;
    }

    await sendPrivate(
      ctx,
      truncate(
        lines(
          title(`Online now (${rows.length})`),
          "",
          ...rows.map((c) => {
            const doing = c.playing?.length
              ? `in ${esc(c.playing.join(", "))}`
              : `menu open${c.menu?.length ? ` (${esc(c.menu.join(", "))})` : ""}`;
            return `${title(c.username)} · ${doing} · since ${ago(c.online_since)}`;
          }),
          "",
          `<i>${result.playing ?? 0} in game</i>`
        )
      ),
      "Sent you who is online in a private message."
    );
  },
};

export const balance = {
  name: "balance",
  description: "Partner balance and how to top it up",
  scope: "billing.read",
  async run({ ctx, api }) {
    const b = await api.balance();
    await send(
      ctx,
      lines(
        title("Balance"),
        "",
        pair("Available", money(b.balance_usd)),
        pair("Your discount", `${b.discount_pct}%`),
        "",
        b.topup
          ? `Top up between ${money(b.topup.min_usd)} and ${money(b.topup.max_usd)} at ${esc(b.topup.url)}`
          : "Top up from the partner panel."
      )
    );
  },
};

const KIND_LABEL = {
  topup: "Top-up",
  purchase: "Keys bought",
  refund: "Refund",
  adjust: "Adjustment",
};

export const ledger = {
  name: "ledger",
  description: "Recent movements on the partner balance",
  args: "[limit]",
  scope: "billing.read",
  async run({ ctx, api, args }) {
    const limit = args[0] === undefined ? 10 : Number(args[0]);
    if (!Number.isInteger(limit) || limit < 1 || limit > 25) {
      await send(ctx, "Limit must be a whole number between 1 and 25.");
      return;
    }

    const result = await api.ledger(limit);
    const rows = result.data ?? [];

    if (!rows.length) {
      await send(ctx, "Nothing on the ledger yet.");
      return;
    }

    await send(
      ctx,
      truncate(
        lines(
          title("Ledger"),
          "",
          ...rows.map((entry) => {
            const amount = Number(entry.amount_usd);
            const sign = amount >= 0 ? "+" : "−";
            const label = KIND_LABEL[entry.kind] ?? entry.kind;
            return lines(
              `${sign}${money(Math.abs(amount)).slice(1)} · ${title(label)} · ${ago(entry.created_at)}`,
              `${esc(entry.note || "No note")} · balance after ${money(entry.balance_after_usd)}`,
              ""
            );
          })
        )
      )
    );
  },
};
