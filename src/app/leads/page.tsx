import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function LeadsPage() {
  const tenant = await prisma.tenant.findFirst();
  const leads = tenant
    ? await prisma.lead.findMany({
        where: { tenantId: tenant.id },
        orderBy: { createdAt: "desc" },
        take: 100,
      })
    : [];

  return (
    <main className="container">
      <h1>Lead</h1>
      <p className="muted">
        Ranh giới hệ thống dừng ở lead — bàn giao thủ công sang phần mềm spa.
      </p>
      {leads.length === 0 ? (
        <p className="empty">Chưa có lead.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Tên</th>
              <th>SĐT</th>
              <th>Nhu cầu</th>
              <th>Nguồn</th>
              <th>Điểm</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.id}>
                <td>{l.name ?? "—"}</td>
                <td>{l.phone ?? "—"}</td>
                <td>{l.need ?? "—"}</td>
                <td className="muted">{l.source ?? "—"}</td>
                <td>{l.score ?? "—"}</td>
                <td>
                  <span className="badge">{l.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
