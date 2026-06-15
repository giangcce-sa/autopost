import type { Tenant } from "@prisma/client";
import { runOptimizer } from "../agents";
import type { OptimizerDecision } from "../agents";

// Nhịp Optimizer mỗi 3h — quyết định cấp danh mục campaign (mục 5.1).
export async function runOptimizeCycle(tenant: Tenant): Promise<OptimizerDecision[]> {
  return runOptimizer(tenant);
}
