import type { Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { MODELS } from "../anthropic";
import { runAgentJson } from "./base";
import type { CeoDecision, IntelPayload } from "./types";
import type { AnalyticsReport } from "./analytics";

// CEO Agent: đọc báo cáo → ra quyết định ngày → đặt/điều chỉnh mục tiêu → giao việc.
export async function runCeo(
  tenant: Tenant,
  inputs: { intel?: IntelPayload; analytics?: AnalyticsReport },
): Promise<CeoDecision> {
  const goals = await prisma.goal.findMany({
    where: { tenantId: tenant.id, status: { in: ["APPROVED", "ACTIVE"] } },
  });

  const system = [
    "Bạn là CEO Agent điều hành marketing cho một spa tại Việt Nam.",
    "Đọc báo cáo tình báo + phân tích, ra QUYẾT ĐỊNH cho hôm nay và GIAO VIỆC cho các agent:",
    "intel, strategy, content, ads, optimizer.",
    "Quyết định phải bám mục tiêu tháng, thực tế với ngân sách spa nhỏ, và tuân thủ pháp luật.",
    'Trả về DUY NHẤT JSON: {"summary":string,"goals":[{"period","serviceName","targetLeads","targetCpaVnd","targetRevenue"}],"decisions":[string],"tasks":[{"agent","instruction"}]}',
  ].join("\n");

  const user = [
    `Spa: ${tenant.name} (${tenant.businessType}). Mức tự trị: ${tenant.autonomyLevel}.`,
    `Mục tiêu hiện có: ${JSON.stringify(goals)}`,
    `Tình báo: ${JSON.stringify(inputs.intel ?? {})}`,
    `Phân tích: ${JSON.stringify(inputs.analytics ?? {})}`,
    `Tháng hiện tại: ${new Date().toISOString().slice(0, 7)}`,
  ].join("\n");

  const { data } = await runAgentJson<CeoDecision>({
    tenant,
    agent: "ceo",
    model: MODELS.reasoning,
    system,
    user,
    maxTokens: 3072,
  });

  // Lưu mục tiêu mới (PROPOSED — chờ duyệt qua cổng Zalo/Telegram).
  for (const g of data.goals ?? []) {
    await prisma.goal.create({
      data: {
        tenantId: tenant.id,
        period: g.period,
        targetLeads: g.targetLeads ?? null,
        targetCpaVnd: g.targetCpaVnd ?? null,
        targetRevenue: g.targetRevenue ?? null,
        status: "PROPOSED",
      },
    });
  }

  // Lưu task giao cho các agent.
  for (const t of data.tasks ?? []) {
    await prisma.agentTask.create({
      data: { tenantId: tenant.id, agent: t.agent, payload: { instruction: t.instruction } },
    });
  }

  return data;
}
