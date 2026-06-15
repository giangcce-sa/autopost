import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

const STATUS_CLASS: Record<string, string> = {
  APPROVED: "good",
  PUBLISHED: "good",
  SCHEDULED: "good",
  PENDING_APPROVAL: "warn",
  DRAFT: "warn",
  REJECTED: "bad",
  FAILED: "bad",
};

export default async function ContentPage() {
  const tenant = await prisma.tenant.findFirst();
  const contents = tenant
    ? await prisma.content.findMany({
        where: { tenantId: tenant.id },
        orderBy: { createdAt: "desc" },
        take: 50,
      })
    : [];

  return (
    <main className="container">
      <h1>Nội dung</h1>
      {contents.length === 0 ? (
        <p className="empty">Chưa có nội dung. Chạy giao ban để Content Agent sinh bài.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Kênh</th>
              <th>Loại</th>
              <th>Nội dung</th>
              <th>Trạng thái</th>
              <th>Cờ tuân thủ</th>
            </tr>
          </thead>
          <tbody>
            {contents.map((c) => (
              <tr key={c.id}>
                <td>{c.channel}</td>
                <td>{c.kind}</td>
                <td style={{ maxWidth: 420 }}>{c.body.slice(0, 200)}</td>
                <td>
                  <span className={`badge ${STATUS_CLASS[c.status] ?? ""}`}>{c.status}</span>
                </td>
                <td className="muted">{c.complianceFlags.join("; ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
