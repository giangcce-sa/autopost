import type { Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { getPublishChannels } from "../tenant";
import { getNotifier } from "../notify/notifier";
import {
  runAnalytics,
  runCeo,
  runContent,
  runIntel,
  runStrategy,
  type IdeaOut,
} from "../agents";

// HỌP GIAO BAN 8H SÁNG — nhịp tim của hệ thống (design doc mục 3.1).
// Pipeline: Intel → Strategy → Content → lên lịch → Analytics → CEO → cổng duyệt.
export async function runDailyStandup(tenant: Tenant): Promise<{ ceoSummary: string }> {
  // 1) Tình báo
  const intel = await runIntel(tenant);

  // 2) Chiến lược (Big Idea / Angle / Hook)
  const ideas: IdeaOut[] = await runStrategy(tenant, intel);

  // 3) Nội dung cho các kênh đang kết nối
  const channels = await getPublishChannels(tenant.id);
  const channelTypes = channels.map((c) => c.type);
  const contentIds: string[] = [];
  if (channelTypes.length > 0 && ideas[0]) {
    const ids = await runContent(tenant, ideas[0], channelTypes);
    contentIds.push(...ids);
  }

  // 4) Lên lịch đăng cho content APPROVED (FULL_AUTO). Content PENDING_APPROVAL chờ duyệt.
  await scheduleApprovedContent(tenant, contentIds);

  // 5) Phân tích
  const analytics = await runAnalytics(tenant);

  // 6) CEO ra quyết định + giao việc
  const ceo = await runCeo(tenant, { intel, analytics });

  // 7) Cổng duyệt: bản tin giao ban qua Zalo/Telegram
  const expiresAt = new Date(Date.now() + 2 * 60 * 60 * 1000); // 2h
  await prisma.approvalRequest.create({
    data: {
      tenantId: tenant.id,
      kind: "daily_decision",
      payload: { ceo, analytics: analytics.metrics } as object,
      expiresAt,
    },
  });

  const owner = await prisma.user.findFirst({
    where: { tenantId: tenant.id, role: "OWNER" },
  });
  const bulletin = [
    `📊 GIAO BAN ${new Date().toLocaleDateString("vi-VN")} — ${tenant.name}`,
    "",
    `Tình báo: ${intel.recommendation}`,
    `Lead mới hôm nay: ${analytics.metrics.newLeads} · Bài đã đăng: ${analytics.metrics.publishedPosts} · Campaign active: ${analytics.metrics.activeCampaigns}`,
    `Chi phí AI hôm nay: $${analytics.metrics.aiCostUsdToday}`,
    "",
    `Quyết định của CEO: ${ceo.summary}`,
    ...ceo.decisions.map((d) => `• ${d}`),
    "",
    "Trả lời: DUYỆT / SỬA / NÂNG MỤC TIÊU (timeout 2h → tự chạy trong guardrails).",
  ].join("\n");
  await getNotifier().send(owner?.telegramChatId ?? owner?.zaloUserId, bulletin);

  return { ceoSummary: ceo.summary };
}

async function scheduleApprovedContent(tenant: Tenant, contentIds: string[]): Promise<void> {
  if (contentIds.length === 0) return;
  const contents = await prisma.content.findMany({
    where: { id: { in: contentIds }, status: "APPROVED" },
  });
  const channels = await getPublishChannels(tenant.id);
  let offsetMin = 30;
  for (const c of contents) {
    const channel = channels.find((ch) => ch.type === c.channel);
    if (!channel) continue;
    await prisma.scheduledPost.create({
      data: {
        tenantId: tenant.id,
        contentId: c.id,
        channelId: channel.id,
        scheduledAt: new Date(Date.now() + offsetMin * 60 * 1000),
        status: "pending",
      },
    });
    await prisma.content.update({ where: { id: c.id }, data: { status: "SCHEDULED" } });
    offsetMin += 120; // giãn cách 2h giữa các bài
  }
}
