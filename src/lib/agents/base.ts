import type { Tenant } from "@prisma/client";
import { prisma } from "../prisma";
import { anthropic, checkAiBudget, estimateCostUsd } from "../anthropic";

export interface AgentContext {
  tenant: Tenant;
  agent: string; // "ceo" | "intel" | ...
  model: string;
  system: string;
  user: string;
  maxTokens?: number;
  /** Bật web_search server tool (cho Intel). Best-effort, fallback nếu không hỗ trợ. */
  webSearch?: boolean;
}

/** Trích JSON object/array đầu tiên từ text trả về của model. */
export function extractJson<T = unknown>(text: string): T {
  const trimmed = text.trim();
  // Bỏ ```json fences nếu có
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/);
  const candidate = fenced ? fenced[1] : trimmed;
  const start = candidate.search(/[[{]/);
  if (start === -1) throw new Error("Không tìm thấy JSON trong phản hồi model");
  // Tìm dấu đóng cân bằng
  const openCh = candidate[start];
  const closeCh = openCh === "{" ? "}" : "]";
  let depth = 0;
  for (let i = start; i < candidate.length; i++) {
    if (candidate[i] === openCh) depth++;
    else if (candidate[i] === closeCh) {
      depth--;
      if (depth === 0) {
        return JSON.parse(candidate.slice(start, i + 1)) as T;
      }
    }
  }
  throw new Error("JSON trong phản hồi model không cân bằng");
}

/**
 * Chạy một agent: gọi Claude, ghi log AgentRun (token + chi phí), trả về text.
 * Áp trần chi phí AI/ngày trước khi gọi.
 */
export async function runAgent(ctx: AgentContext): Promise<{ text: string; runId: string }> {
  await checkAiBudget(ctx.tenant.id, ctx.tenant.aiBudgetUsdDaily);

  const run = await prisma.agentRun.create({
    data: { tenantId: ctx.tenant.id, agent: ctx.agent, model: ctx.model, status: "running" },
  });

  try {
    const params: Record<string, unknown> = {
      model: ctx.model,
      max_tokens: ctx.maxTokens ?? 4096,
      system: ctx.system,
      messages: [{ role: "user", content: ctx.user }],
    };
    if (ctx.webSearch) {
      params.tools = [{ type: "web_search_20260209", name: "web_search" }];
    }

    // Cast any: một số field (server tools) phụ thuộc phiên bản SDK.
    const res = (await anthropic().messages.create(params as never)) as {
      content: Array<{ type: string; text?: string }>;
      usage: { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number };
    };

    const text = res.content
      .filter((b) => b.type === "text" && typeof b.text === "string")
      .map((b) => b.text as string)
      .join("\n")
      .trim();

    const inTok = res.usage.input_tokens ?? 0;
    const outTok = res.usage.output_tokens ?? 0;
    const cacheTok = res.usage.cache_read_input_tokens ?? 0;
    const cost = estimateCostUsd(ctx.model, inTok, outTok);

    await prisma.agentRun.update({
      where: { id: run.id },
      data: {
        inputTokens: inTok,
        outputTokens: outTok,
        cacheReadTokens: cacheTok,
        costUsd: cost,
        status: "ok",
        finishedAt: new Date(),
      },
    });

    return { text, runId: run.id };
  } catch (err) {
    await prisma.agentRun.update({
      where: { id: run.id },
      data: {
        status: "failed",
        error: err instanceof Error ? err.message : String(err),
        finishedAt: new Date(),
      },
    });
    throw err;
  }
}

/** Chạy agent và parse JSON kết quả. */
export async function runAgentJson<T>(ctx: AgentContext): Promise<{ data: T; runId: string }> {
  const { text, runId } = await runAgent(ctx);
  return { data: extractJson<T>(text), runId };
}
