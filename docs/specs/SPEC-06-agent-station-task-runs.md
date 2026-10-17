# SPEC-06 — Agent station and task runs
Status: draft · Milestone: M1
Kind: kernel · Owns:
- `grindstone.work`: tasks, runs, turns, reports, thin matching, thin template runs, context packs, run manifests, liveness, failure causes, the suspend-and-resume mechanism.
- `grindstone.stations`: sessions, lane slots, workspace lifecycle, the host adapter and its event intake, the runner job envelope and dispatch.
- The agent host's core in `agent-host/`: control API, backend wrapper, signed events, the scripted agent preset.

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

A task is the one unit of work, and every attempt at it must leave a record of what it was given, what it did and how it ended (ADR-14, I-06). This specification runs a task end to end on an agent station:
- match its need to a capability;
- prepare a fresh workspace;
- record the run before any session opens;
- drive Claude Code (or the scripted agent) through the host, turn by turn, until one validated report ends each turn;
- suspend without holding a lane when the agent asks the operator, and resume in a new session on the same workspace;
- catch a missing report, a stall or a lost host as a typed failure;
- collect the work and hand it to checks.

It also builds the host core that ADR-42 describes, so the control plane never depends on a session surviving a restart.

## 2. Scope

In scope:
- **Tasks and runs.** The task lifecycle (eight states) and its transition function. Runs, sessions, turns and reports. The run manifest, written before the session.
- **Getting a task started.** Thin matching. Thin template runs: linear, with a `deliver` step attached to the task before it. Input binding by reference closure. The context pack and prompts.
- **Suspending.** The mechanism behind `ask(need="operator")` and `request_permission`.
- **Failures and limits.** Liveness, failure causes and their retry rules, escalations.
- **Sessions on the station.** Lane slots, sessions and workspaces in `stations`. Permission requests from the agent.
- **The host side.** The host control API and signed host events. The agent host core: control API server, backend wrapper and event signer. The scripted agent preset (ADR-19).
- **Check stations.** The runner job envelope and its dispatch.

Out of scope:
- **Kernel MCP tools** themselves: SPEC-07. This specification provides the work services they call.
- **Proof.** Check plans, evidence, the runner's executors and the delivery port: SPEC-08. This specification moves the task through `verifying` and `delivering` on SPEC-08's events.
- **Deployment.** Users, file modes, secrets, the helper that runs commands as agent users, and the Claude preset's launcher: SPEC-05.
- **Factory parts.** Workspace contents and copy-back: SPEC-09's workspace provider, behind the SDK port this specification defines.
- **Cooperation.** Consults, delegation, `load_skill`, the depth and live-children caps, the consult ceiling, the project cap and full matching: SPEC-17 (M3).
- **Later work.** Rework rounds after failed checks: SPEC-18 (M3) with SPEC-19's template edges. Steering from the UI and VS Code: SPEC-22 (M4); the host forwards steering events, which are recorded. Template graphs, `fan_out` and bindings: SPEC-19 (M4).
- **Applied changes.** Delivering applied changes to running tasks: SPEC-16 (M3).

## 3. Foundation links

Implements:
- **ADR-14.** One task model with modes, pinned inputs, an output contract, a check plan, a tier and a parent. Runs in fresh workspaces; Grindstone-numbered turns, each ending with exactly one validated report; typed failure causes with retry rules. Asking the operator ends the turn with outcome waiting, closes the session and frees the lane.
- **ADR-15, as amended by ADR-42.** A thin host on `@ahpd/sdk`, its packages unmodified behind a backend wrapper. A typed control API, idempotent on client keys. HMAC-signed, at-least-once events with IDs and turn numbers. Permission answers only through the control API. Correctness never depends on a session surviving a restart.
- **ADR-17.** T1 agent stations with lanes; T0 as a read-only workspace on a T1 station.
- **ADR-19.** A scripted ACP agent preset replays fixture scripts.
- **ADR-03.** Agent sessions run as child workflows on the station lanes, and waits on people park as decision continuations.
- **ADR-37 (liveness).** A run with no agent activity for the liveness timeout fails `stalled`; an open kernel tool call pauses the timer (SPK-5, experiment 5).
- **ADR-24, thinnest form.** Requests name needs, never capabilities, and an absent or ambiguous match raises an escalation.
- **ADR-41.** No Claude-specific path in the host core or the kernel. Agents are presets, and the scripted preset is a second ACP implementation on every commit.
- **I-03.** Agents' reports and proposals reach intent only as ChangeDrafts and delivery only through SPEC-08.
- **I-06.** The run manifest is written before the session opens.
- **I-04, in part.** No path here moves a task to `done` except SPEC-08's evidence gate.

Delivers:
- **M1-01**, the kernel side of the execution clause: a task is "matched by need" to a capability "and executed by Claude Code on the operator's subscription" in its own workspace → AC-0603-1, AC-0606-1, AC-0623-1. SPEC-04 delivers the intake clause; SPEC-09 the implementing capability, the worktree and copy-back, and the live run of the whole criterion; SPEC-08 and SPEC-09 delivery.
- **M1-03**, these clauses → AC-0608-1, AC-0610-1, AC-0611-1:
  - an invalid report is "fixed in the same turn" (SPEC-07 delivers the refusal with structured errors);
  - "a turn without a report gets one corrective prompt and then fails `missing_report`";
  - "an `ask` to the operator parks the task, and its answer resumes it in a new session on the same workspace".
