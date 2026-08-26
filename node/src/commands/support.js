import { ago, code, esc, lines, pair, title, truncate } from "../format.js";
import { send } from "../reply.js";

const STATUSES = ["all", "open", "answered", "resolved", "closed"];

function line(t) {
  const unread = t.unread ? " · unread reply" : "";
  return lines(
    `${code(t.ref)} ${esc(t.subject)}`,
    `${t.status} · ${t.priority} · ${t.messages} message(s)${unread}`,
    `Last activity ${ago(t.last_message_at)}`
  );
}

export const tickets = {
  name: "tickets",
  description: "List your support threads",
  args: "[status]",
  scope: "tickets.read",
  async run({ ctx, api, args }) {
    const wanted = (args[0] ?? "all").trim().toLowerCase();
    if (!STATUSES.includes(wanted)) {
      await send(ctx, `Status must be one of: ${STATUSES.join(", ")}`);
      return;
    }

    const result = await api.listTickets({ status: wanted });
    const rows = result.tickets ?? [];
    if (!rows.length) {
      await send(ctx, "No tickets match that.");
      return;
    }

    await send(ctx, truncate(lines(title(`Tickets (${rows.length})`), "", rows.map(line).join("\n\n"))));
  },
};

export const ticket = {
  name: "ticket",
  description: "Read one support thread",
  args: "<ref>",
  scope: "tickets.read",
  async run({ ctx, api, args }) {
    const ref = (args[0] ?? "").trim().toUpperCase();
    if (!ref) {
      await send(ctx, `Usage: ${code("/ticket TKT-8H2QMD")}`);
      return;
    }

    const t = await api.getTicket(ref);
    const thread = (t.thread ?? [])
      .map((m) => `${title(m.role === "partner" ? "You" : "Support")} ${ago(m.created_at)}\n${esc(m.body)}`)
      .join("\n\n");

    await send(
      ctx,
      truncate(
        lines(
          title(`${t.ref} ${esc(t.subject)}`),
          `${t.status} · ${t.priority} · ${t.category}`,
          "",
          thread || "No messages yet."
        )
      )
    );
  },
};

export const newticket = {
  name: "newticket",
  description: "Open a support ticket",
  args: "<subject> | <message>",
  scope: "tickets.write",
  async run({ ctx, api, args }) {
    const raw = args.join(" ");
    const [subject, ...rest] = raw.split("|");
    const body = rest.join("|").trim();

    if (!subject?.trim() || !body) {
      await send(ctx, `Usage: ${code("/newticket Key not activating | They redeemed it but nothing happened")}`);
      return;
    }

    const made = await api.createTicket({ subject: subject.trim(), body });
    await send(
      ctx,
      lines(
        title("Ticket opened"),
        `${code(made.ref)} ${esc(made.subject ?? "")}`,
        `Read it with ${code(`/ticket ${made.ref}`)}`
      )
    );
  },
};

export const replyticket = {
  name: "replyticket",
  description: "Reply to one of your support threads",
  args: "<ref> <message>",
  scope: "tickets.write",
  async run({ ctx, api, args }) {
    const ref = (args[0] ?? "").trim().toUpperCase();
    const body = args.slice(1).join(" ").trim();
    if (!ref || !body) {
      await send(ctx, `Usage: ${code("/replyticket TKT-8H2QMD One more thing")}`);
      return;
    }

    const t = await api.replyTicket(ref, body);
    await send(ctx, lines(title("Reply sent"), pair("Ticket", t.ref ?? ref), pair("Messages", t.messages ?? "more")));
  },
};

export const closeticket = {
  name: "closeticket",
  description: "Close a support thread you no longer need",
  args: "<ref>",
  scope: "tickets.write",
  async run({ ctx, api, args }) {
    const ref = (args[0] ?? "").trim().toUpperCase();
    if (!ref) {
      await send(ctx, `Usage: ${code("/closeticket TKT-8H2QMD")}`);
      return;
    }
    const closed = await api.closeTicket(ref);
    await send(ctx, lines(title("Ticket closed"), pair("Ticket", closed.ref ?? ref)));
  },
};

export const activity = {
  name: "activity",
  description: "Recent activity on your partner account",
  args: "[limit]",
  scope: "activity.read",
  async run({ ctx, api, args }) {
    const wanted = Number(args[0]);
    const limit = Number.isInteger(wanted) && wanted > 0 && wanted <= 200 ? wanted : 15;
    const result = await api.activity({ limit });
    const events = result.events ?? [];

    if (!events.length) {
      await send(ctx, "Nothing has happened yet.");
      return;
    }

    await send(
      ctx,
      truncate(
        lines(
          title("Recent activity"),
          "",
          events
            .map((e) => {
              const who = e.actor?.username ? ` by ${esc(e.actor.username)}` : "";
              const about = e.target?.username ? ` · ${esc(e.target.username)}` : "";
              return `${code(e.action)}${who}${about}\n${ago(e.created_at)}`;
            })
            .join("\n\n")
        )
      )
    );
  },
};
