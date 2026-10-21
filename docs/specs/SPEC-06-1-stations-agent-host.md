# SPEC-06 part 1 — Stations and the agent host
Status: accepted (by the operator, 19 October 2026, after the reviews in `docs/specs/reviews/`) · Milestone: M1
Kind: kernel · Owns:
- `grindstone.stations`: agent-user bindings, sessions, workspace lifecycle, the host adapter and its event intake, reconciliation, the activity registry, the runner job envelope and dispatch;
- the SDK ports `WorkspaceProvider` and `SubjectResolver`, with `RunContext`, `Materialization` and `CollectOutcome`;
- the agent host's core in `agent-host/`: control API, backend wrapper, signed events, the scripted agent preset.

Compact walking-skeleton specification (Planning playbook). SPEC-06 is split into two numbered parts, as the playbook allows, so that the specification graph has no cycle: part 1 (this file) ← SPEC-08 ← part 2 (`SPEC-06-2-task-runs.md`). Review: by a session that did not write it, then the operator.

## 1. Purpose

Work runs on stations, and the control plane must be able to drive them while trusting nothing they say beyond a signed, typed event (ADR-15, ADR-17). This part gives `work` (part 2) and `evidence` (SPEC-08) everything they need from a station:
- a fresh workspace per run, owned by one agent user for the run's life;
- sessions created, prompted and disposed exactly once per key;
- every host event verified, de-duplicated and handed to the workflow waiting for it;
- a lost host noticed;
- check jobs handed to the runner and read back.

It also builds the host core ADR-42 describes, so correctness never depends on a session surviving a restart.

## 2. Scope

In scope:
- **Agent users.** Binding a run to one agent user from the pool for its whole life.
- **Workspaces.** Their lifecycle through the workspace provider and the subject resolver, with archives extracted by the host as the run's agent user.
- **Sessions.** Create, prompt, permission answers, cancel, dispose, list, with idempotency keys.
- **Host events.** Signature, de-duplication, ordering, activity, routing to the waiting workflow, transcripts.
- **Reconciliation** after a host restart.
- **The activity registry:** last activity and open kernel calls per run.
- **Runner jobs:** the envelope and its dispatch.
- **SDK ports:** `WorkspaceProvider`, `SubjectResolver` and their contracts.
- **The agent host core:** control API server, backend wrapper, event signer, the scripted preset (ADR-19).

Out of scope:
- **Agent accounts and placement by quota** (ADR-48, foundation v4.10): SPEC-17 (M3). In M1 the station serves one account; with more accounts the agent-user pool (OQ-0604) grows with the lanes.
- **Tasks, runs, turns, reports, matching, templates, context packs, liveness rules, failure causes, suspension:** part 2.
- **Users, file modes, secrets, the helper that runs commands as an agent user, the Claude preset's launcher:** SPEC-05.
- **The runner's executors and the meaning of job payloads:** SPEC-08.
- **Workspace contents and copy-back:** SPEC-09's provider.
- **AHP for browsers and VS Code, steering from them:** SPEC-22. The host forwards steering events, which are recorded.

## 3. Foundation links

Implements:
- **ADR-15, as amended by ADR-42.** A thin host on `@ahpd/sdk`, its packages unmodified behind a backend wrapper; a typed control API, idempotent on client keys; HMAC-signed, at-least-once events with IDs and turn numbers; permission answers only through the control API; correctness never depends on a session surviving a restart.
- **ADR-17.** T1 agent stations; T0 as a read-only workspace on a T1 station; no station holds a control-plane credential.
- **ADR-19.** A scripted ACP agent preset replays fixture scripts.
- **ADR-41.** No Claude-specific path in the host core or the kernel: agents are presets, per-session options are agent-neutral, and the scripted preset is a second ACP implementation on every commit.
- **ADR-27, kernel side.** The kernel sees a workspace only through the provider's `prepare`, `collect` and `discard`, and knows `git_commit` only as a subject kind.
- **I-09.** The control plane never runs work content: it reads workspace files only through the provider, and runner results only as a parsed file.
- **I-15, in part.** A prover's workspace is materialized fresh from the subject, never the maker's.

