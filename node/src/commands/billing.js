import { ago, code, esc, lines, money, pair, title, truncate, until } from "../format.js";
import { requestKey, send, sendPrivate } from "../reply.js";

const STATE_LABEL = {
  waiting: "Waiting for payment",
  confirming: "Payment seen, confirming",
  partially_paid: "Part paid",
  paid: "Paid, crediting now",
  credited: "On your balance",
  expired: "Expired",
  failed: "Failed",
  refunded: "Refunded",
};

function paymentText(t, heading) {
  const pay = t.pay ?? {};
  const open = t.state === "waiting" || t.state === "partially_paid";
  return lines(
    title(heading),
    "",
    pair("Amount", money(t.amount_usd)),
    pair("State", STATE_LABEL[t.state] ?? t.state),
    pair("Reference", t.ref),
    open
      ? lines(
          "",
          `Send exactly ${title(`${pay.amount ?? "?"} ${String(pay.currency ?? "").toUpperCase()}`)} to`,
          code(pay.address ?? "no address yet"),
          pay.extra_id ? `Memo or tag: ${code(pay.extra_id)}. The payment needs it.` : "",
          t.expires_at ? `Expires ${until(t.expires_at)}.` : "",
          `Or pay on the checkout page, with a QR code: ${esc(t.checkout_url)}`
        )
      : t.state === "credited"
        ? "\nThe money is on your balance."
        : ""
  );
}

export const topup = {
  name: "topup",
  description: "Add money to the partner balance with crypto",
  args: "<amount> <coin>",
  scope: "billing.topup",
  async run({ ctx, api, args, log }) {
    const amount = Number(args[0]);
    const coin = (args[1] ?? "").trim().toLowerCase();

    if (!Number.isFinite(amount) || !coin) {
      const result = await api.coins().catch(() => null);
      const popular = (result?.data ?? [])
        .filter((c) => c.popular)
        .slice(0, 12)
        .map((c) => code(c.code))
        .join(", ");
      await send(
        ctx,
        lines(
          `Usage: ${code("/topup 100 usdttrc20")}`,
          `Between ${money(result?.min_usd ?? 20)} and ${money(result?.max_usd ?? 10000)}.`,
          popular ? `Popular coins: ${popular}` : ""
        )
      );
      return;
    }

    const t = await api.startTopup(Math.round(amount * 100) / 100, coin, requestKey(ctx));
    await sendPrivate(
      ctx,
      paymentText(t, "Top-up opened"),
      `Top-up of ${money(t.amount_usd)} opened. Payment details sent privately.`,
      `Top-up of ${money(t.amount_usd)} opened, but I could not message you the payment details.\n` +
        `Open a chat with me and press <b>Start</b>, then run ${code(`/topups ${t.ref}`)} there.`
    );

    await log(
      `${esc(ctx.from.username ?? ctx.from.id)} opened a ${money(t.amount_usd)} top-up in ${esc(
        String(t.pay?.currency ?? coin).toUpperCase()
      )}`
    );
  },
};

export const topups = {
  name: "topups",
  description: "Your recent top-ups, or one of them by reference",
  args: "[ref]",
  scope: "billing.read",
  async run({ ctx, api, args }) {
    const ref = (args[0] ?? "").trim().toUpperCase();

    if (ref) {
      const t = await api.getTopup(ref);
      await sendPrivate(ctx, paymentText(t, `Top-up ${t.ref}`), "Sent you the top-up in a private message.");
      return;
    }

    const result = await api.topups(10);
    const rows = result.data ?? [];
    if (!rows.length) {
      await send(ctx, `No top-ups yet. Start one with ${code("/topup 100 usdttrc20")}.`);
      return;
    }

    await sendPrivate(
      ctx,
      truncate(
        lines(
          title("Recent top-ups"),
          "",
          ...rows.map(
            (t) =>
              `${code(t.ref)} - ${money(t.amount_usd)} · ${STATE_LABEL[t.state] ?? esc(t.state)} · ${esc(
                String(t.pay?.currency ?? "").toUpperCase()
              )} · ${ago(t.created_at)}`
          )
        )
      ),
      "Sent you your top-ups in a private message."
    );
  },
};

