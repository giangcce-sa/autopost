import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const tenant = await prisma.tenant.findFirst();
  if (!tenant) {
    return (
      <main className="container">
        <h1>Chưa có tenant</h1>
        <p className="empty">
          Chạy <code>npm run db:seed</code> để tạo spa demo, sau đó gọi cron giao ban.
        </p>
      </main>
    );
  }

  const since = new Date();
  since.setHours(0, 0, 0, 0);

  const [newLeads, scheduled, published, activeCampaigns, costAgg, lastIntel, lastApproval] =
    await Promise.all([
      prisma.lead.count({ where: { tenantId: tenant.id, createdAt: { gte: since } } }),
      prisma.scheduledPost.count({ where: { tenantId: tenant.id, status: "pending" } }),
      prisma.scheduledPost.count({ where: { tenantId: tenant.id, status: "published" } }),
      prisma.adCampaign.count({ where: { tenantId: tenant.id, status: "active" } }),
      prisma.agentRun.aggregate({
        where: { tenantId: tenant.id, startedAt: { gte: since } },
        _sum: { costUsd: true },
      }),
      prisma.intelReport.findFirst({
        where: { tenantId: tenant.id },
        orderBy: { date: "desc" },
      }),
      prisma.approvalRequest.findFirst({
        where: { tenantId: tenant.id, kind: "daily_decision" },
        orderBy: { createdAt: "desc" },
      }),
    ]);

  const intel = lastIntel?.payload as { recommendation?: string } | undefined;
  const approval = lastApproval?.payload as { ceo?: { summary?: string } } | undefined;

  return (
    <main className="container">
      <h1>Tổng quan · {tenant.name}</h1>
      <p className="muted">
        Loại: {tenant.businessType} · Tự trị: {tenant.autonomyLevel} · Gói: {tenant.plan}
      </p>

      <div className="grid" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Lead hôm nay</h3>
          <div className="metric">{newLeads}</div>
        </div>
        <div className="card">
          <h3>Bài chờ đăng</h3>
          <div className="metric">{scheduled}</div>
        </div>
        <div className="card">
          <h3>Bài đã đăng</h3>
          <div className="metric">{published}</div>
        </div>
        <div className="card">
          <h3>Campaign active</h3>
          <div className="metric">{activeCampaigns}</div>
        </div>
        <div className="card">
          <h3>Chi phí AI hôm nay</h3>
          <div className="metric">${(costAgg._sum.costUsd ?? 0).toFixed(3)}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Quyết định CEO gần nhất</h3>
        <p>{approval?.ceo?.summary ?? "Chưa có. Gọi /api/cron/standup để chạy giao ban."}</p>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Tình báo gần nhất</h3>
        <p>{intel?.recommendation ?? "Chưa có dữ liệu tình báo."}</p>
      </div>
    </main>
  );
}
