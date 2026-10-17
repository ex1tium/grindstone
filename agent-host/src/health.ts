import type { ServiceHealth } from "@grindstone/contracts";

export const VERSION = "0.0.0";

/** Readiness of the agent host. M0 has no dependencies to probe yet. */
export function health(): ServiceHealth {
  return {
    schema_version: 1,
    service: "agent-host",
    version: VERSION,
    status: "ok",
    dependencies: [],
  };
}
