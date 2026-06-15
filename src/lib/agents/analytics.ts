import type { Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { MODELS } from "../anthropic";
import { runAgentJson } from "./base";

export interface AnalyticsReport {
  summary: string;
  insights: string[];
  metrics: {
    newLeads: number;
    publishedPosts: number;
    activeCampaigns: number;
    aiCostUsdToday: number;
  };
}

// Analytics Agent: tổng hợp hiệu suất marketing + lead cho dashboard & CEO.
export async function runAnalytics(tenant: Tenant): Promise<AnalyticsReport> {
  const since = new Date();
  since.setHours(0, 0, 0, 0);

  const [newLeads, publishedPosts, activeCampaigns, costAgg] = await Promise.all([
    prisma.lead.count({ where: { tenantId: tenant.id, createdAt: { gte: since } } }),
    prisma.scheduledPost.count({
      where: { tenantId: tenant.id, status: "published", createdAt: { gte: since } },
    }),
    prisma.adCampaign.count({ where: { tenantId: tenant.id, status: "active" } }),
    prisma.agentRun.aggregate({
      where: { tenantId: tenant.id, startedAt: { gte: since } },
      _sum: { costUsd: true },
    }),
  ]);

  const metrics = {
    newLeads,
    publishedPosts,
    activeCampaigns,
    aiCostUsdToday: Number((costAgg._sum.costUsd ?? 0).toFixed(4)),
  };

  const system = [
    "Bạn là chuyên viên phân tích marketing cho spa.",
    "Từ số liệu, viết tóm tắt ngắn (tiếng Việt) + 2-3 insight hành động được.",
    'Trả về DUY NHẤT JSON: {"summary":string,"insights":[string]}',
  ].join("\n");

  const { data } = await runAgentJson<{ summary: string; insights: string[] }>({
    tenant,
    agent: "analytics",
    model: MODELS.default,
    system,
    user: `Số liệu hôm nay: ${JSON.stringify(metrics)}`,
    maxTokens: 1024,
  });

  return { summary: data.summary, insights: data.insights ?? [], metrics };
}
