import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function GoalsPage() {
  const tenant = await prisma.tenant.findFirst();
  const goals = tenant
    ? await prisma.goal.findMany({
        where: { tenantId: tenant.id },
        orderBy: { createdAt: "desc" },
      })
    : [];

  return (
    <main className="container">
      <h1>Mục tiêu (CEO Agent)</h1>
      {goals.length === 0 ? (
        <p className="empty">Chưa có mục tiêu. CEO Agent sẽ đề xuất khi giao ban.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Kỳ</th>
              <th>Lead mục tiêu</th>
              <th>CPA mục tiêu</th>
              <th>Doanh thu (tham chiếu)</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {goals.map((g) => (
              <tr key={g.id}>
                <td>{g.period}</td>
                <td>{g.targetLeads ?? "—"}</td>
                <td>{g.targetCpaVnd ? `${g.targetCpaVnd.toLocaleString("vi-VN")}đ` : "—"}</td>
                <td>{g.targetRevenue ? `${g.targetRevenue.toLocaleString("vi-VN")}đ` : "—"}</td>
                <td>
                  <span className="badge">{g.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
