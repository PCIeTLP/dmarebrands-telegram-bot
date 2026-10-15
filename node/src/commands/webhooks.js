import { ago, code, esc, lines, title, truncate } from "../format.js";
import { requestKey, send } from "../reply.js";

const ACTIONS = new Set(["test", "pause", "resume"]);

function hookLine(h) {
  const kind = h.kind === "updates" ? "update notes" : "status changes";
  const state = h.enabled ? "on" : "paused";
  const sent = h.last_sent_at ? `last post ${ago(h.last_sent_at)}` : "nothing posted yet";
  return lines(
    `${title(`#${h.id} ${h.label || "Unnamed webhook"}`)} · ${kind} · ${state}`,
    `${esc((h.products ?? []).join(", "))} · ${sent}`,
    h.last_error ? `Last error: ${esc(h.last_error)}` : ""
  );
}

export const webhooks = {
  name: "webhooks",
  description: "Your Discord webhooks for status changes and update notes",
  scope: "brand.read",
  async run({ ctx, api }) {
    const result = await api.webhooks();
    const rows = result.data ?? [];

    if (!rows.length) {
      await send(ctx, "No webhooks yet. Add one on the Webhooks page of the partner panel.");
      return;
    }

    await send(
      ctx,
      truncate(lines(title(`Webhooks (${rows.length} of ${result.max ?? 10})`), "", rows.map(hookLine).join("\n\n")))
    );
  },
};

export const webhook = {
  name: "webhook",
  description: "Test, pause or resume one of your webhooks",
  args: "<id> <test|pause|resume>",
  scope: "brand.write",
  async run({ ctx, api, args, log }) {
    const id = Number(args[0]);
    const action = (args[1] ?? "").trim().toLowerCase();

    if (!Number.isInteger(id) || id < 1 || !ACTIONS.has(action)) {
      await send(ctx, `Usage: ${code("/webhook 7 test")}, ${code("/webhook 7 pause")} or ${code("/webhook 7 resume")}`);
      return;
    }

    if (action === "test") {
      const result = await api.testWebhook(id, requestKey(ctx));
      await send(
        ctx,
        result.sent
          ? lines(title("Test post sent"), `Check the channel webhook #${id} posts to.`)
          : lines(
              title("Discord refused the test post"),
              esc(result.error ?? "No reason given."),
              result.paused ? `The webhook has been paused. Fix it in Discord, then run ${code(`/webhook ${id} resume`)}.` : ""
            )
      );
      return;
    }

    const on = action === "resume";
    const hook = await api.setWebhookEnabled(id, on, requestKey(ctx));
    const name = title(`#${hook.id} ${hook.label || "Unnamed webhook"}`);
    await send(ctx, on ? `${name} posts again.` : `${name} will not post until you resume it.`);
    await log(`${esc(ctx.from.username ?? ctx.from.id)} ${on ? "resumed" : "paused"} webhook #${hook.id}`);
  },
};
