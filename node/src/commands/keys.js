import { code, esc, lines, money, pair, stateLabel, title, truncate, until } from "../format.js";
import { confirm, send, sendPrivate } from "../reply.js";

const FILTERS = new Set(["all", "unused", "active", "expired"]);

function keyLine(key) {
  const owner = key.customer ? ` · ${esc(key.customer.username)}` : "";
  const expiry = key.expires_at ? ` · expires ${until(key.expires_at)}` : "";
  return `${code(key.code)} - ${stateLabel(key.state)} · ${key.days}d ${esc(key.product)}${owner}${expiry}`;
}

export const keys = {
  name: "keys",
  description: "List keys you have issued",
  args: "[all|unused|active|expired] [search]",
  scope: "keys.read",
  async run({ ctx, api, args }) {
    let filter = "all";
    let rest = args;

    if (rest.length && FILTERS.has(rest[0].toLowerCase())) {
      filter = rest[0].toLowerCase();
      rest = rest.slice(1);
    }
    const search = rest.join(" ").trim() || undefined;

    const result = await api.listKeys({ filter, search, limit: 25 });
    const rows = result.data ?? [];

    if (!rows.length) {
      await send(ctx, "No keys matched that.");
      return;
    }

    const body = lines(
      title(`Keys - ${filter === "all" ? "everything" : stateLabel(filter)}`),
      "",
      ...rows.map(keyLine),
      "",
      `<i>${rows.length} shown</i>`
    );

    await sendPrivate(ctx, truncate(body), "Sent you the key list in a private message.");
  },
};

export const key = {
  name: "key",
  description: "Look up a single key",
  args: "<code>",
  scope: "keys.read",
  async run({ ctx, api, args }) {
    const wanted = (args[0] ?? "").trim();
    if (!wanted) {
      await send(ctx, `Usage: <code>/key DMA-XXXX-XXXX-XXXX-XXXX</code>`);
      return;
    }

    const found = await api.getKey(wanted);
    await sendPrivate(
      ctx,
      lines(
        title(`Key ${found.code}`),
        "",
        pair("State", stateLabel(found.state)),
        pair("Product", `${found.days}d ${found.product}`),
        pair("Cost", money(found.cost_usd)),
        pair("Redeemed", found.redeemed_at ? until(found.redeemed_at) : "not yet"),
        pair("Expires", found.expires_at ? until(found.expires_at) : "n/a"),
        found.customer ? pair("Customer", `${found.customer.username} (id ${found.customer.id})`) : ""
      ),
      "Sent you the key details in a private message."
    );
  },
};

export const buy = {
  name: "buy",
  description: "Buy new keys against the partner balance",
  args: "<plan> [count]",
  scope: "keys.buy",
  async run({ ctx, api, args, log }) {
    const planId = (args[0] ?? "").trim();
    const count = args[1] === undefined ? 1 : Number(args[1]);

    if (!planId) {
      await send(ctx, `Usage: <code>/buy rust-30 2</code>\nRun /plans to see the ids.`);
      return;
    }
    if (!Number.isInteger(count) || count < 1 || count > 25) {
      await send(ctx, "Count must be a whole number between 1 and 25.");
      return;
    }

    const planList = await api.plans();
    const chosen = (planList.data ?? []).find((p) => p.id === planId);
    if (!chosen) {
      await send(ctx, `There is no plan called ${code(planId)}. Run /plans to see what is available.`);
      return;
    }

    const total = Math.round(chosen.your_price_usd * count * 100) / 100;
    const balance = await api.balance();
    const available = Number(balance.balance_usd);

    if (available < total) {
      await send(
        ctx,
        lines(
          title("Not enough balance"),
          `${count} × ${esc(chosen.label)} costs ${money(total)} but the account only has ${money(available)}.`
        )
      );
      return;
    }

    const answer = await confirm(ctx, {
      text: lines(
        title("Confirm this purchase"),
        "",
        `${count} × ${esc(chosen.label)} (${chosen.days} days)`,
        `${money(chosen.your_price_usd)} each · ${money(total)} total`,
        `Balance after: ${money(available - total)}`
      ),
      confirmLabel: `Buy for ${money(total)}`,
    });

    if (!answer.ok) {
      if (!answer.timedOut) await send(ctx, "Cancelled. No keys were bought.");
      return;
    }

    const bought = await api.buyKeys(planId, count, `telegram:${ctx.chat?.id ?? "dm"}:${ctx.message?.message_id ?? Date.now()}`);
    const codes = (bought.data ?? []).map((k) => k.code);

    await sendPrivate(
      ctx,
      lines(
        title(`Bought ${codes.length} key${codes.length === 1 ? "" : "s"}`),
        "",
        codes.map((c) => code(c)).join("\n"),
        "",
        pair("Spent", money(bought.spent_usd)),
        pair("Balance", money(bought.balance_usd))
      ),
      `Bought ${codes.length} key${codes.length === 1 ? "" : "s"} for ${money(bought.spent_usd)}. Codes sent privately.`
    );

    await log(
      `${esc(ctx.from.username ?? ctx.from.id)} bought ${codes.length} × ${esc(chosen.label)} for ${money(
        bought.spent_usd
      )}`
    );
  },
};

export const refund = {
  name: "refund",
  description: "Refund an unredeemed key back to your balance",
  args: "<code>",
  scope: "keys.refund",
  async run({ ctx, api, args, log }) {
    const wanted = (args[0] ?? "").trim();
    if (!wanted) {
      await send(ctx, `Usage: <code>/refund DMA-XXXX-XXXX-XXXX-XXXX</code>`);
      return;
    }

    const found = await api.getKey(wanted);
    if (found.state !== "unused") {
      await send(
        ctx,
        lines(
          title("Cannot refund that"),
          "Only keys still in stock can be refunded. That one has already been redeemed."
        )
      );
      return;
    }

    const answer = await confirm(ctx, {
      text: lines(
        title("Confirm this refund"),
        "",
        `${code(found.code)} - ${found.days}d ${esc(found.product)}`,
        `This destroys the key and puts ${money(found.cost_usd)} back on the balance.`,
        "It cannot be undone and the code stops working immediately."
      ),
      confirmLabel: `Refund ${money(found.cost_usd)}`,
    });

    if (!answer.ok) {
      if (!answer.timedOut) await send(ctx, "Cancelled. The key was left alone.");
      return;
    }

    const result = await api.refundKey(wanted);
    await send(
      ctx,
      lines(
        title("Refunded"),
        `${code(result.code)} is gone.`,
        "",
        pair("Returned", money(result.refunded_usd)),
        pair("Balance", money(result.balance_usd))
      )
    );

    await log(
      `${esc(ctx.from.username ?? ctx.from.id)} refunded ${code(result.code)} for ${money(result.refunded_usd)}`
    );
  },
};
