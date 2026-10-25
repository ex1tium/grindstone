// Generated from the Pydantic contracts in grindstone.contracts. Do not edit.
// Regenerate with `make gen`; CI fails on drift (FF-02).

export type JsonValue = unknown;
/**
 * Where an answer was given, from the authenticated session (SPEC-10).
 */
export type Channel = "ui" | "api" | "vscode" | "plugin";
/**
 * The kind of principal that authored a revision.
 */
export type AuthorKind = "person" | "agent" | "policy" | "system";
/**
 * How a decision may be answered; set only by the kernel code that raises it (Concepts).
 */
export type DecisionFlag =
  | "scope_expansion"
  | "principle"
  | "untrusted"
  | "rounds_exhausted"
  | "revert_conflict"
  | "cap_reached"
  | "irreversible";
export type RecommendationSource = "fixed" | "agent" | "advisor";
/**
 * The decision lifecycle; `expired` is reserved for SPEC-15 and has no writer in M1.
 */
export type DecisionState = "open" | "answered" | "superseded" | "expired";
/**
 * Overall state of a service or one of its dependencies.
 */
export type HealthStatus = "ok" | "degraded" | "down";
/**
 * How an error is handled, and by whom.
 */
export type ErrorClass = "validation" | "rule" | "authority" | "limit" | "transient" | "internal";

export interface GrindstoneContracts {
  Answer: Answer;
  AuthorKind: AuthorKind;
  BlobRef: BlobRef;
  BlobSetSubject: BlobSetSubject;
  BlobSubject: BlobSubject;
  Channel: Channel;
  ConfigInvalid: ConfigInvalid;
  Decision: Decision;
  DecisionAnswered: DecisionAnswered;
  DecisionFlag: DecisionFlag;
  DecisionRaised: DecisionRaised;
  DecisionScope: DecisionScope;
  DecisionState: DecisionState;
  DecisionSuperseded: DecisionSuperseded;
  DependencyHealth: DependencyHealth;
  ErrorClass: ErrorClass;
  ErrorEnvelope: ErrorEnvelope;
  EventEnvelope: EventEnvelope;
  FactoryLoaded: FactoryLoaded;
  FactoryRefused: FactoryRefused;
  GitCommitSubject: GitCommitSubject;
  HealthStatus: HealthStatus;
  ItemRef: ItemRef;
  ItemRevisionSubject: ItemRevisionSubject;
  JsonValue: JsonValue;
  ProjectConfigured: ProjectConfigured;
  Provenance: Provenance;
  Recommendation: Recommendation;
  RecommendationSource: RecommendationSource;
  RunManifest: RunManifest;
  ServiceHealth: ServiceHealth;
}
/**
 * An accepted answer: what, by whom, through which channel and against which context.
 *
 * REQ-0417.
 */
export interface Answer {
  answer: {
    [k: string]: JsonValue | undefined;
  };
  answered_by: string;
  at: string;
  channel: Channel;
  client_key: string;
  context_hash_seen: string;
  decision: string;
  schema_version: 1;
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
 * A project's current configuration is invalid, so the project is paused.
 */
export interface ConfigInvalid {
  problems: string[];
  schema_version: 1;
  type: "config.invalid";
}
/**
 * One decision record (REQ-0416).
 */
export interface Decision {
  context_hash: string;
  flags: DecisionFlag[];
  id: string;
  kind: string;
  payload: {
    [k: string]: JsonValue | undefined;
  };
  project: string;
  raised_at: string;
  raised_by: string;
  recommendation: Recommendation;
  schema_version: 1;
  scope: DecisionScope;
  state: DecisionState;
  superseded_by: string | null;
  title: string;
}
/**
 * The recommended answer, why, and who recommends it.
 */
export interface Recommendation {
  answer: {
    [k: string]: JsonValue | undefined;
  };
  reason: string;
  source: RecommendationSource;
}
/**
 * The records a decision is about.
 */
export interface DecisionScope {
  changeset: string | null;
  delivery: string | null;
  run: string | null;
  task: string | null;
}
export interface DecisionAnswered {
  decision: string;
  kind: string;
  schema_version: 1;
  type: "decision.answered";
}
export interface DecisionRaised {
  decision: string;
  flags: DecisionFlag[];
  kind: string;
  schema_version: 1;
  type: "decision.raised";
}
export interface DecisionSuperseded {
  decision: string;
  replacement: string;
  schema_version: 1;
  type: "decision.superseded";
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
 * One recorded event: its stream, its place in it, and the event model's fields.
 *
 * `type` and `event_version` are the event model's `type` and
 * `schema_version`; `payload` holds its other fields, so the envelope
 * round-trips to the model.
 */
export interface EventEnvelope {
  event_id: string;
  event_version: number;
  occurred_at: string;
  payload: {
    [k: string]: JsonValue | undefined;
  };
  project: string;
  schema_version: 1;
  seq: number;
  type: string;
}
/**
 * A factory passed its load at start-up.
 */
export interface FactoryLoaded {
  factory: string;
  manifest_hash: string;
  schema_version: 1;
  type: "factory.loaded";
  version: string;
}
/**
 * A factory was refused at start-up, with the `file:field: rule` lines that failed.
 */
export interface FactoryRefused {
  factory: string;
  problems: string[];
  schema_version: 1;
  type: "factory.refused";
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
 * A project's configuration gained a version.
 */
export interface ProjectConfigured {
  hash: string;
  schema_version: 1;
  type: "project.configured";
  version: number;
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
