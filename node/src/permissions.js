import { SCOPES } from "./config.js";

export function scopesFor(userId, userScopes) {
  if (userId === undefined || userId === null) return new Set();
  return new Set(userScopes.get(String(userId)) ?? []);
}

export function allows(granted, needed) {
  return granted.has(needed);
}

export function describeScopes(granted) {
  if (!granted.size) return "none";
  return SCOPES.filter((scope) => granted.has(scope)).join(", ");
}

export function deniedMessage(needed) {
  return `You are not allowed to do that. This command needs the <code>${needed}</code> scope, which your account does not have.`;
}

export function chatAllowed(chat, config) {
  if (!chat) return false;
  if (chat.type === "private") return true;
  return config.allowedChats.has(String(chat.id));
}
