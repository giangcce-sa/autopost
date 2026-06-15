import { NextResponse } from "next/server";
import { checkCronAuth } from "@/app/api/_auth";
import { runPublisher } from "@/lib/orchestrator/publisher";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

// Cron thường xuyên (vd mỗi 5-15 phút): đăng các bài tới hạn.
export async function GET(req: Request) {
  const denied = checkCronAuth(req);
  if (denied) return denied;
  const result = await runPublisher();
  return NextResponse.json(result);
}

export const POST = GET;
