import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function AdsPage() {
  const tenant = await prisma.tenant.findFirst();
  const campaigns = tenant
    ? await prisma.adCampaign.findMany({
        where: { tenantId: tenant.id },
        orderBy: { createdAt: "desc" },
        include: { metrics: { orderBy: { at: "desc" }, take: 1 } },
      })
    : [];

  return (
    <main className="container">
      <h1>Ads</h1>
      <p className="muted">
        Ưu tiên Advantage+/Smart+ — agent quyết định ở cấp danh mục, không micro-manage bid.
      </p>
      {campaigns.length === 0 ? (
        <p className="empty">Chưa có campaign.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Nền tảng</th>
              <th>Mục tiêu</th>
              <th>Ngân sách/ngày</th>
              <th>Trạng thái</th>
              <th>CPL gần nhất</th>
              <th>ROAS</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => {
              const m = c.metrics[0];
              return (
                <tr key={c.id}>
                  <td>{c.platform}</td>
                  <td>{c.objective}</td>
                  <td>{c.dailyBudgetVnd.toLocaleString("vi-VN")}đ</td>
                  <td>
                    <span className="badge">{c.status}</span>
                  </td>
                  <td>{m?.cpl != null ? `${m.cpl.toLocaleString("vi-VN")}đ` : "—"}</td>
                  <td>{m?.roas ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </main>
  );
}