Delivers:
- **Supports M1-04** (delivered by SPEC-02): workspace preparation, session creation, prompts, disposal, collect and job dispatch are registered external steps, and the replay of duplicate host events is idempotent, each with a crash-and-resume test (AC-0609-1, AC-0616-1, AC-0621-1).
- Part 2 delivers this specification's share of M1-01, M1-03 and M1-06, on the services here.

Depends on:
- **SPEC-01:** `SubjectRef`, `BlobRef`, record IDs, errors.
- **SPEC-02:** external steps, deterministic workflow IDs, keyed messages, the check lane, blobs.
- **SPEC-03:** registries (workspace providers, subject resolvers), contexts, instance sections, events.
- **SPEC-05:** agent users, the helper, the people directory, the Claude preset's launcher, listeners and secrets.

Scenarios: K1 step 3 (dispatch to a T1 station, session create keyed by run) and step 5 (the workspace collected through the provider).

## 4. Requirements

REQ-0606: Each run has a fresh workspace prepared by its capability's workspace provider (writing) or materialized from its subject by the subject's resolver (read-only), owned by the run's bound agent user, and never shared with another run.
REQ-0609: Every call to the host carries an idempotency key derived from the run and turn; replaying a call returns the original result, and a session is never created twice for one key.
REQ-0616: Host events are accepted only with a valid HMAC over their canonical JSON under the host event key; a duplicate event ID is acknowledged and ignored, and a forged, tampered or out-of-order event is refused and logged.
REQ-0617: The host control API refuses any call without the host control key, and serves `create_session`, `prompt`, `answer_permission`, `cancel`, `dispose`, `list`, `prepare_workspace`, `discard_workspace` and `stop_user`, each idempotent on its client key.
REQ-0618: The backend wrapper builds each agent's environment from scratch from its preset's allow-list, gives the session its kernel MCP server with the per-task bearer token in its headers, and reads both from the host's own session record, never from AHP session configuration.
REQ-0619: After a host restart, `stations` reconciles from `list()` and from each event's host boot ID: any session it believes live that the host does not list is reported `host_lost` to the workflow waiting on it.
REQ-0620: The scripted preset replays a fixture script of kernel tool calls, file writes, permission requests and turn ends through ACP and MCP, and is selectable for every capability by instance configuration only.
REQ-0621: Runner jobs are written as job directories with a typed envelope, picked up only once complete, and a job with no result by its timeout is recorded as an `error` outcome.
REQ-0623: A run is bound to one agent user from the station's pool when its workspace is prepared, every session of the run runs as that user, no two unfinished runs share a user, and the binding is released only when the run's workspace is discarded.
REQ-0624: The SDK ports, protocols in `grindstone.contracts.ports` (SPEC-03, DEC-0308), `WorkspaceProvider` (`prepare`, `collect`, `discard`) and `SubjectResolver` (`materialize`, `read_file`) take a kernel-built `RunContext` or `Context`, and `collect` returns a `CollectOutcome` with the subject, extra checks, permission requests and prover context, or a typed refusal.
REQ-0625: The host delivers each session's events one at a time in sequence order and does not send the next until the current one is acknowledged, so a refused event never sits behind a later one.
REQ-0626: Per-session options are agent-neutral (model, effort, permission categories, tool timeout, read-only); each preset maps them to its agent's own settings, and nothing in `stations` or the host core names an agent-specific setting.
REQ-0629: Before a run's collect, and before its agent user is released, every process of that user is stopped and the host confirms that none remains; collect and release do not proceed until it has.

## 5. Design

**Contracts** (`grindstone.contracts.stations`, `.host`; schema version 1 each):

| Model | Fields |
| --- | --- |
| `SessionOptions` | `preset`, `model`, `effort`, `permissions` (`allow` categories, `otherwise`: `deny`), `tool_timeout_seconds`, `read_only`, `script` (scripted preset only) |
| `HostEvent` | `event_id` (UUIDv7), `host_boot`, `seq` (per session), `session`, `run`, `turn`, `type`, `at`, `payload`, `sig` |
| `RunnerJob` | `job_id`, `checks`, `shape`, `timeout_s`, `payload` (shape-specific, SPEC-08), `env` (declared environment) |
| `RunnerResult` | `job_id`, `status` (`completed`, `error`), `outputs` (shape-specific, SPEC-08), `started_at`, `ended_at` |

