import type { ChannelType } from "@prisma/client";

export interface CreateCampaignInput {
  platform: ChannelType; // META_ADS | TIKTOK_ADS
  accessToken: string;
  objective: string;
  dailyBudgetVnd: number;
  // Ưu tiên Advantage+/Smart+ — nền tảng tự lo bid/targeting/creative.
  useSmartCampaign?: boolean;
}

export interface AdsConnector {
  platform: ChannelType;
  createCampaign(input: CreateCampaignInput): Promise<{ externalId: string }>;
  setBudget(externalId: string, dailyBudgetVnd: number, accessToken: string): Promise<void>;
  pause(externalId: string, accessToken: string): Promise<void>;
}

const registry = new Map<ChannelType, AdsConnector>();
export function registerAdsConnector(c: AdsConnector): void {
  registry.set(c.platform, c);
}
export function getAdsConnector(platform: ChannelType): AdsConnector {
  const c = registry.get(platform);
  if (!c) throw new Error(`Chưa có ads connector cho ${platform}`);
  return c;
}
