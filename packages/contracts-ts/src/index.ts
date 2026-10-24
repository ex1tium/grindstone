// Generated from the Pydantic contracts in grindstone.contracts. Do not edit.
// Regenerate with `make gen`; CI fails on drift (FF-02).

/**
 * The kind of principal that authored a revision.
 */
export type AuthorKind = "person" | "agent" | "policy" | "system";
/**
 * Overall state of a service or one of its dependencies.
 */
export type HealthStatus = "ok" | "degraded" | "down";
/**
 * How an error is handled, and by whom.
 */
export type ErrorClass = "validation" | "rule" | "authority" | "limit" | "transient" | "internal";
export type JsonValue = unknown;

export interface GrindstoneContracts {
  AuthorKind: AuthorKind;
  BlobRef: BlobRef;
  BlobSetSubject: BlobSetSubject;
  BlobSubject: BlobSubject;
  DependencyHealth: DependencyHealth;
  ErrorClass: ErrorClass;
  ErrorEnvelope: ErrorEnvelope;
  GitCommitSubject: GitCommitSubject;
  HealthStatus: HealthStatus;
  ItemRef: ItemRef;
  ItemRevisionSubject: ItemRevisionSubject;
  JsonValue: JsonValue;
  Provenance: Provenance;
  RunManifest: RunManifest;
  ServiceHealth: ServiceHealth;
}
/**
 * Content in the blob store, addressed by the hash of its bytes.
 */
export interface BlobRef {
  media_type: string;
  schema_version: 1;
  sha256: string;
  size: number;
}
/**
 * A set of blobs, held sorted and unique by content hash.
 */
export interface BlobSetSubject {
  kind: "blob_set";
  members: BlobRef[];
  schema_version: 1;
}
/**
 * A single blob.
 */
export interface BlobSubject {
  blob: BlobRef;
  kind: "blob";
  schema_version: 1;
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
 * One service error, in the shape every interface returns.
 */
export interface ErrorEnvelope {
  code: string;
  detail: {
    [k: string]: JsonValue | undefined;
  };
  error_class: ErrorClass;
  message: string;
  retryable: boolean;
  schema_version: 1;
}
/**
 * A commit in a repository.
 */
export interface GitCommitSubject {
  kind: "git_commit";
  repo: string;
  schema_version: 1;
  sha: string;
}
/**
 * One item revision, pinned by its semantic hash.
 */
export interface ItemRef {
  hash: string;
  id: string;
  schema_version: 1;
}
/**
 * An item revision, proven as an object in its own right.
 */
export interface ItemRevisionSubject {
  item: ItemRef;
  kind: "item_revision";
  schema_version: 1;
}
/**
 * Carried by every revision: the author, what it came through, and the reason.
 */
export interface Provenance {
  author: string;
  author_kind: AuthorKind;
  changeset: string | null;
  decision: string | null;
  finding: string | null;
  reason: string;
  schema_version: 1;
  task: string | null;
}
/**
 * The pinned inputs, configuration and prompts of one task run.
 */
export interface RunManifest {
  capability: string;
  capability_hash: string;
  context_pack_hash: string;
  factory: string;
  factory_version: string;
  instance_config_hash: string;
  items: ItemRef[];
  model: string;
  project_config_hash: string;
  prompts: BlobRef[];
  provider: string;
  run: string;
  schema_version: 1;
  subject: (GitCommitSubject | BlobSubject | BlobSetSubject | ItemRevisionSubject) | null;
  task: string;
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
