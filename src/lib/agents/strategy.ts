import type { Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { MODELS } from "../anthropic";
import { runAgentJson } from "./base";
import type { IdeaOut, IntelPayload } from "./types";

// Creative Director / Strategy: từ tình báo → Big Idea / Angle / Hook.
export async function runStrategy(tenant: Tenant, intel: IntelPayload): Promise<IdeaOut[]> {
  const system = [
    "Bạn là Creative Director cho một spa tại Việt Nam.",
    "Từ dữ liệu tình báo, tạo 3 ý tưởng marketing: mỗi ý tưởng gồm Big Idea, Angle, Hook.",
    "Hook phải tò mò, đúng tâm lý khách hàng spa, KHÔNG thổi phồng/sai sự thật.",
    'Trả về DUY NHẤT JSON: {"ideas":[{"bigIdea","angle","hook","serviceName"}]}',
  ].join("\n");

  const user = `Tình báo: ${JSON.stringify(intel)}\nĐề xuất: ${intel.recommendation}`;

  const { data } = await runAgentJson<{ ideas: IdeaOut[] }>({
    tenant,
    agent: "strategy",
    model: MODELS.reasoning,
    system,
    user,
    maxTokens: 2048,
  });

  const ideas = data.ideas ?? [];
  await prisma.idea.createMany({
    data: ideas.map((i) => ({
      tenantId: tenant.id,
      bigIdea: i.bigIdea,
      angle: i.angle ?? null,
      hook: i.hook ?? null,
    })),
  });
  return ideas;
}
