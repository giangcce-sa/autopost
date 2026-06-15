import type { ChannelType, Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { MODELS } from "../anthropic";
import { runAgentJson } from "./base";
import { checkContent, complianceInstructions } from "../compliance/guardrail";
import type { ContentOut, IdeaOut } from "./types";

// Content Team: sinh bài đa kênh theo brand voice + guardrail tuân thủ.
export async function runContent(
  tenant: Tenant,
  idea: IdeaOut,
  channels: ChannelType[],
): Promise<string[]> {
  const system = [
    "Bạn là Content Creator cho spa tại Việt Nam, viết bài mạng xã hội hấp dẫn, tự nhiên.",
    tenant.brandVoice ? `Brand voice: ${tenant.brandVoice}` : "",
    complianceInstructions(tenant.businessType),
    'Trả về DUY NHẤT JSON: {"contents":[{"kind":"EDUCATION|CASE_STUDY|FEEDBACK|PROMOTION|TREND","channel":"FACEBOOK_PAGE|INSTAGRAM|TIKTOK|ZALO_OA","body","hashtags":[string]}]}',
  ]
    .filter(Boolean)
    .join("\n");

  const user = [
    `Big Idea: ${idea.bigIdea}`,
    `Angle: ${idea.angle}`,
    `Hook: ${idea.hook}`,
    `Viết cho các kênh: ${channels.join(", ")}. Mỗi kênh 1 bài phù hợp định dạng kênh đó.`,
  ].join("\n");

  const { data } = await runAgentJson<{ contents: ContentOut[] }>({
    tenant,
    agent: "content",
    model: MODELS.default,
    system,
    user,
    maxTokens: 3072,
  });

  const created: string[] = [];
  for (const c of data.contents ?? []) {
    const fullBody = c.hashtags?.length ? `${c.body}\n\n${c.hashtags.join(" ")}` : c.body;
    const compliance = checkContent(fullBody, {
      businessType: tenant.businessType,
      isCosmetic: c.kind === "PROMOTION",
    });
    const status = !compliance.ok
      ? "REJECTED"
      : compliance.needsHumanReview
        ? "PENDING_APPROVAL"
        : "APPROVED";

    const content = await prisma.content.create({
      data: {
        tenantId: tenant.id,
        kind: c.kind,
        channel: c.channel,
        body: fullBody,
        mediaUrls: [],
        status,
        complianceFlags: compliance.flags,
      },
    });
    created.push(content.id);
  }
  return created;
}
