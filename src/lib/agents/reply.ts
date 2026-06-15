import type { ChannelType, Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { MODELS } from "../anthropic";
import { runAgentJson } from "./base";
import type { ReplyOut } from "./types";

interface Msg {
  role: "customer" | "agent";
  text: string;
  at: string;
}

// Social Care + Lead Collector hợp nhất: trả lời inbox & phát hiện/gom lead.
export async function runReply(
  tenant: Tenant,
  channel: ChannelType,
  externalUserId: string,
  customerMessage: string,
): Promise<ReplyOut> {
  const services = await prisma.service.findMany({
    where: { tenantId: tenant.id, active: true },
  });

  const convo = await prisma.conversation.findUnique({
    where: { tenantId_channel_externalUserId: { tenantId: tenant.id, channel, externalUserId } },
  });
  const history: Msg[] = (convo?.messages as Msg[] | undefined) ?? [];

  const system = [
    "Bạn là nhân viên tư vấn (Social Care) của spa tại Việt Nam, thân thiện, chuyên nghiệp.",
    "Mục tiêu: tư vấn ngắn gọn + xin SĐT để tư vấn kỹ/đặt lịch. Không thổi phồng, không hứa chữa bệnh.",
    `Dịch vụ & giá: ${services.map((s) => `${s.name}${s.priceFrom ? ` từ ${s.priceFrom}đ` : ""}`).join("; ") || "(liên hệ)"}.`,
    "Phát hiện lead khi khách để lại SĐT hoặc thể hiện ý định rõ ràng.",
    'Trả về DUY NHẤT JSON: {"reply":string,"isLead":boolean,"lead":{"name":string,"phone":string,"need":string,"score":number}}',
  ].join("\n");

  const user = [
    `Lịch sử: ${JSON.stringify(history.slice(-8))}`,
    `Tin nhắn mới của khách: ${customerMessage}`,
  ].join("\n");

  const { data } = await runAgentJson<ReplyOut>({
    tenant,
    agent: "reply",
    model: MODELS.cheap,
    system,
    user,
    maxTokens: 1024,
  });

  // Cập nhật hội thoại.
  const now = new Date().toISOString();
  const newMessages: Msg[] = [
    ...history,
    { role: "customer", text: customerMessage, at: now },
    { role: "agent", text: data.reply, at: now },
  ];

  let leadId: string | undefined;
  if (data.isLead && data.lead) {
    const lead = await prisma.lead.create({
      data: {
        tenantId: tenant.id,
        name: data.lead.name ?? null,
        phone: data.lead.phone ?? null,
        need: data.lead.need ?? null,
        score: data.lead.score ?? null,
        source: `chat:${channel}`,
        status: "NEW",
      },
    });
    leadId = lead.id;
  }

  await prisma.conversation.upsert({
    where: { tenantId_channel_externalUserId: { tenantId: tenant.id, channel, externalUserId } },
    create: {
      tenantId: tenant.id,
      channel,
      externalUserId,
      messages: newMessages as object,
      leadId: leadId ?? null,
    },
    update: { messages: newMessages as object, ...(leadId ? { leadId } : {}) },
  });

  return data;
}
