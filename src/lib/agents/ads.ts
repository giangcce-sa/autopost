import type { Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { MODELS } from "../anthropic";
import { runAgentJson } from "./base";
import type { AdProposal } from "./types";

// Media Buyer: đề xuất cấu trúc campaign (ưu tiên Advantage+/Smart+),
// KHÔNG micro-manage bid/targeting (xem design doc mục 5.1).
export async function runMediaBuyer(
  tenant: Tenant,
  goalContext: string,
): Promise<string[]> {
  const services = await prisma.service.findMany({
    where: { tenantId: tenant.id, active: true },
  });

  const system = [
    "Bạn là Media Buyer cho spa tại Việt Nam.",
    "Nguyên tắc: ưu tiên Meta Advantage+ / TikTok Smart+ (AI nền tảng tự lo bid/targeting/creative-test).",
    "Bạn chỉ quyết định: dịch vụ đẩy, ngân sách/ngày, mục tiêu campaign. KHÔNG tinh chỉnh bid/đối tượng.",
    'Trả về DUY NHẤT JSON: {"campaigns":[{"platform":"META_ADS|TIKTOK_ADS","serviceName","objective","dailyBudgetVnd":number,"rationale"}]}',
  ].join("\n");

  const user = [
    `Dịch vụ: ${services.map((s) => s.name).join(", ") || "(chưa khai báo)"}.`,
    `Bối cảnh mục tiêu: ${goalContext}`,
    "Đề xuất 1-2 campaign hợp lý cho ngân sách spa nhỏ.",
  ].join("\n");

  const { data } = await runAgentJson<{ campaigns: AdProposal[] }>({
    tenant,
    agent: "ads",
    model: MODELS.default,
    system,
    user,
    maxTokens: 2048,
  });

  const ids: string[] = [];
  for (const c of data.campaigns ?? []) {
    const svc = services.find((s) => s.name === c.serviceName);
    const camp = await prisma.adCampaign.create({
      data: {
        tenantId: tenant.id,
        platform: c.platform,
        serviceId: svc?.id ?? null,
        objective: c.objective ?? "LEADS",
        dailyBudgetVnd: Math.max(0, Math.round(c.dailyBudgetVnd ?? 0)),
        status: "draft",
      },
    });
    ids.push(camp.id);
  }
  return ids;
}