function invoiceState(inv) {
  if (inv.status === "paid") return "Paid";
  if (inv.stock_locked) return "Keys locked";
  if (inv.overdue) return "Due";
  return "Unpaid";
}

function day(value) {
  return value ? esc(String(value).slice(0, 10)) : "?";
}

function lastDay(value) {
  const ms = Date.parse(value ?? "");
  return Number.isNaN(ms) ? "?" : new Date(ms - 1000).toISOString().slice(0, 10);
}

export const invoices = {
  name: "invoices",
  description: "Your monthly credit invoices, or one of them by number",
  args: "[number]",
  scope: "billing.read",
  async run({ ctx, api, args }) {
    const number = (args[0] ?? "").trim().toUpperCase();

    if (number) {
      const inv = await api.getInvoice(number);
      const used = (inv.lines ?? []).filter((line) => line.kind === "usage");
      await sendPrivate(
        ctx,
        truncate(
          lines(
            title(`Invoice ${inv.number}`),
            "",
            pair("Amount", money(inv.amount_usd)),
            pair("Paid", money(inv.paid_usd)),
            pair("Still due", money(inv.due_usd)),
            pair("Period", `${day(inv.period_start)} to ${lastDay(inv.period_end)}`),
            pair("State", invoiceState(inv)),
            "",
            used.length
              ? used
                  .map(
                    (line) =>
                      `${line.qty} × ${esc(line.duration ?? "")} ${esc(line.product ?? "")} at ${money(line.unit_usd)} · ${money(
                        Math.abs(Number(line.amount_usd))
                      )}`
                  )
                  .join("\n")
              : "No keys used in this period."
          )
        ),
        "Sent you the invoice in a private message."
      );
      return;
    }

    const result = await api.invoices({ limit: 12 });
    const rows = result.data ?? [];
    if (!rows.length) {
      await send(ctx, "No invoices yet.");
      return;
    }
    await sendPrivate(
      ctx,
      truncate(
        lines(
          title("Invoices"),
          "",
          ...rows.map(
            (inv) =>
              `${code(inv.number)} - ${day(inv.period_start)} to ${lastDay(inv.period_end)} · ${money(inv.amount_usd)} · ${invoiceState(inv)}${
                inv.status === "open" ? ` · ${money(inv.due_usd)} due` : ""
              }`
          )
        )
      ),
      "Sent you your invoices in a private message."
    );
  },
};

export const payinvoice = {
  name: "payinvoice",
  description: "Open a payment for what is still due on an invoice",
  args: "<number> <coin> [amount]",
  scope: "billing.topup",
  async run({ ctx, api, args, log }) {
    const number = (args[0] ?? "").trim().toUpperCase();
    const coin = (args[1] ?? "").trim().toLowerCase();
    const amount = args[2] === undefined ? null : Number(args[2]);

    if (!number || !coin || (amount !== null && !Number.isFinite(amount))) {
      await send(ctx, lines(`Usage: ${code("/payinvoice INV-202611-K7QD usdttrc20")}`, "Add an amount, from 20, to pay part of it."));
      return;
    }

    const t = await api.payInvoice(number, coin, requestKey(ctx), amount ? Math.round(amount * 100) / 100 : null);
    await sendPrivate(
      ctx,
      paymentText(t, `Payment for ${number}`),
      `Payment of ${money(t.amount_usd)} opened. Payment details sent privately.`,
      `Payment of ${money(t.amount_usd)} opened, but I could not message you the payment details.\n` +
        `Open a chat with me and press <b>Start</b>, then run ${code(`/invoices ${number}`)} there.`
    );

    await log(`${esc(ctx.from.username ?? ctx.from.id)} opened a ${money(t.amount_usd)} payment for invoice ${esc(number)}`);
  },
};
