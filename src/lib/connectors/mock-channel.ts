import type { ChannelType } from "@prisma/client";
import { registerChannelConnector, type ChannelConnector } from "./channel";

// Connector mock/sandbox — dùng khi CONNECTOR_MODE=mock (chờ app review).
// In log thay vì gọi API thật, trả về id giả lập.
function makeMock(type: ChannelType): ChannelConnector {
  return {
    type,
    async publish(input) {
      const id = `mock_${type.toLowerCase()}_${Date.now()}_${Math.floor(Math.random() * 1e4)}`;
      console.log(`[mock-channel:${type}] đăng bài → ${id}\n${input.body.slice(0, 120)}...`);
      return { externalPostId: id, url: `https://example.test/${id}` };
    },
  };
}

const TYPES: ChannelType[] = ["FACEBOOK_PAGE", "INSTAGRAM", "TIKTOK", "ZALO_OA"];

let registered = false;
export function ensureMockChannelConnectors(): void {
  if (registered) return;
  for (const t of TYPES) registerChannelConnector(makeMock(t));
  registered = true;
}
