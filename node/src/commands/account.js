import { ago, code, esc, lines, money, pair, title } from "../format.js";
import { describeScopes } from "../permissions.js";
import { send } from "../reply.js";

export const account = {
  name: "account",
  description: "Partner account, brand and headline numbers",
  scope: "account.read",
  async run({ ctx, api }) {
    const me = await api.me();
    const brand = me.brand ?? {};
    const stats = me.stats ?? {};

    await send(
      ctx,
      lines(
        title(`Partner account: ${me.username}`),
        brand.name ? `Trading as ${esc(brand.name)}` : "No brand name set yet.",
        "",
        pair("Balance", money(me.balance_usd)),
        pair("Discount", `${me.discount_pct}%`),
        pair("Customers", stats.customers ?? 0),
        pair("Keys in stock", stats.keys_unused ?? 0),
        pair("Keys active", stats.keys_active ?? 0),
        pair("Spent all time", money(stats.spent_usd)),
        brand.store_url ? `\nStore: ${esc(brand.store_url)}` : ""
      )
    );
  },
};

export const plans = {
  name: "plans",
  description: "Every plan you can buy, with your discounted price",
  scope: "account.read",
  async run({ ctx, api }) {
    const result = await api.plans();
    const rows = result.data ?? [];

    if (!rows.length) {
      await send(ctx, "No plans are available right now.");
      return;
    }

    await send(
      ctx,
      lines(
        title("Plans"),
        "",
        ...rows.map((plan) =>
          lines(
            `${title(plan.label)} ${code(plan.id)}`,
            `${plan.days} days · ${money(plan.your_price_usd)} for you · list ${money(
              plan.list_price_usd
            )} · you save ${money(plan.saving_usd)}`,
            ""
          )
        )
      )
    );
  },
};

export const stats = {
  name: "stats",
  description: "Keys issued, active, expired and customers",
  scope: "account.read",
  async run({ ctx, api }) {
    const s = await api.stats();
    await send(
      ctx,
      lines(
        title("Stats"),
        "",
        pair("Keys issued", s.keys_total),
        pair("In stock", s.keys_unused),
        pair("Active", s.keys_active),
        pair("Expired", s.keys_expired),
        pair("Customers", s.customers),
        pair("Balance", money(s.balance_usd)),
        pair("Spent all time", money(s.spent_usd)),
        pair("HWID resets (30d)", s.hwid_resets_30d)
      )
    );
  },
};

export const domains = {
  name: "domains",
  description: "Your white-label domains and whether they are live",
  scope: "domains.read",
  async run({ ctx, api }) {
    const result = await api.domains();
    const rows = result.data ?? [];

    if (!rows.length) {
      await send(
        ctx,
        lines(
          "No domains set up yet.",
          "Add one at https://partners.dmarebrands.st/partners/branding",
          `Point a CNAME at ${code(result.cname_target ?? "the target shown in the panel")}.`
        )
      );
      return;
    }

    await send(
      ctx,
      lines(
        title("Your domains"),
        "",
        ...rows.map((d) =>
          lines(
            `${title(d.hostname)} - ${esc(d.kind)}`,
            d.live ? "Live" : `Not live yet (${esc(d.status)} / ssl ${esc(d.ssl_status)})`,
            d.checked_at ? `Checked ${ago(d.checked_at)}` : "",
            d.last_error ? esc(d.last_error) : "",
            ""
          )
        ),
        result.cname_target ? `CNAME target: ${code(result.cname_target)}` : ""
      )
    );
  },
};

export const whoami = {
  name: "whoami",
  description: "Show what this bot will let you do",
  scope: null,
  async run({ ctx, granted }) {
    await send(
      ctx,
      lines(
        title("Your access"),
        "",
        `Telegram user ID: ${code(ctx.from.id)}`,
        granted.size
          ? `Scopes: ${code(describeScopes(granted))}`
          : "You are not on this bot's allowlist, so every command will be refused.\nAsk whoever runs it to add your user ID."
      )
    );
  },
};

export const help = {
  name: "help",
  description: "List every command",
  scope: null,
  async run({ ctx, commands, granted }) {
    const usable = commands.filter((c) => !c.scope || granted.has(c.scope));
    const blocked = commands.filter((c) => c.scope && !granted.has(c.scope));

    await send(
      ctx,
      lines(
        title("dmarebrands partner bot"),
        "",
        usable.length ? title("You can use") : "",
        ...usable.map((c) => `/${c.name}${c.args ? ` ${esc(c.args)}` : ""} - ${esc(c.description)}`),
        blocked.length ? `\n${title("Not available to you")}` : "",
        ...blocked.map((c) => `/${c.name} - ${esc(c.description)}`)
      )
    );
  },
};

export const start = {
  name: "start",
  description: "Get started",
  scope: null,
  async run(context) {
    const { ctx, granted } = context;
    if (!granted.size) {
      await send(
        ctx,
        lines(
          title("dmarebrands partner bot"),
          "",
          "You are not on the allowlist yet.",
          `Your Telegram user ID is ${code(ctx.from.id)} - give that to whoever runs this bot.`
        )
      );
      return;
    }
    await help.run(context);
  },
};
