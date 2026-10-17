// Generated from the Pydantic contracts in grindstone.contracts. Do not edit.
// Regenerate with `make gen`; CI fails on drift (FF-02).

/**
 * Overall state of a service or one of its dependencies.
 */
export type HealthStatus = "ok" | "degraded" | "down";

export interface GrindstoneContracts {
  DependencyHealth: DependencyHealth;
  HealthStatus: HealthStatus;
  ServiceHealth: ServiceHealth;
}
/**
 * The state of one thing a service needs, such as its database.
 */
export interface DependencyHealth {
  /**
   * Short reason for a non-ok status, safe to show to the operator.
   */
  detail: string | null;
  /**
   * Stable name of the dependency, e.g. `postgres`.
   */
  name: string;
  status: HealthStatus;
}
/**
 * Readiness report of one Grindstone service.
 */
export interface ServiceHealth {
  dependencies: DependencyHealth[];
  schema_version: 1;
  service: "grindstone" | "agent-host" | "runner";
  status: HealthStatus;
  version: string;
}