SDK contracts (exported by SDK 0.1.0, SPEC-03):
- `RunContext` extends `Context` with `run`, `task`, `mode`, `workspace_ref` and `base` (the subject the run starts from, once known).
- `Materialization`: `archive` (a path in the staging area), `base: SubjectRef | None`.
- `CollectOutcome`:
  - `subject: SubjectRef`;
  - `extra_checks: tuple[CheckSpec, ...]`, which the kernel adds and never removes;
  - `permission_requests` (each an action and a reason);
  - `prover_context: tuple[BlobRef, ...]`: blobs every prover of this subject is given, for example a diff against the base (SPEC-09);
  - or `refused`, with the refused paths and the cause.

Kernel error codes declared here (in `grindstone.contracts.errors`):
- transient: `host_unavailable`, `station_unavailable`, `agent_user_busy` (a stop that did not complete in its bound wait; the step retries, and collect never runs while it fails);
- limit: `agent_user_unavailable`;
- internal: `event_rejected`.

Events: `session.created`, `session.ended`, `workspace.prepared`, `workspace.discarded`.

**Agent users (REQ-0623, DEC-0606).** SPEC-05 creates a pool of agent users per agent station (seed 8, `gs-agent-1` to `gs-agent-8`). `stations.agent_users (station, user, run)` binds one to a run:
- `bind(run)` takes a free user in one unit of work, skipping locked rows. If none is free the run waits and retries, and the wait is shown as `agent_user_unavailable` on the run.
- Every session of the run runs as that user.
- `release(run)` runs after the workspace is discarded, on every path: success, failure and cancellation.

Lanes are separate: they are DBOS queues (SPEC-02) that bound how many sessions run at once. A run suspended on a decision holds its user and its workspace, never a lane. With the seeds (one writing and four read-only lane slots), eight users leave room for three suspended runs before a new run waits for a user; the pool size is instance configuration.

