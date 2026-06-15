import { getActiveTenants } from "../src/lib/tenant";
import { runOptimizeCycle } from "../src/lib/orchestrator/optimize";

async function main() {
  for (const t of await getActiveTenants()) {
    console.log(`\n=== Optimize: ${t.name} ===`);
    console.log(await runOptimizeCycle(t));
  }
}

main().then(
  () => process.exit(0),
  (e) => {
    console.error(e);
    process.exit(1);
  },
);