- **M1-06**, the recording clause → AC-0605-1, AC-0605-2. SPEC-01 delivers the contract.
- **Supports M1-04** (delivered by SPEC-02): sessions, prompts, workspace materialization, disposal, copy-out and the replay of duplicate host events are registered external steps with crash-and-resume tests (AC-0609-1, AC-0616-1).

Depends on:
- **SPEC-01:** `RunManifest`, `ItemRef`, `BlobRef`, `SubjectRef`, record IDs, errors.
- **SPEC-02:** workflows, external steps, lanes, blobs and roots.
- **SPEC-03:** registries (capabilities, templates, needs, workspace providers), project configuration, instance sections, events, the SDK.
- **SPEC-04:** reading and rendering items, ChangeDrafts, decisions and continuations.
- **SPEC-05:** agent users and slots, the helper, the Claude preset's launcher, listeners and secrets.
- **SPEC-08:** `plan_checks`, the evidence gate and the delivery port, used by `work` only.

`stations` depends on nothing in SPEC-08. SPEC-08's `evidence` depends on `stations`. `work` depends on both. The modules are therefore acyclic, and tickets follow that order: `stations`, then `evidence`, then `work`.

Scenarios: K1 steps 2–5 and 8.

## 4. Requirements

REQ-0601: The task lifecycle has the eight states of the Concepts tab, and one transition function in `work` is its only writer, refusing any transition not in section 5's table.
REQ-0602: Readiness is computed, never stored: a queued task is ready when its inputs exist at their pinned revisions, no open decision blocks its scope, and a station of its tier is configured.
REQ-0603: A task's need is matched to exactly one capability from the factories enabled in its project that offers the need in the task's mode, preferring the requesting factory's own capability; no candidate, or more than one, raises an escalation and creates no run.
REQ-0604: A template run executes its steps in order; a `deliver` step sets the delivery target of the `task` step before it, and the template run is done when its last task is done; a template run started twice with the same client key is started once.
REQ-0605: Before a run's first session is created, the run record holds a `RunManifest` with the pinned item revisions, capability and its hash, factory and version, agent preset, configured model, subject version, context-pack hash and the initial prompt as a blob; each turn records the model the host reported for it.
REQ-0606: Each run has a fresh workspace prepared by its capability's workspace provider (writing) or from its subject (read-only), owned by the run's lane-slot agent user, and never shared with another run.
REQ-0607: Each turn runs as a child workflow on its station's lane for the capability's workspace mode, holds one lane slot and its agent user for the turn only, and frees both when the turn ends.
REQ-0608: A turn ends only when its report is accepted, its session reports turn end after an accepted report, or a suspending tool ends it; a turn that ends without an accepted report gets exactly one corrective prompt in the same session, and if that turn also ends without one, the run fails `missing_report`.
REQ-0609: Every call to the host carries an idempotency key derived from the run and turn; replaying a call returns the original result, and a session is never created twice for one key.
REQ-0610: A report is validated against the task's output contract; an invalid report returns structured errors and leaves the turn open, so the agent can submit a corrected report in the same turn.
REQ-0611: `ask(need="operator")` records the turn's report with outcome `waiting`, raises a `question` decision with the agent's recommended answer and a continuation, disposes the session and frees the lane; the answer resumes the run in a new session on the same workspace, with the answer at the top of the next prompt.
REQ-0612: A run with no host activity for the liveness timeout and no open kernel tool call fails `stalled`; a run with an open kernel tool call or a pending permission request is never failed for inactivity.
REQ-0613: Each failure cause follows its retry rule: `host_lost` continues once in a new session and then retries the run once; `rate_limited` and `provider_error` park the run and retry with backoff; `stalled`, `missing_report`, `context_exhausted` and `checks_failed` block the task and raise an escalation offering retry and cancel.
REQ-0614: An agent's permission request is answered `deny` at once when its capability says `deny`, and otherwise raises a `permission` decision whose answer is sent through the control API.
REQ-0615: When the maker reports `done`, the run collects its subject through the workspace provider, copies the output contract's declared files into the blob store with a lease root for the run, turns proposals into one ChangeDraft, raises any permission requests the provider returned, and moves the task to `verifying` with the provider's extra checks added to its plan.
REQ-0616: Host events are accepted only with a valid HMAC over their canonical JSON under the host event key; a duplicate event ID is acknowledged and ignored, and a forged, tampered or out-of-order event is refused and logged.
REQ-0617: The host control API refuses any call without the host control key, and serves `create_session`, `prompt`, `answer_permission`, `cancel`, `dispose`, `list`, `prepare_workspace` and `discard_workspace`, each idempotent on its client key.
REQ-0618: The backend wrapper builds each agent's environment from scratch, gives the session its kernel MCP server with the per-task bearer token in its headers, and reads both from the host's own session record, never from AHP session configuration.
REQ-0619: After a host restart, the control plane reconciles from `list()`: any session it believes active that the host does not list fails its turn `host_lost`.
REQ-0620: The scripted preset replays a fixture script of kernel tool calls, file writes and turn ends through ACP and MCP, and is selectable for every capability by instance configuration only.
REQ-0621: Runner jobs are written as job directories with a typed envelope, picked up only once complete, and a job with no result by its timeout is recorded as an `error` outcome.
REQ-0622: A task's maker never sees its own later checks' sessions: check runs are separate tasks in `check` mode with their own runs and workspaces.

