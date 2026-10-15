export function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export function money(value) {
  const n = Number(value ?? 0);
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function ago(value) {
  if (!value) return "never";
  const ms = typeof value === "number" ? value * 1000 : Date.parse(value);
  if (!Number.isFinite(ms)) return "unknown";
  return relative(ms);
}

export function until(seconds) {
  if (seconds === null || seconds === undefined) return "n/a";
  const n = Number(seconds);
  if (!Number.isFinite(n) || n <= 0) return "n/a";
  return relative(n * 1000);
}

function relative(ms) {
  const diff = ms - Date.now();
  const future = diff > 0;
  const mins = Math.round(Math.abs(diff) / 60000);

  if (mins < 1) return "just now";
  if (mins < 60) return future ? `in ${mins} min` : `${mins} min ago`;

  const hours = Math.round(mins / 60);
  if (hours < 48) return future ? `in ${hours}h` : `${hours}h ago`;

  const days = Math.round(hours / 24);
  return future ? `in ${days} days` : `${days} days ago`;
}

export function stateLabel(state) {
  if (state === "unused") return "in stock";
  if (state === "active") return "active";
  if (state === "expired") return "expired";
  return String(state ?? "unknown");
}

export function title(text) {
  return `<b>${esc(text)}</b>`;
}

export function code(text) {
  return `<code>${esc(text)}</code>`;
}

export function lines(...parts) {
  return parts.filter((p) => p !== null && p !== undefined && p !== "").join("\n");
}

export function clip(text, max) {
  const value = String(text ?? "");
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

export function pair(label, value) {
  return `${esc(label)}: <b>${esc(value)}</b>`;
}

const TRUNCATED = "\n\n<i>… list truncated</i>";

export function truncate(text, max = 3800) {
  if (text.length <= max) return text;
  const room = max - TRUNCATED.length;
  const line = text.lastIndexOf("\n", room);
  const kept =
    line > room / 2 ? text.slice(0, line) : text.slice(0, room).replace(/<[^>]*$|&[#\w]*$|[\ud800-\udbff]$/, "");
  return `${closeTags(kept)}${TRUNCATED}`;
}

function closeTags(html) {
  const open = [];
  for (const [, closing, name] of html.matchAll(/<(\/?)([a-z][\w-]*)[^>]*>/gi)) {
    if (closing) open.pop();
    else open.push(name);
  }
  return html + open.reverse().map((name) => `</${name}>`).join("");
}
