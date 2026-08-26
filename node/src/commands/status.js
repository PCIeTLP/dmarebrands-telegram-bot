import { esc, lines, pair, title } from "../format.js";
import { send } from "../reply.js";

const HEADLINE = {
  undetected: "Up and safe to use",
  updating: "Updating",
  offline: "Temporarily offline",
  detected: "Detected, tell people to stop",
  discontinued: "Discontinued",
};

export const status = {
  name: "status",
  description: "Whether a product is up, and whether customer keys are frozen",
  args: "[product]",
  scope: "status.read",
  async run({ ctx, api, args }) {
    const result = await api.status((args[0] ?? "").trim() || undefined);
    const rows = result.products ?? [];

    if (!rows.length) {
      await send(ctx, "No products came back.");
      return;
    }

    const blocks = rows.map((p) =>
      lines(
        title(`${esc(p.label)}: ${HEADLINE[p.status] ?? p.status}`),
        p.beta ? "In beta." : "",
        p.frozen ? "Keys are frozen, so nobody is losing time." : "",
        p.sellable ? "" : "This one cannot be sold any more.",
        p.message ? esc(p.message) : "",
        pair("Changed", p.updated_at ?? "unknown")
      )
    );

    await send(ctx, blocks.join("\n\n"));
  },
};

export const updates = {
  name: "updates",
  description: "The latest Rust build and the recent patch notes",
  scope: "status.read",
  async run({ ctx, api }) {
    const result = await api.updates();
    const build = result.current_build;
    const notes = (result.updates ?? []).slice(0, 5);

    await send(
      ctx,
      lines(
        title("Game updates"),
        build ? pair("Current build", build.buildid) : "No build information yet.",
        build?.at ? pair("Seen", build.at) : "",
        result.average_gap_days ? pair("Usual gap", `${result.average_gap_days} days`) : "",
        notes.length ? "" : null,
        notes.length ? title("Recent notes") : null,
        ...notes.map((n) => `${esc(n.title)}\n${esc(n.url)}`)
      )
    );
  },
};
