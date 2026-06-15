import { NextResponse } from "next/server";
import type { ChannelType } from "@prisma/client";
import { getTenantOrThrow } from "@/lib/tenant";
import { runReply } from "@/lib/agents";

export const dynamic = "force-dynamic";

// Webhook inbox/comment từ kênh → Social Care trả lời + gom lead.
// Body: { tenantId, channel, externalUserId, message }
export async function POST(req: Request) {
  let body: { tenantId?: string; channel?: ChannelType; externalUserId?: string; message?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const { tenantId, channel, externalUserId, message } = body;
  if (!tenantId || !channel || !externalUserId || !message) {
    return NextResponse.json({ error: "missing fields" }, { status: 400 });
  }
  try {
    const tenant = await getTenantOrThrow(tenantId);
    const result = await runReply(tenant, channel, externalUserId, message);
    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 500 },
    );
  }
}
