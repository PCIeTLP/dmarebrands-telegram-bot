import { ago, clip, esc, lines, pair, title, truncate } from "../format.js";
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
        title(`${p.label ?? ""}: ${HEADLINE[p.status] ?? p.status}`),
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
  description: "The latest game build and the recent patch notes",
  args: "[product]",
  scope: "status.read",
  async run({ ctx, api, args }) {
    const wanted = (args[0] ?? "").trim() || undefined;
    const result = await api.updates(wanted);
    const build = result.current_build;
    const notes = (result.updates ?? []).slice(0, 5);

    await send(
      ctx,
      lines(
        title(`Game updates · ${result.game ?? wanted ?? "rust"}`),
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

const LANGS = new Set(["en", "ru", "zh", "cn"]);

export const changelog = {
  name: "changelog",
  description: "What changed in the latest loader and product releases",
  args: "[product] [en|ru|zh]",
  scope: "status.read",
  async run({ ctx, api, args }) {
    let product;
    let lang = "en";
    for (const arg of args.map((a) => a.toLowerCase())) {
      if (LANGS.has(arg)) lang = arg === "cn" ? "zh" : arg;
      else product = arg;
    }

    const result = await api.changelogs({ product, lang, limit: 5 });
    const rows = result.data ?? [];

    if (!rows.length) {
      await send(ctx, "No release notes yet.");
      return;
    }

    await send(
      ctx,
      truncate(
        lines(
          title("Release notes"),
          "",
          rows
            .map((r) =>
              lines(
                `${title(`${r.label} ${r.version}`)}${r.previous_version ? ` (from ${esc(r.previous_version)})` : ""} · ${ago(r.created_at)}`,
                r.notes ? esc(clip(r.notes, 700)) : "<i>No notes for this release.</i>"
              )
            )
            .join("\n\n")
        )
      )
    );
  },
};
