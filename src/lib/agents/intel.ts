import type { Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { MODELS } from "../anthropic";
import { runAgentJson } from "./base";
import type { IntelPayload } from "./types";

// Phòng Tình Báo: theo dõi đối thủ/trend. Ưu tiên nguồn chính thức + web_search;
// ghi rõ độ tin cậy (degrade gracefully) — xem design doc mục 14.
export async function runIntel(tenant: Tenant): Promise<IntelPayload> {
  const services = await prisma.service.findMany({
    where: { tenantId: tenant.id, active: true },
  });

  const system = [
    "Bạn là Trưởng phòng Tình báo Marketing cho một spa tại Việt Nam.",
    "Nhiệm vụ: tổng hợp động thái đối thủ, xu hướng thị trường làm đẹp theo mùa, và đề xuất dịch vụ nên đẩy.",
    "Chỉ dùng dữ liệu công khai. Nếu không chắc, hạ reliability và nói rõ là suy luận.",
    'Trả về DUY NHẤT JSON: {"competitors":[{"name","activity"}],"trends":[string],"recommendation":string,"sources":[string],"reliability":"high|medium|low"}',
  ].join("\n");

  const user = [
    `Spa: ${tenant.name}. Dịch vụ: ${services.map((s) => s.name).join(", ") || "(chưa khai báo)"}.`,
    `Hôm nay: ${new Date().toISOString().slice(0, 10)}.`,
    "Hãy nghiên cứu trend mùa hiện tại & động thái đối thủ ngành spa, rồi đề xuất dịch vụ trọng tâm.",
  ].join("\n");

  const { data } = await runAgentJson<IntelPayload>({
    tenant,
    agent: "intel",
    model: MODELS.default,
    system,
    user,
    maxTokens: 2048,
    webSearch: true,
  });

  await prisma.intelReport.create({
    data: { tenantId: tenant.id, payload: data as object },
  });
  return data;
}
