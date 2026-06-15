import type { ChannelType } from "@prisma/client";

export interface PublishInput {
  channelType: ChannelType;
  externalId: string; // page/oa id
  accessToken: string; // đã giải mã
  body: string;
  mediaUrls: string[];
}

export interface PublishResult {
  externalPostId: string;
  url?: string;
}

export interface ChannelConnector {
  type: ChannelType;
  publish(input: PublishInput): Promise<PublishResult>;
}

// Đăng ký connector theo loại kênh. Live connector cắm thêm khi có app review.
const registry = new Map<ChannelType, ChannelConnector>();

export function registerChannelConnector(c: ChannelConnector): void {
  registry.set(c.type, c);
}

export function getChannelConnector(type: ChannelType): ChannelConnector {
  const c = registry.get(type);
  if (!c) throw new Error(`Chưa có connector cho kênh ${type}`);
  return c;
}
