import Anthropic from "@anthropic-ai/sdk";
import { prisma } from "./prisma";

// ───────────────────────── Phân tầng model & chi phí ─────────────────────────
// Giá tham chiếu (USD / 1M token), xem docs/AI-MOS-DESIGN.md mục 7.

export const MODELS = {
  // Quyết định khó: CEO, Strategy, Optimizer
  reasoning: "claude-opus-4-8",
  // Mặc định: Content, Ads, Analytics, Intel
  default: "claude-sonnet-4-6",
  // Khối lượng lớn, rẻ: Reply, Lead
  cheap: "claude-haiku-4-5",
} as const;

const PRICE: Record<string, { in: number; out: number }> = {
  "claude-opus-4-8": { in: 5, out: 25 },
  "claude-sonnet-4-6": { in: 3, out: 15 },
  "claude-haiku-4-5": { in: 1, out: 5 },
};

export function estimateCostUsd(model: string, inTok: number, outTok: number): number {
  const p = PRICE[model] ?? PRICE["claude-sonnet-4-6"];
  return (inTok * p.in + outTok * p.out) / 1_000_000;
}

let _client: Anthropic | null = null;
export function anthropic(): Anthropic {
  if (!_client) {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) throw new Error("Thiếu ANTHROPIC_API_KEY");
    _client = new Anthropic({ apiKey });
  }
  return _client;
}

// Trần chi phí AI/ngày theo tenant (mục 7 & 8 design doc).
export async function checkAiBudget(tenantId: string, capUsd: number): Promise<void> {
  const since = new Date();
  since.setHours(0, 0, 0, 0);
  const agg = await prisma.agentRun.aggregate({
    where: { tenantId, startedAt: { gte: since } },
    _sum: { costUsd: true },
  });
  const spent = agg._sum.costUsd ?? 0;
  if (spent >= capUsd) {
    throw new Error(
      `Vượt trần chi phí AI/ngày của tenant (${spent.toFixed(4)} >= ${capUsd} USD).`,
    );
  }
}