## 5. Design

**Contracts** (`grindstone.contracts.work`, `.stations`, `.host`; schema version 1 each):

| Model | Fields |
| --- | --- |
| `Task` | `id`, `project`, `origin` (template run and step, parent task, or command), `need`, `capability`, `mode` (`work`, `consult`, `check`), `goal`, `inputs` (`items: tuple[ItemRef, ...]`, `blobs`, `subject: SubjectRef \| None`), `output` (`report_schema`, `kinds`, `files` globs, `delivery: adapter \| None`), `checks` (SPEC-08's `CheckSpec` tuple), `tier`, `lane`, `parent` |
| `Run` | `id`, `task`, `number`, `state`, `cause`, `manifest: RunManifest`, `workspace`, `started_at`, `ended_at` |
| `Turn` | `run`, `number`, `session`, `prompt: BlobRef`, `kind` (`grindstone`, `corrective`, `steering`), `model`, `outcome`, `report` |
| `Report` | `outcome` (`done`, `blocked`, `failed`; `waiting` only from a suspending tool), `summary`, `data` (validated against `report_schema`), `files` (paths declared produced), `proposals` (draft revisions, SPEC-07's `propose`) |
| `ContextPack` | `items` (refs, with the rendered Markdown as a blob), `principles` (refs), `skills` (name and hash; empty in M1); hashed with `semantic_hash` |
| `HostEvent` | `event_id` (UUIDv7), `host_boot`, `seq` (per session), `session`, `run`, `turn`, `type`, `at`, `payload`, `sig` |
| `RunnerJob` | `job_id`, `checks`, `shape`, `timeout_s`, `payload` (shape-specific, SPEC-08), `env` (declared environment) |
| `RunnerResult` | `job_id`, `status` (`completed`, `error`), `outputs` (shape-specific, SPEC-08), `started_at`, `ended_at` |

Error codes:
- validation: `report_invalid`, `report_already_accepted`;
- limit: `match_none`, `match_ambiguous`;
- transient: `host_unavailable`, `station_unavailable`;
- internal: `event_rejected`.

Events: `task.created`, `task.transitioned`, `run.started`, `run.ended`, `turn.started`, `turn.ended`, `session.created`, `session.ended`.

**Task lifecycle** (writer: `work.transition_task`, the only one; FF-08):

| From | To | When (M1) |
| --- | --- | --- |
| `queued` | `running` | Ready, and its first run starts |
| `running` | `waiting` | A turn ends with outcome `waiting` |
| `waiting` | `running` | The continuation of the decision it waited on starts a new session |
| `running` | `verifying` | The maker reported `done` and collect succeeded |
| `running` | `blocked` | A run failed with a blocking cause, or collect failed |
| `verifying` | `delivering` | SPEC-08's gate holds and the task has a delivery target |
| `verifying` | `done` | The gate holds and there is no delivery target |
| `verifying` | `blocked` | A required check failed (`checks_failed`) or errored after its retry |
| `delivering` | `done` | SPEC-08 reports the delivery completed |
| `delivering` | `blocked` | The delivery failed or its decision was cancelled |
| `blocked` | `queued` | An escalation answered `retry` |
| any but `done` | `cancelled` | An escalation answered `cancel` |
| `done` | `queued` | Reserved for a failing re-check (SPEC-12); no writer in M1 |
| `verifying` | `running` | Reserved for rework rounds (SPEC-18); no writer in M1 |

The run lifecycle is `preparing → active → collecting → succeeded`, with `active ⇄ parked` and `failed` (with cause) reachable from every state but `succeeded`. Its writer is `work.transition_run`.

**Matching (REQ-0603).** Filter, in order, the capabilities of the project's enabled factories:
1. those offering the need in the mode (`work` matches offers serving `delegate`; `check` matches `check`);
2. if more than one remains, those in the requesting template's factory.

Exactly one remaining is the match. Otherwise the task is `blocked` with an `escalation` (`match_none` or `match_ambiguous`, recommendation `cancel`, reason naming the candidates). SPEC-17 adds the other filters and the project pin.

**Templates (REQ-0604).** `work.start_template(project, template, args, by, client_key)` validates `args` against the template's schema and records `work.template_runs`, whose `client_key` is unique per project, so a repeated command returns the original run. A `deliver` step's adapter becomes the preceding task's `output.delivery`. Each `task` step creates a task:
- **Inputs:** the closure binding resolves to pinned revisions: from an argument's item, follow the named edge types forward or inverted (for example, from `args.note`, follow `notes.cites`). Each revision is pinned at its current hash.
- **Checks:** `evidence.plan_checks` (SPEC-08) checks make and prove against the matched capability.

`task.transitioned` to `done`, `blocked` or `cancelled` advances or ends the template run through an event consumer.

**Runs.** The workflow `run-<task>-<n>`, started for a ready task:
1. **Prepare** (external step, key `run-<id>:prepare`). Writing workspace: `provider.prepare(ctx)` (SDK `WorkspaceProvider`) returns a `Materialization`, an archive in `workspaces/staging/<run>.tar` and the subject version it starts from. Read-only workspace: the subject's resolver materializes it the same way. Then `host.prepare_workspace(run, slot, archive)` extracts it as the slot's agent user (SPEC-05's helper).
2. **Record** (transaction). Assemble the context pack:
   - the pinned items rendered (SPEC-04);
   - the project's current `core.principle` items, pinned;
   - the capability's start skills.

   Write the pack and the initial prompt as blobs with lease roots. The prompt is:
   - the capability prompt, then the project's `extra_prompt`;
   - the pack;
   - the goal;
   - the output contract, with the kernel tools to use.

   Write the run and its `RunManifest` (REQ-0605). The configured model is the instance's model for the capability's model slot (`[agents.<preset>].models`).
3. **Turns.** Enqueue `turn-<run>-<k>` on `lane.<station>.writing` or `.readonly` and wait for it. A parent run waiting on its own turn is not on a lane, so it cannot deadlock (SPK-2, experiment 7).
4. **Act on the turn's outcome** by cause (REQ-0613), or collect (REQ-0615) on `done`.

**A turn** (the workflow `turn-<run>-<k>`, on the lane):
1. Acquire a slot in `stations.slots`, skipping locked rows. The lane's concurrency guarantees one is free.
2. Mint the per-task MCP token for run and turn, through the minting function SPEC-07 provides and the composition root registers with `work` (`work` may not import `surface`, Components, "Module map").
3. `create_session` (key `run-<id>:s<k>`), with the preset, the per-session options derived from the capability and the slot's agent user. The options carry:
   - the model and effort;
   - permission allow rules;
   - `MCP_TOOL_TIMEOUT` above the consult ceiling, as SPK-5 advises;
   - for a read-only workspace, the agent's file-writing tools denied.
4. `prompt` (key `run-<id>:t<k>`).
5. Loop on `DBOS.recv(f"turn-{k}", timeout=60 s)`. Host events arrive as messages keyed by event ID (REQ-0616). Each wake checks liveness: `stations.sessions.last_activity` against the timeout, unless `stations.open_calls(run)`, which SPEC-07's tool wrapper maintains, is non-zero or a permission request is pending (REQ-0612). Each tool call also counts as activity (`stations.touch`).
6. On turn end:
   - with an accepted report, return its outcome;
   - with none, and no corrective prompt sent yet, send one (key `run-<id>:t<k>c`) naming the missing `report` call and keep waiting;
   - otherwise fail `missing_report`.
7. `dispose` (key `run-<id>:d<k>`), release the slot, return.

A report rejected by validation leaves the turn open (REQ-0610). The agent sees the errors as its tool result and calls `report` again in the same turn.

**Suspending (REQ-0611).** `work.suspend(run, turn, request)` is called by SPEC-07's `ask(need="operator")` and `request_permission`. In one unit of work it:
- records the turn's report with outcome `waiting`;
- raises a `question` or `permission` decision with the agent's recommendation and the continuation `work.resume_run`;
- moves the task to `waiting`;
- sends the turn workflow a `suspended` message.

The tool returns its confirmation, the turn workflow disposes the session and frees the lane, and the run workflow ends. The workspace stays. When the decision is answered, its continuation runs `run-<id>-r<decision>`, which goes straight to turn `k+1` with the answer, or the permission outcome, at the top of the prompt. Because SPK-5 found that a client may not see a result delivered as its call is cut, the answer lives in the decision and the resumed prompt, never only in a tool result.

**Liveness (REQ-0612).** The seed is 20 minutes, from instance configuration `[limits].liveness_timeout`. SPEC-17 owns the seeds and per-capability overrides. Activity is any host event for the session. Stall handling: cancel, dispose, fail `stalled`.

**Failures (REQ-0613).**

| Cause | Detected by | M1 handling |
| --- | --- | --- |
| `host_lost` | Reconciliation (REQ-0619), or a host event with a new `host_boot` | Turn `k+1` in a new session on the same workspace; a second loss fails the run, and the task retries once with a fresh run, then blocks |
| `rate_limited`, `provider_error` | Host `error` events with that kind | Run `parked`; `DBOS.sleep` with exponential backoff (1, 2, 4 … 30 min); then a new turn; after 6 attempts, block |
| `context_exhausted` | Host `error` event | Block, with an escalation |
| `stalled`, `missing_report` | The turn workflow | Block, with an escalation |
| `checks_failed` | SPEC-08, or a permission request denied at collect | Block, with an escalation carrying the failing evidence |
| `cancelled` | An escalation answer | Cancel the session if any, discard the workspace |

Escalations carry the cause, the run and the recommendation:
- `retry` for `host_lost`, `rate_limited` and `provider_error`;
- `cancel` otherwise, with the reason.

`retry` queues the task again, and its next run gets a fresh workspace.

**Collect (REQ-0615).**
1. `provider.collect(ctx)` (external step, keyed by run) returns SDK `CollectOutcome`: `subject`, `extra_checks`, `permission_requests`, and on refusal a typed failure with the refused paths (SPEC-09).
2. The output contract's files are read from the workspace by the provider's `read_file` and put as blobs.
3. Proposals become one ChangeDraft with source `task output`.
4. Each permission request raises a `permission` decision. The task enters `verifying` only once all are answered; any `deny` fails the run `checks_failed`.
5. The workspace is discarded (`host.discard_workspace`, then `provider.discard`) when the run ends, after collect or failure, except while the task waits on a decision.

**Host control API (REQ-0617).**
- **Transport:** HTTP/JSON on `agent-host:8090` (SPEC-05), bearer `host_control_key`, header `Grindstone-Host-Protocol: 1`.
- **Errors:** `ErrorEnvelope`.

| Call | Body | Effect |
| --- | --- | --- |
| `POST /v1/workspaces` | `key`, `run`, `slot`, `archive` | Creates `agents/<slot>/<run>/` and extracts the archive as the slot's user; an existing one with the same key is a no-op |
| `DELETE /v1/workspaces/<run>` | `key` | Removes it as the slot's user |
| `POST /v1/sessions` | `key`, `run`, `turn`, `slot`, `workspace`, `preset`, `options`, `mcp` (`url`, `token`) | Creates the AHP session; returns its ID, or the existing one for the key |
| `POST /v1/sessions/<id>/prompts` | `key`, `turn`, `text` | Dispatches a turn; idempotent by key |
| `POST /v1/sessions/<id>/permissions/<request>` | `key`, `option` | Answers a pending permission request |
| `POST /v1/sessions/<id>/cancel`, `DELETE /v1/sessions/<id>` | `key` | Ends a turn; disposes the session and its configuration directory |
| `GET /v1/sessions` | — | The live sessions with their keys, for reconciliation |

The host keeps keys and session records in memory only. After a restart it lists nothing, which is what REQ-0619 relies on (SPK-1, experiment 8).

**Host events (REQ-0616).**
- **Delivery:** the host POSTs each event to `grindstone:8081/stations/host/events` (SPEC-05's station listener), retrying with backoff until it gets a 2xx.
- **Types:**
  - `host.started`;
  - `session.started`, `session.ended`;
  - `turn.started`, `turn.ended` (stop reason);
  - `tool.call` (name, status, and for the transcript its input and output, truncated to a configured size);
  - `permission.requested`;
  - `steering.received`;
  - `model` (the model serving the turn);
  - `error` (`rate_limited`, `provider_error`, `context_exhausted`, `other`).
- **Signature:** HMAC-SHA256 under `host_event_key` over the RFC 8785 canonical JSON of the event without `sig` (SPK-1 recommends canonical JSON over key order). The host uses `canonicalize`, SPEC-01's TypeScript dependency.
- **Intake** (`stations`):
  1. verify the signature;
  2. insert into `stations.host_events`, where a unique `event_id` makes a duplicate a no-op;
  3. check `seq` per session;
  4. update `last_activity`;
  5. `DBOS.send` turn-relevant events to `turn-<run>-<k>` with `idempotency_key=event_id`.
- **Transcript:** tool-call and message events are appended to the run's transcript, written as a blob when the run ends. They are the run's working notes. Nothing reads them as evidence (SPEC-08).

**Agent host core** (`agent-host/src/`, TypeScript on Node 24):
- `createHost` from `@ahpd/sdk` 0.12.0, with the people directory from SPEC-05.
- One backend: the wrapper around `acpAgent` from `@ahpd/agent-acp` 0.12.0 (REQ-0618). For each new session it reads the host's session record by the session UUID (SPK-1's mapping). It then:
  - adds `{type: "http", url, headers: {Authorization: "Bearer …"}}` to `start.mcpServers`;
  - creates an `acpAgent` for that session alone, whose command is the preset's launcher;
  - runs the launcher through SPEC-05's helper as the slot's user, with the session's configuration directory;
  - passes an environment built from the preset's allow-list only: `PATH`, `HOME`, `CLAUDE_CONFIG_DIR`, the model credential the preset declares, `NODE_EXTRA_CA_CERTS` when the instance sets one, and `MCP_TOOL_TIMEOUT`. `@ahpd/agent-acp` merges an agent's environment over the host's own, so the host itself runs with a minimal environment.
- The control API server and the event signer.
- Presets are data under `agent-host/presets/<name>/` (command, environment allow-list, option schema). Claude is SPEC-05's; scripted is this specification's.

Package pins, each the latest on the npm registry on 17 October 2026: `@ahpd/sdk` 0.12.0, `@ahpd/agent-acp` 0.12.0, `@agentclientprotocol/claude-agent-acp` 0.93.0, `@agentclientprotocol/sdk` 1.9.0, `@microsoft/agent-host-protocol` 1.0.0, `@modelcontextprotocol/sdk` 1.32.1 (for the scripted preset's MCP client).

**Scripted preset (REQ-0620).** An ACP agent written with `@agentclientprotocol/sdk`.
- **Script:** each session's options carry a script, a JSON list of turns. Each turn is a list of actions: `call` (a kernel tool with arguments, and optionally the error code it expects), `write` (a file in the workspace), `wait` (seconds), `request` (a permission request through ACP) and `end`.
- **Execution:** it calls the kernel MCP server with the session's token, and records what it saw for the test to assert on.
- **Selection:** instance configuration `[agents].force_preset = "scripted"` makes every capability use it. CI and the kernel scenario tests run that way; projects cannot set it (I-14).

**Runner jobs (REQ-0621).**
1. `stations.dispatch_job(job, subject_dir)` writes `runs/.incoming/<job>/` (`job.json`, `subject/`, empty `out/`) and renames it to `runs/<job>/`, so the runner never sees a partial job.
2. It waits on the check lane (`lane.<station>.check`) for `out/DONE`, by polling every 2 s, up to `timeout_s` plus a margin.
3. It parses `out/result.json` against `RunnerResult` and nothing else from the directory.
4. A timeout or an unparseable result is an `error` outcome. SPEC-08 decides retries.
5. The job directory is removed when its evidence is recorded.

**State and ownership.**
- Schema `work`: `tasks` (`state` by transition function), `task_runs` (`state` by transition function; manifest JSONB), `turns`, `reports`, `template_runs`, `context_packs`. Turns and reports are insert-only.
- Schema `stations`: `slots (station, slot, agent_user, lane, run)`, `sessions (id, run, turn, key, state, last_activity)`, `workspaces (run, slot, state)`, `host_events` (insert-only), `jobs (id, state)`.
- Readiness, liveness age and "waiting on" are computed (FF-09).

**Interfaces.**
- `work`: `start_template`, `create_task`, `submit_report(run, turn, report) → errors | accepted`, `suspend`, `context_for(run)` (for SPEC-07's scoping), `on_check_result` and `on_delivery` consumers, `resume_run` continuation.
- `stations`: `host` client, `dispatch_job`, the in-memory activity registry (`touch`, `open_calls`), the host event route mounted on the station listener by the composition root.

**Configuration** (instance sections owned here):
- `[stations.<id>]`: `kind`, `tier`, `control_url` or `runs_dir`, `lanes`.
- `[agents.<preset>]`: `models` (slot → model), `force_preset`.
- `[limits]`: `liveness_timeout`, `corrective_prompts` (1), `park_backoff`.
- `[host]`: `transcript_truncate`.

**Security.**
- B1: agents reach the kernel only through MCP with a per-task token (SPEC-07). Their writes reach intent only through ChangeDrafts and reach checks only as the collected subject. Host events are signed with a key agents cannot read (SPEC-05).
- The control API is keyed. The host never reads session configuration from AHP clients (REQ-0618).
- Read-only workspaces are fresh copies of the subject, owned by the reviewer's user. Nothing in them is collected, and writing tools are denied.

**Make and prove.**
- A `work` task makes; its proof is a separate `check`-mode task or job (REQ-0622). SPEC-08 refuses a check whose performer is the maker.
- A maker's own test runs are tool calls in its transcript, recorded as working notes and never evidence (M1-07, the working-notes clause, which SPEC-08 delivers).

**Fitness functions.**
- FF-08 is extended: the task and run state columns are written only by their transition functions.
- FF-10: the external steps of this specification are registered with crash-and-resume tests: workspace prepare, session create, prompt, corrective prompt, dispose, collect, blob copy-out and job dispatch.
- FF-07 covers `work` and `stations`.
- FF-09: readiness and liveness are not columns.

## 6. Decisions

DEC-0601: In M1 a template is linear, and a `deliver` step attaches its adapter to the task before it · The task lifecycle already has `delivering`, so one task carries make, prove and deliver without a template engine · Rejected: building SPEC-19's graph engine now (M4 scope); a separate delivery task (a second lifecycle for the same work).
DEC-0602: Turns are child workflows on the lanes, and runs wait on them off-lane · The lane is held only while a session runs, so suspending or failing frees it at once (ADR-14) · Rejected: whole runs on lanes (a run waiting on a decision would hold the lane).
DEC-0603: Workspace contents reach the agent as an archive the control plane writes to a staging area and the host extracts as the agent user · No process needs a capability to give an agent a writable copy, and the control plane never writes into agent-owned directories (SPEC-05) · Rejected: the control plane writing the workspace directly (it would own the files, so the agent could not write them); agents fetching their own inputs (they would need access to `repos`).
DEC-0604: A read-only workspace is a fresh copy owned by the reviewer's agent user, with writing tools denied and nothing collected · What makes a prover independent is that its verdict is about the subject and that nothing it writes can reach the subject; both hold · Rejected: a copy the reviewer cannot write (needs a third owner, so a capability or a user per run).
DEC-0605: Host events are signed over RFC 8785 canonical JSON · Key order differs between Node and Python serializers; SPK-1, experiment 9, signed an encoding both sides happened to agree on · Rejected: signing the raw body bytes (forces both sides to keep the exact bytes through every proxy and parser).

## 7. Tickets and acceptance criteria

TKT-0601: Task and run lifecycles, reports, matching, templates, context pack, manifest · implements REQ-0601 to REQ-0605, REQ-0610 · depends on TKT-0403, TKT-0302 · paths `packages/grindstone/src/grindstone/work/`, `packages/grindstone/src/grindstone/contracts/work.py`, `packages/grindstone/tests/work/`.
TKT-0602: Stations: slots, sessions, workspaces, host client, host event intake, runner job dispatch · implements REQ-0606, REQ-0609, REQ-0616, REQ-0619, REQ-0621 · depends on TKT-0204, TKT-0205 · paths `packages/grindstone/src/grindstone/stations/`, `packages/grindstone/src/grindstone/contracts/stations.py`, `packages/grindstone/tests/stations/`.
TKT-0603: Run and turn workflows: corrective prompt, suspend and resume, liveness, failure causes, permissions, collect · implements REQ-0607, REQ-0608, REQ-0611 to REQ-0615, REQ-0622 · depends on TKT-0601, TKT-0602, TKT-0802 · `work` paths.
TKT-0604: Scripted preset · implements REQ-0620 · depends on TKT-0605 · paths `agent-host/presets/scripted/`, `agent-host/test/`.
TKT-0605: Agent host core: control API, backend wrapper, event signer · implements REQ-0617, REQ-0618 · depends on TKT-0502, TKT-0504 · paths `agent-host/src/`, `agent-host/package.json`, `packages/contracts-ts/`.
TKT-0606: Live run of the kernel's execution path with a real agent: a fixture capability on the Claude preset · implements REQ-0603, REQ-0606 · depends on TKT-0603, TKT-0503 · paths `packages/grindstone/tests/live/`, `docs/live/`.

AC-0601-1: Over random sequences of events (property test), the task state changes only through the table's transitions, and FF-08 finds no other writer of `tasks.state` · verifies REQ-0601 · property · `test_task_lifecycle_transitions`.
AC-0602-1: A queued task whose pinned revision no longer exists, or whose scope has an open blocking decision, is not ready; readiness has no column · verifies REQ-0602 · unit · `test_readiness_is_computed`.
AC-0603-1: With one fixture capability offering `notes.write` in `delegate` mode, a `work` task needing `notes.write` matches it; with two from different factories, the requesting factory's wins; with two in the same factory, or none, the task blocks with `match_ambiguous` or `match_none` in an escalation and no run exists · verifies REQ-0603 · unit · `test_thin_matching`.
AC-0604-1: A fixture template `task` → `deliver` creates one task whose output names the adapter, and the template run ends when that task is done · verifies REQ-0604 · unit · `test_linear_template_attaches_delivery`.
AC-0605-1: With the scripted preset, the run's manifest exists and holds every M1-06 field before the host receives `create_session` (asserted from the fake host's request log against the database's commit order) · verifies REQ-0605 · integration · `test_manifest_written_before_session`.
AC-0605-2: A host `model` event naming a different model from the configured one is recorded on that turn, and the manifest keeps the configured one · verifies REQ-0605 · unit · `test_turn_records_served_model`.
AC-0606-1: Two runs of one task get different workspaces under their slots' subtrees, and a read-only run's workspace is materialized from its subject, not from the maker's workspace · verifies REQ-0606 · integration · `test_fresh_workspace_per_run`.
AC-0607-1: With the writing lane at 1, a second writing turn starts only after the first disposes its session, and a turn that suspends frees the lane before the decision is answered · verifies REQ-0607 · integration · `test_turn_holds_lane_only_while_running`.
AC-0608-1: Scripted: a turn that ends without `report` receives exactly one corrective prompt; if it reports then, the run continues; if not, the run fails `missing_report` and an escalation is open · verifies REQ-0608 · scripted agent · `test_corrective_prompt_then_missing_report`.
AC-0609-1: Killed after the host created a session and before the step's checkpoint, the run on restart gets the same session for the same key, and the fake host created one · verifies REQ-0609 · crash-and-resume · `test_session_create_once`.
AC-0610-1: Scripted: a report missing a required field is refused with `report_invalid` and a JSON pointer to the field, and a corrected report in the same turn is accepted and ends it · verifies REQ-0610 · scripted agent · `test_invalid_report_fixed_in_same_turn`.
AC-0611-1: Scripted: `ask(need="operator")` leaves the task `waiting` with an open `question` decision carrying the agent's recommendation, the session disposed and the lane free; answering it starts a new session on the same workspace whose first prompt begins with the answer, and the agent finds the file it wrote before asking · verifies REQ-0611 · scripted agent · `test_ask_operator_suspends_and_resumes`.
AC-0612-1: With the liveness timeout at 2 minutes, a scripted session that goes silent with no open kernel call fails `stalled` within one check interval after the timeout · verifies REQ-0612 · scripted agent · `test_silent_run_fails_stalled`.
AC-0612-2: With the same timeout, a scripted session holding a kernel call open for 5 minutes (a test-only slow tool) is not failed · verifies REQ-0612 · scripted agent · `test_open_kernel_call_pauses_liveness`.
AC-0613-1: Each failure cause, injected through the fake host, follows its retry rule in the table, and `retry` on an escalation starts a run with a fresh workspace · verifies REQ-0613 · integration · `test_failure_causes_follow_rules`.
AC-0614-1: A permission request for a capability with `otherwise: deny` is answered deny with no decision; with `decision`, a `permission` decision is raised, and its `allow_once` answer reaches the fake host · verifies REQ-0614 · integration · `test_permission_requests`.
AC-0615-1: When a scripted maker reports `done`, the fake provider's subject, extra checks and permission requests are applied: the declared file is a blob with a lease root for the run, proposals form one ChangeDraft, permission decisions are raised, and the task enters `verifying` with the extra check in its plan only after they are allowed · verifies REQ-0615 · integration · `test_collect_hands_over_to_verifying`.
AC-0616-1: A replayed host event is acknowledged and changes nothing; a tampered, a wrongly keyed and an out-of-order event are refused; killed between insert and send, the event reaches its turn once · verifies REQ-0616 · crash-and-resume · `test_host_events_signed_and_deduplicated`.
AC-0617-1: The control API refuses a call without the key, and replaying `create_session`, `prompt` and `prepare_workspace` with the same key returns the original result · verifies REQ-0617 · contract · `test_host_control_api_idempotent`.
AC-0618-1: The agent's environment contains only the preset's allow-list, its MCP configuration carries the session's own bearer token, and an AHP client's session configuration naming another MCP server has no effect · verifies REQ-0618 · integration · `test_backend_wrapper_builds_session`.
AC-0619-1: Killing the host during a scripted turn makes the run continue in turn `k+1` in a new session on the same workspace; killing it again fails the run `host_lost`, and the task retries once with a fresh run · verifies REQ-0619 · scripted agent · `test_host_restart_reconciles`.
AC-0620-1: A scripted session runs a fixture script of a `read_item`, a file write, a `report` and an end, through the real host, the real kernel MCP surface and the real control plane · verifies REQ-0620 · scripted agent · `test_scripted_preset_end_to_end`.
AC-0621-1: The runner never sees a job before its rename; a job whose result never appears is recorded `error` at its timeout; a job killed after dispatch and before its checkpoint is dispatched once · verifies REQ-0621 · crash-and-resume · `test_runner_job_dispatch`.
AC-0622-1: A check task for a maker's subject is a separate task in `check` mode with its own run, workspace and session · verifies REQ-0622 · integration · `test_checks_run_as_separate_tasks`.
AC-0623-1: Live run: a fixture template's task, needing `notes.write`, is matched to a fixture capability on the Claude preset, runs as Claude Code on the operator's subscription in its own workspace, writes its declared file and reports `done`; the run log, manifest and transcript are kept · verifies REQ-0603, REQ-0606 · live run · `live_m1_01_kernel_execution`.

## 8. Test plan

- **Unit:** AC-0602-1, AC-0603-1, AC-0604-1, AC-0605-2.
- **Property:** AC-0601-1.
- **Integration**, on real Postgres and DBOS with a fake host speaking the control API: AC-0605-1, AC-0606-1, AC-0607-1, AC-0613-1, AC-0614-1, AC-0615-1, AC-0618-1, AC-0622-1.
- **Scripted agent**, through the real host in its container (ADR-19): AC-0608-1, AC-0610-1, AC-0611-1, AC-0612-1, AC-0612-2, AC-0619-1, AC-0620-1.
- **Crash-and-resume:** AC-0609-1, AC-0616-1, AC-0621-1.
- **Contract**, both sides of the control API from the generated contracts: AC-0617-1.
- **Live run:** AC-0623-1.

## 9. Open items and risks

OQ-0601: Should a host restart mid-turn resume Claude Code's own session from the transcript in its configuration directory, rather than start a new one? · Default: new session; SPK-1 did not test resume, and the workspace carries the state that matters · Resolved at the M1 review from the live run's host-loss behaviour.
OQ-0602: Is 60 s the right `recv` interval for liveness checks? · Default: yes; QS-15 asks for action within one minute of the limit · Resolved by AC-0612-1's timing.
OQ-0603: How large may a turn's transcript grow before it is truncated? · Default: tool outputs truncated to 64 KiB each in events; the full transcript is kept only as the agent wrote it in its configuration directory, which is discarded with the session · Resolved by TKT-0603.

Risks mitigated: duplicate sessions and prompts across crashes (keys); stalls and missing reports (liveness, corrective prompt); a waiting task holding a lane (suspend frees it); a lost host costing correctness (reconciliation, new session).
Risk added: the agent host packages are pre-1.0 and release every few days. Mitigation: exact pins; the scripted preset exercises the real host on every commit; upgrades are deliberate commits that re-run these tests.

## 10. Rollout

The first migrations create schemas `work` and `stations`. The M0 agent host's health server becomes part of the control API server, and `/readyz` stays. The host control protocol starts at version 1; both sides must support the old and new versions during an upgrade (Components, "Contracts, versioning"). No stored data exists before M1.
