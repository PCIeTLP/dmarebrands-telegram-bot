import { account, domains, help, plans, start, stats, whoami } from "./account.js";
import { buy, key, keys, refund } from "./keys.js";
import { balance, customer, customers, ledger, resetkey, resetuser } from "./customers.js";
import { status, updates } from "./status.js";
import { brand, setbrand } from "./brand.js";
import { activity, closeticket, newticket, replyticket, ticket, tickets } from "./support.js";

export const COMMANDS = [
  start,
  help,
  account,
  plans,
  stats,
  balance,
  ledger,
  keys,
  key,
  buy,
  refund,
  customers,
  customer,
  resetkey,
  resetuser,
  domains,
  status,
  updates,
  brand,
  setbrand,
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
