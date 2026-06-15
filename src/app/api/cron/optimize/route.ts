import { NextResponse } from "next/server";
import { checkCronAuth } from "@/app/api/_auth";
import { getActiveTenants } from "@/lib/tenant";
import { runOptimizeCycle } from "@/lib/orchestrator/optimize";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

// Cron mỗi 3h: Optimizer cấp danh mục campaign.
export async function GET(req: Request) {
  const denied = checkCronAuth(req);
  if (denied) return denied;

  const tenants = await getActiveTenants();
  const results: Record<string, unknown> = {};
  for (const t of tenants) {
    try {
      results[t.id] = await runOptimizeCycle(t);
    } catch (err) {
      results[t.id] = { error: err instanceof Error ? err.message : String(err) };
    }
  }
  return NextResponse.json({ ran: tenants.length, results });
}

export const POST = GET;
