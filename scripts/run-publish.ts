import { runPublisher } from "../src/lib/orchestrator/publisher";

async function main() {
  console.log(await runPublisher());
}

main().then(
  () => process.exit(0),
  (e) => {
    console.error(e);
    process.exit(1);
  },
);
