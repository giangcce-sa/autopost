import type { ChannelType, ContentKind } from "@prisma/client";

export interface IntelPayload {
  competitors: { name: string; activity: string }[];
  trends: string[];
  recommendation: string;
  sources: string[];
  reliability: "high" | "medium" | "low";
}

export interface IdeaOut {
  bigIdea: string;
  angle: string;
  hook: string;
  serviceName?: string;
}

export interface ContentOut {
  kind: ContentKind;
  channel: ChannelType;
  body: string;
  hashtags?: string[];
}

export interface AdProposal {
  platform: "META_ADS" | "TIKTOK_ADS";
  serviceName?: string;
  objective: string;
  dailyBudgetVnd: number;
  rationale: string;
}

export type OptimizerAction = "keep" | "pause" | "scale" | "duplicate" | "reallocate";

export interface OptimizerDecision {
  campaignId: string;
  action: OptimizerAction;
  newBudgetVnd?: number;
  reason: string;
}

export interface ReplyOut {
  reply: string;
  isLead: boolean;
  lead?: { name?: string; phone?: string; need?: string; score?: number };
}

export interface CeoDecision {
  summary: string;
  goals?: { period: string; serviceName?: string; targetLeads?: number; targetCpaVnd?: number; targetRevenue?: number }[];
  decisions: string[];
  tasks: { agent: string; instruction: string }[];
}
