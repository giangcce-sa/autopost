import { NextResponse } from "next/server";

// Bảo vệ cron bằng header x-cron-secret (so với env CRON_SECRET).
export function checkCronAuth(req: Request): NextResponse | null {
  const secret = process.env.CRON_SECRET;
  if (!secret) return null; // chưa cấu hình → cho phép (dev)
  // Hỗ trợ cả x-cron-secret và Authorization: Bearer (Vercel Cron).
  const got =
    req.headers.get("x-cron-secret") ??
    req.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (got !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  return null;
}
