import type { Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { MODELS } from "../anthropic";
import { runAgentJson } from "./base";
import type { OptimizerDecision } from "./types";

// Optimizer (mỗi 3h): quyết định CẤP DANH MỤC campaign — bật/tắt, tái phân bổ
// ngân sách xuyên nền tảng, nhân bản campaign thắng. KHÔNG chỉnh bid (mục 5.1).
export async function runOptimizer(tenant: Tenant): Promise<OptimizerDecision[]> {
  const campaigns = await prisma.adCampaign.findMany({
    where: { tenantId: tenant.id, status: { in: ["active", "draft"] } },
    include: { metrics: { orderBy: { at: "desc" }, take: 3 } },
  });
  if (campaigns.length === 0) return [];

  const system = [
    "Bạn là AI Optimizer cho ads của spa.",
    "Chỉ quyết định ở cấp danh mục campaign: keep | pause (campaign yếu) | scale (tăng ngân sách) | duplicate (nhân bản campaign thắng) | reallocate.",
    "Dựa trên CPL, CTR, ROAS, frequency. KHÔNG đề xuất chỉnh bid/đối tượng (nền tảng tự lo).",
    'Trả về DUY NHẤT JSON: {"decisions":[{"campaignId","action","newBudgetVnd":number,"reason"}]}',
  ].join("\n");

  const user = JSON.stringify(
    campaigns.map((c) => ({
      campaignId: c.id,
      platform: c.platform,
      dailyBudgetVnd: c.dailyBudgetVnd,
      status: c.status,
      recentMetrics: c.metrics,
    })),
  );

  const { data } = await runAgentJson<{ decisions: OptimizerDecision[] }>({
    tenant,
    agent: "optimizer",
    model: MODELS.reasoning,
    system,
    user,
    maxTokens: 2048,
  });

  // Áp quyết định (trong guardrail: trần ngân sách).
  for (const d of data.decisions ?? []) {
    const camp = campaigns.find((c) => c.id === d.campaignId);
    if (!camp) continue;
    if (d.action === "pause") {
      await prisma.adCampaign.update({ where: { id: camp.id }, data: { status: "paused" } });
    } else if ((d.action === "scale" || d.action === "reallocate") && d.newBudgetVnd) {
      // Trần: không tăng quá 2x ngân sách hiện tại trong một bước.
      const capped = Math.min(d.newBudgetVnd, camp.dailyBudgetVnd * 2);
      await prisma.adCampaign.update({
        where: { id: camp.id },
        data: { dailyBudgetVnd: Math.round(capped), status: "active" },
      });
    }
    // duplicate/keep: ghi nhận, xử lý ở connector layer khi live.
  }
  return data.decisions ?? [];
}
