import { account, domains, help, plans, start, stats, whoami } from "./account.js";
import { buy, key, keys, redemptions, refund } from "./keys.js";
import { balance, customer, customerkeys, customers, ledger, online, resetkey, resetuser } from "./customers.js";
import { changelog, status, updates } from "./status.js";
import { brand, setbrand } from "./brand.js";
import { activity, closeticket, newticket, replyticket, ticket, tickets } from "./support.js";
import { topup, topups } from "./billing.js";
import { accountinfo, requestinfo } from "./accountinfo.js";
import { webhook, webhooks } from "./webhooks.js";

export const COMMANDS = [
  start,
  help,
  account,
  plans,
  stats,
  balance,
  ledger,
  topup,
  topups,
  keys,
  key,
  buy,
  refund,
  redemptions,
  customers,
  customer,
  customerkeys,
  online,
  resetkey,
  resetuser,
  accountinfo,
  requestinfo,
  domains,
  status,
  updates,
  changelog,
  brand,
  setbrand,
  webhooks,
  webhook,
  tickets,
  ticket,
  newticket,
  replyticket,
  closeticket,
  activity,
  whoami,
];

export const BY_NAME = new Map(COMMANDS.map((command) => [command.name, command]));

export const MENU = COMMANDS.filter((c) => c.name !== "start").map((command) => ({
  command: command.name,
  description: command.description.slice(0, 256),
}));
