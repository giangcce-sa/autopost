import { NextResponse } from "next/server";
import { checkCronAuth } from "@/app/api/_auth";
import { getActiveTenants } from "@/lib/tenant";
import { runDailyStandup } from "@/lib/orchestrator/standup";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

// Cron 8h sáng (theo timezone tenant — lập lịch ở tầng cron provider).
// Vercel Cron gọi GET; cũng hỗ trợ POST khi gọi thủ công.
export async function GET(req: Request) {
  const denied = checkCronAuth(req);
  if (denied) return denied;

  const tenants = await getActiveTenants();
  const results: Record<string, unknown> = {};
  for (const t of tenants) {
    try {
      results[t.id] = await runDailyStandup(t);
    } catch (err) {
      results[t.id] = { error: err instanceof Error ? err.message : String(err) };
    }
  }
  return NextResponse.json({ ran: tenants.length, results });
}

export const POST = GET;
