import type { ChannelType } from "@prisma/client";
import { registerAdsConnector, type AdsConnector } from "./ads";

function makeMock(platform: ChannelType): AdsConnector {
  return {
    platform,
    async createCampaign(input) {
      const id = `mock_camp_${platform.toLowerCase()}_${Date.now()}`;
      console.log(
        `[mock-ads:${platform}] tạo campaign (${input.useSmartCampaign ? "Smart/Advantage+" : "manual"}) ngân sách ${input.dailyBudgetVnd}đ/ngày → ${id}`,
      );
      return { externalId: id };
    },
    async setBudget(externalId, dailyBudgetVnd) {
      console.log(`[mock-ads:${platform}] set ngân sách ${externalId} = ${dailyBudgetVnd}đ/ngày`);
    },
    async pause(externalId) {
      console.log(`[mock-ads:${platform}] pause ${externalId}`);
    },
  };
}

let registered = false;
export function ensureMockAdsConnectors(): void {
  if (registered) return;
  registerAdsConnector(makeMock("META_ADS"));
  registerAdsConnector(makeMock("TIKTOK_ADS"));
  registered = true;
}
