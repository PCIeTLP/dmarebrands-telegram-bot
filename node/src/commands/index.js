import { account, domains, help, plans, start, stats, whoami } from "./account.js";
import { buy, key, keys, refund } from "./keys.js";
import { balance, customer, customers, ledger, resetkey, resetuser } from "./customers.js";

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
  whoami,
];

export const BY_NAME = new Map(COMMANDS.map((command) => [command.name, command]));

export const MENU = COMMANDS.filter((c) => c.name !== "start").map((command) => ({
  command: command.name,
  description: command.description.slice(0, 256),
}));
