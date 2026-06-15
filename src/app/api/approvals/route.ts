import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

// Cổng phê duyệt 2 chiều (từ Zalo/Telegram hoặc dashboard).
// Body: { approvalId, decision: "approve"|"edit"|"reject", note? }
export async function POST(req: Request) {
  let body: { approvalId?: string; decision?: string; note?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const { approvalId, decision, note } = body;
  if (!approvalId || !decision) {
    return NextResponse.json({ error: "missing fields" }, { status: 400 });
  }

  const approval = await prisma.approvalRequest.findUnique({ where: { id: approvalId } });
  if (!approval) return NextResponse.json({ error: "not found" }, { status: 404 });

  await prisma.approvalRequest.update({
    where: { id: approvalId },
    data: { decision, note: note ?? null, resolvedAt: new Date() },
  });

  // Nếu duyệt quyết định ngày: kích hoạt mục tiêu đang PROPOSED.
  if (decision === "approve" && approval.kind === "daily_decision") {
    await prisma.goal.updateMany({
      where: { tenantId: approval.tenantId, status: "PROPOSED" },
      data: { status: "APPROVED" },
    });
  }
  // Nếu duyệt content nhạy cảm:
  if (decision === "approve" && approval.kind === "content" && approval.refId) {
    await prisma.content.update({
      where: { id: approval.refId },
      data: { status: "APPROVED" },
    });
  }

  return NextResponse.json({ ok: true });
}