**Workspaces (REQ-0606).**
1. `prepare_workspace(run, task, mode, provider_or_subject)` (external step, key `<run>:prepare`). `stations` cannot read tasks, so `work` passes the task's ID, its mode, and the workspace provider with the base it starts from (writing) or the subject (read-only), from which the step builds the `RunContext`:
   - bind the agent user;
   - writing workspace: call `provider.prepare(ctx)`, which writes an archive into `workspaces/staging/<run>.tar` and returns the `Materialization` with its base;
   - read-only workspace: call the subject's resolver to `materialize` the subject into a staging directory, which `stations` archives the same way, so a prover's copy comes from the subject alone (I-15);
   - ask the host to create `agents/<user>/<run>/` and extract the archive into it as the bound user (SPEC-05's helper: the host reads the archive and streams it to an extractor running as the user);
   - delete the archive.
2. `collect(run)` (external step, key `<run>:collect`): first ask the host to stop every process of the run's agent user and wait until none remains (REQ-0629), then call `provider.collect(ctx)` and return its `CollectOutcome`. The kernel never reads the workspace itself. With no process of that user alive, nothing can change the workspace while the provider reads it.
3. `discard_workspace(run)` (external steps): ask the host to stop every process of the bound user (REQ-0629), remove the directory as that user, call `provider.discard(ctx)`, then release the user, so no process of one run survives into the next run bound to the same user.

**Host client (REQ-0609, REQ-0617).** HTTP/JSON to `agent-host:8090` (SPEC-05), bearer `host_control_key`, header `Grindstone-Host-Protocol: 1`, errors as `ErrorEnvelope`.

| Call | Body | Effect |
| --- | --- | --- |
| `POST /v1/workspaces` | `key`, `run`, `user`, `archive` | Creates `agents/<user>/<run>/` and extracts the archive as that user; an existing one with the same key is a no-op |
| `DELETE /v1/workspaces/<run>` | `key` | Removes it as its user |
| `POST /v1/users/<user>/stop` | `key`, `run` | Kills every process of that agent user (SPEC-05's helper) and returns once `/proc` shows none, or fails `agent_user_busy` after a bound wait; refused unless the user is bound to `run` |
| `POST /v1/sessions` | `key`, `run`, `turn`, `user`, `workspace`, `options` (`SessionOptions`), `mcp` (`url`, `token`), `notify` (the workflow to send its events to) | Creates the AHP session; returns its ID, or the existing one for the key |
| `POST /v1/sessions/<id>/prompts` | `key`, `turn`, `text` | Dispatches a turn; idempotent by key |
| `POST /v1/sessions/<id>/permissions/<request>` | `key`, `option` | Answers a pending permission request |
| `POST /v1/sessions/<id>/cancel`, `DELETE /v1/sessions/<id>` | `key` | Ends a turn; disposes the session and its configuration directory |
| `GET /v1/sessions` | — | The live sessions with their keys and the host's boot ID, for reconciliation |

Keys are given by `work` (part 2) from the run and turn. The host keeps keys and session records in memory only, so after a restart it lists nothing (SPK-1, experiment 8).

**Host events (REQ-0616, REQ-0625).**
- **Delivery:** the host POSTs each event to `grindstone:8081/stations/host/events` (SPEC-05's station listener). Per session, one at a time in `seq` order, retrying the current event with backoff until it gets a 2xx; events of different sessions are independent.
- **Types:** `host.started`; `session.started`, `session.ended`; `turn.started`, `turn.ended` (stop reason); `tool.call` (name, status, and for the transcript its input and output, truncated to `[host].transcript_truncate`); `permission.requested`; `steering.received`; `model` (the model serving the turn); `error` (`rate_limited`, `provider_error`, `context_exhausted`, `other`).
- **Signature:** HMAC-SHA256 under `host_event_key` over the RFC 8785 canonical JSON of the event without `sig` (DEC-0605). The host uses `canonicalize`, SPEC-01's TypeScript dependency.
- **Intake** (`stations`), the route mounted on the station listener by the composition root:
  1. verify the signature;
  2. insert into `stations.host_events`, where a unique `event_id` makes a duplicate a no-op;
  3. require `seq` to be the session's next, otherwise refuse;
  4. update the session's `last_activity`;
  5. `DBOS.send` turn-relevant events (`turn.ended`, `permission.requested`, `error`, `session.ended`, `model`) to the session's `notify` workflow with `idempotency_key=event_id`.
- **Transcript:** tool-call and message events are appended to the run's transcript, which `work` writes as a blob when the run ends. They are the run's working notes, and nothing reads them as evidence (SPEC-08).

**Reconciliation (REQ-0619).** On every `host.started` event with a new boot ID, and every 60 s, `stations` calls `list()`. A session it holds as live that the host does not list, or that belongs to an older boot, is marked ended and reported to its `notify` workflow as `host_lost`. Part 2 decides what happens next.

**Activity registry.** In process memory: `touch(run)` and `open_calls(run)`, maintained by SPEC-07's tool wrapper, plus `last_activity` from host events. A restart ends every open call, so nothing is persisted. Part 2's liveness rule reads it.

**Agent host core** (`agent-host/src/`, TypeScript on Node 24):
- `createHost` from `@ahpd/sdk` 0.12.0, with SPEC-05's people directory.
- One backend: the wrapper around `acpAgent` from `@ahpd/agent-acp` 0.12.0 (REQ-0618). For each new session it reads the host's own session record by the session UUID (SPK-1's mapping). It then:
  - adds `{type: "http", url, headers: {Authorization: "Bearer …"}}` to `start.mcpServers`;
  - creates an `acpAgent` for that session alone, whose command is the preset's launcher;
  - runs the launcher through SPEC-05's helper as the run's bound user, with the session's configuration directory;
  - passes an environment built only from the preset's allow-list and the options the preset maps (REQ-0626). `@ahpd/agent-acp` merges an agent's environment over the host's own, so the host itself runs with a minimal environment.
- The control API server and the event signer.
- **Presets** are data under `agent-host/presets/<name>/`: command, environment allow-list, and a mapping from `SessionOptions` to the agent's settings. Claude's preset is SPEC-05's; for example, it maps `tool_timeout_seconds` to `MCP_TOOL_TIMEOUT`, permission categories to its tool rules, and `read_only` to denying its file-writing tools. The scripted preset is this specification's.

Package pins, each the latest on the npm registry on 17 October 2026: `@ahpd/sdk` 0.12.0, `@ahpd/agent-acp` 0.12.0, `@agentclientprotocol/claude-agent-acp` 0.93.0, `@agentclientprotocol/sdk` 1.9.0, `@microsoft/agent-host-protocol` 1.0.0, `@modelcontextprotocol/sdk` 1.32.1 (the scripted preset's MCP client).

**Scripted preset (REQ-0620).** An ACP agent written with `@agentclientprotocol/sdk`.
- **Script:** `SessionOptions.script`, a JSON list of turns. Each turn is a list of actions: `call` (a kernel tool with arguments, and optionally the error code it expects), `write` (a file in the workspace), `wait` (seconds), `request` (a permission request through ACP) and `end`.
- **Execution:** it calls the kernel MCP server with the session's token, and records what it saw for the test to assert on.
- **Selection:** instance configuration `[agents].force_preset = "scripted"` (part 2) makes every capability use it. Projects cannot set it (I-14).

**Runner jobs (REQ-0621).**
1. `dispatch_job(job, subject_dir)` (external step, key the job ID) writes `runs/.incoming/<job>/` (`job.json`, `subject/`, empty `out/`) and renames it to `runs/<job>/`, so the runner never sees a partial job.
2. It waits on the check lane (`lane.<station>.check`) for `out/DONE`, polling every 2 s, up to `timeout_s` plus a margin.
3. It parses `out/result.json` against `RunnerResult`, and nothing else from the directory.
4. A timeout or an unparseable result is an `error` outcome; SPEC-08 decides retries.
5. The job directory is removed when SPEC-08 has recorded its evidence.

**State and ownership.** Schema `stations`:
- `agent_users (station, user, run)`;
- `sessions (id, run, turn, key, notify, host_boot, state, last_activity)`, `state` written only by `stations.transition_session` (FF-08);
- `workspaces (run, user, state)`, `state` written only by `stations.transition_workspace`;
- `host_events` (insert-only), `jobs (id, state)`.

Liveness age is computed, never stored (FF-09).

**Interfaces** (to part 2 and SPEC-08): `bind`, `prepare_workspace`, `collect`, `discard_workspace`, `open_session`, `prompt`, `answer_permission`, `cancel`, `dispose`, `touch`, `open_calls`, `last_activity`, `dispatch_job`.

**Configuration** (instance sections owned here): `[stations.<id>]` (`kind`, `tier`, `control_url` or `runs_dir`, `lanes`, `agent_users` for agent stations); `[host]` (`transcript_truncate`, 64 KiB).

**Security.**
- B1: host events are signed with a key agents cannot read (SPEC-05), refused when forged, replayed or out of order. The control API is keyed.
- The host never reads session configuration from AHP clients (REQ-0618).
- A run's workspace is readable only by its own agent user, the host and the control plane (SPEC-05). No two unfinished runs share a user (REQ-0623).
- An agent can leave processes behind that the session's end does not kill (a `setsid` or `nohup` child of its shell tool, which the parent-death signal does not reach). None survives collect or the release of its user (REQ-0629), so none can change a workspace while the control plane reads it, or reach the next run bound to the same user (confirmation 1, C4).
- Read-only workspaces are fresh copies of the subject. Nothing in them is collected, and `read_only` makes the preset deny writing tools.

**Make and prove.** No subjects are made here. A prover's workspace comes only from the subject's resolver, never from a maker's workspace (I-15).

**Fitness functions.**
- FF-08: `sessions.state` and `workspaces.state` registered with their transition functions (SPEC-04's single-writer check).
- FF-10: workspace prepare, session create, prompt, permission answer, dispose, user stop, collect, discard and job dispatch are registered external steps with crash-and-resume tests.
- FF-07 covers `stations`; FF-09: no stored liveness.

## 6. Decisions

DEC-0603: Workspace contents reach the agent as an archive the control plane writes to a staging area and the host streams to an extractor running as the agent user · No process needs a capability to give an agent a writable copy, and the control plane never writes into agent-owned directories (SPEC-05) · Rejected: the control plane writing the workspace directly (it would own the files, so the agent could not write them); agents fetching their own inputs (they would need access to `repos`).
DEC-0604: A read-only workspace is a fresh copy owned by the reviewer's agent user, with writing tools denied and nothing collected · What makes a prover independent is that its verdict is about the subject and that nothing it writes can reach the subject; both hold · Rejected: a copy the reviewer cannot write (needs a third owner, so a capability or a user per run).
DEC-0605: Host events are signed over RFC 8785 canonical JSON · Key order differs between Node and Python serializers; SPK-1, experiment 9, signed an encoding both sides happened to agree on · Rejected: signing the raw body bytes (forces both sides to keep the exact bytes through every proxy and parser).
DEC-0606: A run is bound to one agent user for its life, from a pool larger than the lanes, and lanes stay DBOS queues · A suspended run keeps its workspace without holding a lane, and its next session runs as the user that owns the workspace (review 1, F1) · Rejected: binding a run to a lane slot for its life (a run waiting on a person would hold a lane, against ADR-14); moving the workspace to another user on resume (a copy per resume, and a window where two users hold it).
DEC-0607: The host sends each session's events in order, one at a time · Refusing an out-of-order event is only safe if the sender cannot have a later event in flight · Rejected: parallel delivery with reordering at intake (a buffer of untrusted input in the control plane).
DEC-0610: Stop every process of a run's agent user before collect and before release · Ending a session kills only the agent's own process tree, and a detached process can still write the workspace, so a reader in the control plane could be raced, and a later run bound to the same user would inherit it; the one-run-per-user binding (DEC-0606) makes killing every process of that user exact · Rejected: relying on the parent-death signal (it reaches only the direct child); a PID namespace per session (needs a capability the host does not hold, SPEC-05); defending the reader alone (the cross-run leak remains).

## 7. Tickets and acceptance criteria

TKT-0602: Stations: agent-user bindings, sessions, workspaces, host client, host event intake, reconciliation, activity registry, runner job dispatch · implements REQ-0606, REQ-0609, REQ-0616, REQ-0619, REQ-0621, REQ-0623, REQ-0629 · depends on TKT-0204, TKT-0205, TKT-0303 · paths `packages/grindstone/src/grindstone/stations/`, `packages/grindstone/src/grindstone/contracts/stations.py`, `packages/grindstone/tests/stations/`.
TKT-0604: Scripted preset · implements REQ-0620 · depends on TKT-0605 · paths `agent-host/presets/scripted/`, `agent-host/test/`.
TKT-0605: Agent host core: control API, backend wrapper, preset option mapping, ordered signed events · implements REQ-0617, REQ-0618, REQ-0625, REQ-0626 · depends on TKT-0502, TKT-0504 · paths `agent-host/src/`, `agent-host/package.json`, `packages/contracts-ts/`.
TKT-0607: SDK ports `WorkspaceProvider` and `SubjectResolver`, their contracts and the kernel's `blob`, `blob_set` and `item_revision` resolvers · implements REQ-0624 · depends on TKT-0301 · paths `packages/grindstone/src/grindstone/contracts/ports.py` (the protocols), `packages/grindstone/src/grindstone/contracts/stations.py` (`RunContext`, `Materialization`, `CollectOutcome`), the SDK's export list in `packages/grindstone/src/grindstone/sdk/`, `packages/grindstone/src/grindstone/stations/`.

AC-0606-1: Two runs of one task get different workspaces under their users' subtrees, and a read-only run's workspace is materialized from its subject by the resolver, not from the maker's workspace · verifies REQ-0606 · integration · `test_fresh_workspace_per_run`.
AC-0609-1: Killed after the host created a session and before the step's checkpoint, the run on restart gets the same session for the same key, and the fake host created one · verifies REQ-0609 · crash-and-resume · `test_session_create_once`.
AC-0616-1: A replayed host event is acknowledged and changes nothing; a tampered, a wrongly keyed and an out-of-order event are refused; killed between insert and send, the event reaches its workflow once · verifies REQ-0616 · crash-and-resume · `test_host_events_signed_and_deduplicated`.
AC-0617-1: The control API refuses a call without the key, and replaying `create_session`, `prompt` and `prepare_workspace` with the same key returns the original result · verifies REQ-0617 · contract · `test_host_control_api_idempotent`.
AC-0618-1: The agent's environment contains only the preset's allow-list and mapped options, its MCP configuration carries the session's own bearer token, and an AHP client's session configuration naming another MCP server has no effect · verifies REQ-0618 · integration · `test_backend_wrapper_builds_session`.
AC-0619-1: Killing the host during a session makes reconciliation report `host_lost` to the session's workflow within one reconciliation interval, and an event from the new boot for the old session is refused · verifies REQ-0619 · integration · `test_reconciliation_reports_host_lost`.
AC-0620-1: A scripted session runs a fixture script of a `read_item`, a file write, a `report` and an end, through the real host, the real kernel MCP surface and the real control plane · verifies REQ-0620 · scripted agent · `test_scripted_preset_end_to_end`.
AC-0621-1: The runner never sees a job before its rename; a job whose result never appears is recorded `error` at its timeout; a job killed after dispatch and before its checkpoint is dispatched once · verifies REQ-0621 · crash-and-resume · `test_runner_job_dispatch`.
AC-0623-1: Two read-only runs that each suspend and resume keep their own agent users and workspaces across the resume; with every user bound, a new run waits with `agent_user_unavailable` and starts once a run releases its user; a cancelled run releases its user after its workspace is removed · verifies REQ-0623 · integration · `test_runs_keep_their_agent_user`.
AC-0624-1: A fixture provider and resolver in the `notes` style implement the ports from `grindstone.sdk` alone; a `CollectOutcome` with prover context and an extra check round-trips; a provider cannot obtain a context for another factory · verifies REQ-0624 · unit · `test_workspace_ports`.
AC-0625-1: With intake refusing one event, the host does not send that session's next event until the first is accepted, while another session's events keep flowing · verifies REQ-0625 · integration · `test_host_events_in_order_per_session`.
AC-0626-1: A grep of `packages/grindstone/src/grindstone/stations/` and `agent-host/src/` for the Claude preset's setting names finds none, and the Claude preset maps `tool_timeout_seconds` to its timeout variable · verifies REQ-0626 · contract · `test_no_agent_specific_settings_in_core`.
AC-0629-1: With the real host, a scripted session that starts a detached process (`setsid sleep`) and ends: collect and discard each find no process of that user alive before the provider runs or the user is released, and the next run bound to the same user sees no process from the previous one · verifies REQ-0629 · security · `test_agent_user_processes_stopped_before_collect_and_release`.

## 8. Test plan

- **Unit:** AC-0624-1.
- **Integration**, on real Postgres and DBOS with a fake host speaking the control API, or the real host where named: AC-0606-1, AC-0618-1, AC-0619-1, AC-0623-1, AC-0625-1.
- **Scripted agent**, through the real host in its container (ADR-19): AC-0620-1.
- **Crash-and-resume:** AC-0609-1, AC-0616-1, AC-0621-1.
- **Security**, with the real host in its container: AC-0629-1.
- **Contract:** AC-0617-1 (both sides of the control API from the generated contracts), AC-0626-1.

## 9. Open items and risks

OQ-0601: Should a host restart mid-turn resume Claude Code's own session from the transcript in its configuration directory, rather than start a new one? · Default: new session; SPK-1 did not test resume, and the workspace carries the state that matters · Resolved at the M1 review from the live run's host-loss behaviour.
OQ-0603: How large may a turn's transcript grow before it is truncated? · Default: tool outputs truncated to 64 KiB each in events; the full transcript is kept only as the agent wrote it in its configuration directory, which is discarded with the session · Resolved by TKT-0602.
OQ-0604: Is a pool of eight agent users enough? · Default: yes for one writing and four read-only lane slots with a few runs waiting on the operator; the wait is visible as `agent_user_unavailable` · Resolved at the M1 review from the live runs.

Risks mitigated: duplicate sessions, prompts and jobs across crashes (keys); a lost host costing correctness (reconciliation); forged or replayed events (signature, IDs, ordering); a run's workspace becoming unreachable after a resume (one user per run).
Risk added: the agent host packages are pre-1.0 and release every few days. Mitigation: exact pins; the scripted preset exercises the real host on every commit; upgrades are deliberate commits that re-run these tests.

## 10. Rollout

The first migration creates schema `stations`. The M0 agent host's health server becomes part of the control API server, and `/readyz` stays. The host control protocol starts at version 1; both sides support the old and new versions during an upgrade (Components, "Contracts, versioning"). No stored data exists before M1.
