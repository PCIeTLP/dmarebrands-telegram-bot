import { ago, code, esc, lines, money, pair, title, truncate, until } from "../format.js";
import { confirm, send, sendPrivate } from "../reply.js";

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
        title("Machines"),
        machineLines(found)
      ),
      "Sent you the customer details in a private message."
    );
  },
};

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

    const answer = await confirm(ctx, {
      text: lines(
        title("Confirm this reset"),
        "",
        `This clears every hardware lock on ${title(found.customer.username)} (id ${found.customer.id}).`,
        "They will be able to bind a new machine on their next launch."
      ),
      confirmLabel: "Reset machine",
    });

    if (!answer.ok) {
      if (!answer.timedOut) await send(ctx, "Cancelled. Nothing was cleared.");
      return;
    }

    const result = await api.resetByKey(wanted);
    await send(
      ctx,
      lines(
        title("Machine reset"),
        `Cleared ${result.cleared} lock${result.cleared === 1 ? "" : "s"} for ${title(found.customer.username)}.`
      )
    );
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
    const answer = await confirm(ctx, {
      text: lines(
        title("Confirm this reset"),
        "",
        `This clears every hardware lock on ${title(found.username)} (id ${found.id}).`,
        "They will be able to bind a new machine on their next launch."
      ),
      confirmLabel: "Reset machine",
    });

    if (!answer.ok) {
      if (!answer.timedOut) await send(ctx, "Cancelled. Nothing was cleared.");
      return;
    }

    const result = await api.resetByCustomer(found.id);
    await send(
      ctx,
      lines(
        title("Machine reset"),
        `Cleared ${result.cleared} lock${result.cleared === 1 ? "" : "s"} for ${title(found.username)}.`
      )
    );
    await log(`${esc(ctx.from.username ?? ctx.from.id)} reset HWID for ${esc(found.username)} (id ${id})`);
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
