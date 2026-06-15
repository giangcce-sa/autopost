import type { Channel, ChannelType, Tenant } from "@prisma/client";
import { prisma } from "./prisma";
import { decryptToken } from "./crypto";

export async function getActiveTenants(): Promise<Tenant[]> {
  return prisma.tenant.findMany();
}

export async function getTenantOrThrow(tenantId: string): Promise<Tenant> {
  const t = await prisma.tenant.findUnique({ where: { id: tenantId } });
  if (!t) throw new Error(`Không tìm thấy tenant ${tenantId}`);
  return t;
}

/** Kênh đăng bài (không phải ads) của tenant. */
export async function getPublishChannels(tenantId: string): Promise<Channel[]> {
  return prisma.channel.findMany({
    where: {
      tenantId,
      status: "active",
      type: { in: ["FACEBOOK_PAGE", "INSTAGRAM", "TIKTOK", "ZALO_OA"] },
    },
  });
}

export function channelToken(channel: Channel): string {
  // Mock mode: token có thể là chuỗi thường; live mode: giải mã.
  if (process.env.CONNECTOR_MODE === "live") return decryptToken(channel.accessToken);
  try {
    return decryptToken(channel.accessToken);
  } catch {
    return channel.accessToken;
  }
}

export const publishChannelTypes: ChannelType[] = [
  "FACEBOOK_PAGE",
  "INSTAGRAM",
  "TIKTOK",
  "ZALO_OA",
];
