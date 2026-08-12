import { Bot } from "grammy";
import { loadConfig } from "../src/config.js";
import { MENU } from "../src/commands/index.js";

const config = loadConfig();
const clear = process.argv.includes("--clear");
const bot = new Bot(config.token);

try {
  if (clear) {
    await bot.api.deleteMyCommands();
    console.log("Removed the command menu.");
  } else {
    await bot.api.setMyCommands(MENU);
    console.log(`Published ${MENU.length} commands to the Telegram menu:`);
    for (const entry of MENU) console.log(`  /${entry.command}`);
    console.log("\nThe menu is a hint only. Permissions are still checked on every command.");
  }
} catch (err) {
  console.error("\nCould not update the command menu.");
  console.error(err?.description ?? err?.message ?? err);
  process.exit(1);
}
