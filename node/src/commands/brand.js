import { code, lines, pair, title } from "../format.js";
import { send } from "../reply.js";

const BOOLS = { true: true, on: true, yes: true, false: false, off: false, no: false };
const TEXT_FIELDS = ["name", "primary", "accent", "store_url"];
const FLAG_FIELDS = ["public_features", "public_guide"];

function linkLine(label, url, isPublic) {
  if (!url) return pair(label, "not until your menu domain is live");
  return pair(label, `${isPublic ? "public" : "sign in required"}\n${url}`);
}

function view(b) {
  return lines(
    title(b.name || "No brand name set"),
    "",
    pair("Brand colour", b.primary ?? "not set"),
    pair("Second colour", b.accent ?? "not set"),
    pair("Logo", b.has_logo ? "uploaded" : "none"),
    pair("Store link", b.store_url || "not set"),
    "",
    linkLine("Features", b.features_url, b.public_features),
    linkLine("Setup guide", b.guide_url, b.public_guide)
  );
}

export const brand = {
  name: "brand",
  description: "Show your branding and the links to your public pages",
  scope: "brand.read",
  async run({ ctx, api }) {
    await send(ctx, view(await api.brand()));
  },
};

export const setbrand = {
  name: "setbrand",
  description: "Change your branding, one field at a time",
  args: "<field> <value>",
  scope: "brand.write",
  async run({ ctx, api, args }) {
    const field = (args[0] ?? "").trim().toLowerCase();
    const value = args.slice(1).join(" ").trim();

    if (!field) {
      await send(
        ctx,
        lines(
          "Usage:",
          code("/setbrand name Your Brand"),
          code("/setbrand primary #7c5cff"),
          code("/setbrand store_url https://yourbrand.com/store"),
          code("/setbrand public_guide on"),
          "",
          `Fields: ${[...TEXT_FIELDS, ...FLAG_FIELDS].join(", ")}`
        )
      );
      return;
    }

    if (FLAG_FIELDS.includes(field)) {
      const flag = BOOLS[value.toLowerCase()];
      if (flag === undefined) {
        await send(ctx, `Say on or off, for example ${code(`/setbrand ${field} on`)}`);
        return;
      }
      await send(ctx, view(await api.updateBrand({ [field]: flag })));
      return;
    }

    if (!TEXT_FIELDS.includes(field)) {
      await send(ctx, `Unknown field. Try one of: ${[...TEXT_FIELDS, ...FLAG_FIELDS].join(", ")}`);
      return;
    }

    const patch = { [field]: value === "" || value.toLowerCase() === "clear" ? null : value };
    await send(ctx, view(await api.updateBrand(patch)));
  },
};
