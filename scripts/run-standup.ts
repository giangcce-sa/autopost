import { getActiveTenants } from "../src/lib/tenant";
import { runDailyStandup } from "../src/lib/orchestrator/standup";

// Chạy giao ban thủ công (local). Cần ANTHROPIC_API_KEY + DATABASE_URL.
async function main() {
  const tenants = await getActiveTenants();
  for (const t of tenants) {
    console.log(`\n=== Giao ban: ${t.name} ===`);
    const r = await runDailyStandup(t);
    console.log("CEO:", r.ceoSummary);
  }
}

main().then(
  () => process.exit(0),
  (e) => {
    console.error(e);
    process.exit(1);
  },
);
