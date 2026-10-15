import { ago, code, esc, lines, pair, title, truncate } from "../format.js";
import { requestKey, send, sendFile, sendPrivate } from "../reply.js";

const REASON_LABEL = {
  chargeback: "Chargeback",
  dispute: "Payment dispute",
  fraud: "Fraud report",
  other: "Something else",
};

const STATUS_LABEL = {
  pending: "Waiting for approval",
  approved: "Ready to download",
  declined: "Declined",
};

const ATTACH_LIMIT = 20 * 1024 * 1024;

function found(summary) {
  return lines(
    `${summary.website_sign_ins} website sign-ins · ${summary.loader_sign_ins} loader sign-ins`,
    `${summary.downloads} downloads · ${summary.game_sessions} game sessions`,
    `${summary.ip_addresses} IP addresses · ${summary.machines} machines · ${summary.active_days} active days`,
    summary.first_use ? `First use ${ago(summary.first_use)} · last seen ${ago(summary.last_seen)}` : ""
  );
}

function statusText(r) {
  return lines(
    title(`Account info ${r.ref}`),
    "",
    pair("Status", STATUS_LABEL[r.status] ?? r.status),
    pair("Customer", r.customer?.username ?? "unknown"),
    pair("Key", r.key),
    pair("Reason", REASON_LABEL[r.reason] ?? r.reason),
    r.reference ? pair("Your reference", r.reference) : "",
    pair("Asked", ago(r.created_at)),
    r.status === "declined" && r.decline_reason ? `\n${esc(r.decline_reason)}` : "",
    r.summary ? `\n${title("What we found")}\n${found(r.summary)}` : ""
  );
}

export const accountinfo = {
  name: "accountinfo",
  description: "Your account info requests, or one of them with its zip",
  args: "[ref]",
  scope: "accountinfo.read",
  async run({ ctx, api, args }) {
    const ref = (args[0] ?? "").trim().toUpperCase();

    if (!ref) {
      const result = await api.listAccountInfo({ limit: 15 });
      const rows = result.data ?? [];
      if (!rows.length) {
        await send(ctx, `No requests yet. Ask for one with ${code("/requestinfo DMA-XXXX-XXXX-XXXX-XXXX chargeback")}.`);
        return;
      }
      await sendPrivate(
        ctx,
        truncate(
          lines(
            title(`Account info requests (${rows.length})`),
            "",
            rows
              .map((r) =>
                lines(
                  `${code(r.ref)} ${title(r.customer?.username ?? "unknown")} · ${code(r.key)}`,
                  `${REASON_LABEL[r.reason] ?? esc(r.reason)} · ${STATUS_LABEL[r.status] ?? esc(r.status)} · ${ago(r.created_at)}`
                )
              )
              .join("\n\n")
          )
        ),
        "Sent you your requests in a private message."
      );
      return;
    }

    const r = await api.getAccountInfo(ref);
    const text = statusText(r);

    if (r.status !== "approved" || !r.download) {
      await sendPrivate(ctx, text, "Sent you the request in a private message.");
      return;
    }

    if (Number(r.download.bytes) > ATTACH_LIMIT) {
      await sendPrivate(
        ctx,
        lines(text, "", "The zip is too big to send here. Download it from the ticket in the partner panel."),
        "Sent you the request in a private message."
      );
      return;
    }

    const file = await api.downloadAccountInfo(ref);
    await sendFile(
      ctx,
      file.data,
      file.name,
      truncate(lines(text, "", `SHA-256 ${code(file.sha256 ?? r.download.sha256)}`), 1000),
      "Sent you the zip in a private message."
    );
  },
};

export const requestinfo = {
  name: "requestinfo",
  description: "Ask for a customer's account history, for chargebacks and disputes",
  args: "<key> <chargeback|dispute|fraud|other> [reference] [| note]",
  scope: "accountinfo.request",
  async run({ ctx, api, args, log }) {
    const raw = args.join(" ");
    const [head, ...rest] = raw.split("|");
    const [key, reason, reference] = head.trim().split(/\s+/).filter(Boolean);
    const note = rest.join("|").trim();

    if (!key || !reason || !REASON_LABEL[reason.toLowerCase()]) {
      await send(
        ctx,
        lines(
          `Usage: ${code("/requestinfo DMA-XXXX-XXXX-XXXX-XXXX chargeback dp_12345 | anything we should know")}`,
          "The reason is chargeback, dispute, fraud or other. The reference and note are optional."
        )
      );
      return;
    }

    const made = await api.requestAccountInfo(
      { code: key, reason: reason.toLowerCase(), reference, note: note || undefined },
      requestKey(ctx)
    );

    await send(
      ctx,
      lines(
        title("Request sent"),
        `We check every request before the zip is made. Check on it with ${code(`/accountinfo ${made.ref}`)}.`,
        `Our replies show up in ${code(`/ticket ${made.ref}`)}.`,
        "",
        pair("Reference", made.ref),
        pair("Customer", made.customer?.username ?? "unknown")
      )
    );

    await log(
      `${esc(ctx.from.username ?? ctx.from.id)} asked for account info on ${esc(made.customer?.username ?? "a customer")} (${code(made.ref)})`
    );
  },
};
