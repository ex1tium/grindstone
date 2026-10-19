# SPEC-06 part 2 — Task runs
Status: in review (revision 2 answers confirmation 1, `docs/specs/reviews/M1-specifications-confirmation-1.md`; revision 1: SPEC-06 split into two parts and revised from `docs/specs/reviews/SPEC-06-review-1.md`) · Milestone: M1
Kind: kernel · Owns: `grindstone.work`: tasks, runs, turns, reports, thin matching, thin template runs, context packs, run manifests, liveness, failure causes, the suspend-and-resume mechanism, collect into verifying

Compact walking-skeleton specification (Planning playbook). Part 2 of SPEC-06; part 1 (`SPEC-06-1-stations-agent-host.md`) owns `stations` and the agent host. Review: by a session that did not write it, then the operator.

## 1. Purpose

A task is the one unit of work, and every attempt at it must leave a record of what it was given, what it did and how it ended (ADR-14, I-06). This part runs a task end to end on the station services of part 1:
- match its need to a capability;
- record the run, with everything that configured it, before any session opens;
- drive the agent turn by turn until one validated report ends each turn;
- suspend without holding a lane when the agent asks the operator or for a permission, and resume in a new session on the same workspace;
- catch a missing report, a stall, a lost host or a provider failure as a typed cause;
- collect the work and hand it to checks, then to delivery.

## 2. Scope

In scope:
- **Tasks and runs.** The task lifecycle (eight states) and the run and turn lifecycles, each with one transition function. Reports. The run manifest, written before the first session.
- **Getting a task started.** Thin matching, thin template runs (linear, a `deliver` step attached to the task before it), input binding by reference closure, the context pack and prompts.
- **Suspending.** The mechanism behind `ask(need="operator")` and `request_permission`.
- **Failures and limits.** Liveness, failure causes and their retry rules, escalations.
- **Collect into verifying.** The collect outcome, output files, proposals as a draft request, permission requests at collect, check tasks for review checks, and the hand-over to delivery.

Out of scope:
- **Station services:** part 1.
- **Kernel MCP tools themselves:** SPEC-07. This part provides the work services they call.
- **Proof and delivery:** check plans, evidence, the gate and the delivery port, SPEC-08. This part moves the task on SPEC-08's results and events.
- **Cooperation:** consults, delegation, `load_skill`, the depth and live-children caps, the consult ceiling, the project cap and full matching, SPEC-17 (M3).
- **Later work:** rework rounds after failed checks (SPEC-18 with SPEC-19's edges); template graphs, `fan_out` and graph bindings (SPEC-19); applied changes reaching running tasks (SPEC-16); steering (SPEC-22).

## 3. Foundation links

Implements:
- **ADR-14.** One task model with modes, pinned inputs, an output contract, a check plan, a tier and a parent; runs in fresh workspaces; Grindstone-numbered turns, each ending with exactly one validated report; typed failure causes with retry rules. Asking the operator ends the turn with outcome waiting, closes the session and frees the lane.
- **ADR-03.** Agent sessions run as child workflows on the station lanes; waits on people park as decision continuations.
- **ADR-37 (liveness).** A run with no agent activity for the liveness timeout fails `stalled`; an open kernel tool call pauses the timer (SPK-5, experiment 5).
- **ADR-24, thinnest form.** Requests name needs, never capabilities; an absent or ambiguous match raises an escalation.
- **ADR-41.** The options `work` passes to a session are agent-neutral (part 1, REQ-0626).
- **I-03.** Agents' reports and proposals reach intent only through a ChangeSet draft and delivery only through SPEC-08.
- **I-06.** The run manifest, with the configuration hashes, is written before the first session opens.
- **I-04, in part.** No path here moves a task to `done` except SPEC-08's gate and delivery.
- **The Concepts tab's rule that "no task ever holds a lane while it waits"**, applied to `request_permission` too (foundation v4.6, "Suspending tools").

Delivers:
- **M1-01**, the kernel side of the execution clause: a task is "matched by need" to a capability "and executed by Claude Code on the operator's subscription" in its own workspace → AC-0603-1, AC-0607-2, AC-0603-2. SPEC-04 delivers the intake clause; SPEC-09 the implementing capability, the worktree and copy-back, and the live run of the whole criterion; SPEC-08 and SPEC-09 delivery.
- **M1-03**, these clauses → AC-0608-1, AC-0610-1, AC-0611-1:
  - an invalid report is "fixed in the same turn" (SPEC-07 delivers the refusal with structured errors);
  - "a turn without a report gets one corrective prompt and then fails `missing_report`";
  - "an `ask` to the operator parks the task, and its answer resumes it in a new session on the same workspace".
- **M1-06**, the recording clause → AC-0605-1, AC-0605-2. SPEC-01 delivers the contract.

Depends on:
- **SPEC-01:** `RunManifest`, refs, record IDs, errors.
- **SPEC-02:** workflows, external steps, lanes, blobs and roots.
- **SPEC-03:** registries (capabilities, templates, needs), project configuration and its hash, instance configuration and its hash, events and consumers.
- **SPEC-04:** reading and rendering items, the `change.draft_requested` event, decisions and continuations.
- **SPEC-06 part 1:** agent users, workspaces, sessions, host events, the activity registry, the collect outcome.
- **SPEC-08:** `plan_checks`, `start_mechanical`, `record_review`, the gate, and the delivery events `work` consumes. `work` never calls `delivery`: SPEC-08 starts a delivery by consuming `task.transitioned` to `delivering`.

The token minting function is registered with `work` by the composition root from SPEC-07; `work` defines the hook and does not depend on SPEC-07.

Scenarios: K1 steps 2, 4, 5 and 8.

## 4. Requirements

REQ-0601: The task lifecycle has the eight states of the Concepts tab, and one transition function in `work` is its only writer, refusing any transition not in section 5's table.
REQ-0602: Readiness is computed, never stored: in M1 a queued task is ready when its inputs exist at their pinned revisions, no open decision blocks its scope, and a station of its tier is configured; prerequisite tasks and the project cap arrive with SPEC-19 and SPEC-17, and the free lane is the queue's to wait for.
REQ-0603: A task's need is matched to exactly one capability from the factories enabled in its project that offers the need in the task's mode, preferring the requesting factory's own capability; no candidate, or more than one, raises an escalation and creates no run.
REQ-0604: A template run executes its steps in order; a `deliver` step sets the delivery target of the `task` step before it, and the template run is done when its last task is done; a template run started twice with the same client key is started once.
REQ-0605: Before a run's first session is created, the run record holds a `RunManifest` with the pinned item revisions, capability and its hash, factory and version, agent preset, configured model, subject version, context-pack hash, instance and project configuration hashes and the initial prompt as a blob; each turn records the model the host reported for it.
REQ-0607: Each turn runs as a child workflow on its station's lane for the capability's workspace mode, holds the lane for the turn only, and runs as the run's bound agent user (part 1).
REQ-0608: A turn ends only when its report is accepted, its session reports turn end after an accepted report, or a suspending tool ends it; a turn that ends without an accepted report gets exactly one corrective prompt in the same session, and if that turn also ends without one, the run fails `missing_report`.
REQ-0610: A report is validated against the task's output contract; an invalid report returns structured errors and leaves the turn open, so the agent can submit a corrected report in the same turn.
REQ-0611: `ask(need="operator")` and `request_permission` record the turn's report with outcome `waiting`, raise a `question` or `permission` decision with the agent's recommended answer and a continuation, end the turn, suspend the run, dispose the session and free the lane; the answer resumes the run in a new session on the same workspace, with the answer at the top of the next prompt.
REQ-0612: A run with no host activity for the liveness timeout and no open kernel tool call fails `stalled`; a run with an open kernel tool call is never failed for inactivity.
REQ-0613: Each failure cause follows its retry rule: `host_lost` continues once in a new session and then retries the run once; `rate_limited` and `provider_error` park the run and retry with backoff; `stalled`, `missing_report`, `context_exhausted`, `storage_limit` and `checks_failed` block the task and raise an escalation offering retry and cancel.
REQ-0614: An agent's own permission request through its session is answered `deny` at once in M1, because SPEC-03 refuses a capability whose permissions name `decision` until SPEC-15 adds expiry; a kernel-level permission is asked through `request_permission`, which suspends.
REQ-0615: When the maker reports `done`, the run collects its outcome through part 1; reads the output contract's declared files from the collected subject through its resolver and stores them as blobs with a lease root for the run; emits one `change.draft_requested` for the run's proposals; puts the task in `waiting` while the collect outcome's permission decisions are open; and moves the task to `verifying` with the extra checks added only when all are allowed.
REQ-0622: A task's maker never sees its own later checks' sessions: review checks run as separate tasks in `check` mode with their own runs, workspaces and agent users.
REQ-0627: The run lifecycle has a `suspended` state between a suspending tool and the continuation that resumes it, and every turn ends in a recorded end state, so a kernel token minted for a suspended or ended turn is refused (SPEC-07).
REQ-0628: A check task for a subject pins the collect outcome's prover-context blobs among its inputs and puts them in its prompt, so a reviewer sees what changed against the base.

## 5. Design

**Contracts** (`grindstone.contracts.work`; schema version 1 each):

| Model | Fields |
| --- | --- |
| `Task` | `id`, `project`, `origin` (template run and step, parent task, or command), `need`, `capability`, `mode` (`work`, `consult`, `check`), `goal`, `inputs` (`items: tuple[ItemRef, ...]`, `blobs`, `subject: SubjectRef \| None`), `output` (`report_schema`, `kinds`, `files` globs, `delivery: adapter \| None`), `checks` (SPEC-08's `CheckSpec` tuple), `tier`, `lane`, `parent` |
| `Run` | `id`, `task`, `number`, `state`, `cause`, `manifest: RunManifest`, `agent_user`, `started_at`, `ended_at` |
| `Turn` | `run`, `number`, `session`, `prompt: BlobRef`, `kind` (`grindstone`, `corrective`, `steering`), `model`, `state` (`open`, `suspended`, `ended`), `outcome`, `report` |
| `Report` | `outcome` (`done`, `blocked`, `failed`; `waiting` only from a suspending tool), `summary`, `data` (validated against `report_schema`), `files` (paths declared produced), `proposals` (draft revisions, SPEC-07's `propose`) |
| `ContextPack` | `items` (refs, with the rendered Markdown as a blob), `principles` (refs), `skills` (name and hash; empty in M1), `prover_context` (blobs, for check tasks); hashed with `semantic_hash` |

Kernel error codes declared here (in `grindstone.contracts.errors`): validation `report_invalid`, `report_already_accepted`; limit `match_none`, `match_ambiguous`.

Events: `task.created`, `task.transitioned` (with the task's delivery target and subject when it enters `delivering`), `run.started`, `run.transitioned`, `run.ended`, `turn.started`, `turn.ended`.

**Task lifecycle** (writer: `work.transition_task`, the only one; FF-08):

| From | To | When (M1) |
| --- | --- | --- |
| `queued` | `running` | Ready, and its first run starts |
| `running` | `waiting` | A turn ends with outcome `waiting`, or collect's permission decisions are open |
| `waiting` | `running` | The continuation of the decision it waited on resumes the run |
| `waiting` | `verifying` | Every permission decision of collect is answered allow |
| `running` | `verifying` | The maker reported `done`, collect succeeded and raised no permission request |
| `running`, `waiting` | `blocked` | A run failed with a blocking cause, collect refused, or a collect permission was denied (`checks_failed`) |
| `verifying` | `delivering` | SPEC-08's gate passes and the task has a delivery target |
| `verifying` | `done` | The gate passes and there is no delivery target |
| `verifying` | `blocked` | The gate fails (`checks_failed`) |
| `delivering` | `done` | `delivery.delivered` for the task's delivery (the task is complete when its delivery reaches `delivered`, foundation v4.6) |
| `delivering` | `blocked` | `delivery.failed`, a cancelled delivery decision, or a gate that no longer passes at delivery (SPEC-08) |
| `blocked` | `queued` | An escalation answered `retry` |
| any but `done` | `cancelled` | An escalation answered `cancel` |
| `done` | `queued` | Reserved for a failing re-check (SPEC-12); no writer in M1 |
| `verifying` | `running` | Reserved for rework rounds (SPEC-18); no writer in M1 |

**Run lifecycle** (writer: `work.transition_run`): `preparing → active → collecting → succeeded`; `active ⇄ suspended` (a suspending tool; the continuation); `active ⇄ parked` (provider limits); `failed` (with cause) from every state but `succeeded`. **Turn states** (writer: `work.transition_turn`): `open → ended` with an outcome, or `open → suspended` by a suspending tool; a suspended turn stays suspended, and the resumed run starts a new turn.

**Matching (REQ-0603).** Filter, in order, the capabilities of the project's enabled factories:
1. those offering the need in the task's mode, by SPEC-03's mapping (`work` matches `delegate`);
2. if more than one remains, those in the requesting template's factory.

Exactly one remaining is the match. Otherwise the task is `blocked` with an `escalation` (`match_none` or `match_ambiguous`, recommendation `cancel`, reason naming the candidates). SPEC-17 adds the other filters and the project pin.

**Templates (REQ-0604).** `work.start_template(project, template, args, by, client_key)` validates `args` against the template's schema and records `work.template_runs`, whose `client_key` is unique per project. A `deliver` step's adapter becomes the preceding task's `output.delivery`. Each `task` step creates a task:
- **Inputs:** from an argument's item, follow the named edge types forward or inverted (for example, from `args.note`, follow `notes.cites`), each revision pinned at its current hash.
- **Checks:** the specs are kept on the task; SPEC-08's `plan_checks` validates them against the matched capability when the task enters `verifying`.

`task.transitioned` to `done`, `blocked` or `cancelled` advances or ends the template run through an event consumer, which reads the task's current state (SPEC-03, REQ-0319).

**Runs.** The workflow `run-<task>-<n>`, started with the run ID as its first input (SPEC-02):
1. **Prepare.** `stations.prepare_workspace(run, task, mode, provider_or_subject)` binds an agent user and prepares the workspace (part 1); `work` passes what part 1 cannot read from `work`. The base it returns is the run's subject version.
2. **Record** (transaction). Assemble the context pack: the pinned items rendered (SPEC-04); the project's current `core.principle` items, pinned; the capability's start skills; and, for a check task, the prover context (REQ-0628). Write the pack and the initial prompt as blobs with lease roots. The prompt is the capability prompt, then the project's `extra_prompt`, then the pack, the goal, and the output contract with the kernel tools to use. Write the run and its `RunManifest` (REQ-0605): the configured model is the instance's model for the capability's model slot (`[agents.<preset>].models`), and the configuration hashes come from SPEC-03.
3. **Turns.** Enqueue `turn-<run>-<k>` on `lane.<station>.writing` or `.readonly` and wait for it. The parent run waits off-lane, so it cannot deadlock (SPK-2, experiment 7).
4. **Act on the turn's outcome** by cause (REQ-0613), or collect (REQ-0615) on `done`.

**A turn** (the workflow `turn-<run>-<k>`, on the lane):
1. Mint the per-task MCP token for run and turn through the minting function the composition root registers with `work` from SPEC-07 (`work` may not import `surface`).
2. `stations.open_session` (key `<run>:s<k>`) as the run's agent user, with agent-neutral `SessionOptions` from the capability and the instance (part 1): model, effort, permission categories, `tool_timeout_seconds` above the consult ceiling as SPK-5 advises, `read_only` for a read-only workspace, and `notify` = this workflow.
3. `stations.prompt` (key `<run>:t<k>`).
4. Loop on `DBOS.recv(f"turn-{k}", timeout=60 s)`. Host events arrive as messages keyed by event ID (part 1). Each wake applies the liveness rule: `stations.last_activity(run)` against the timeout, unless `stations.open_calls(run)` is non-zero (REQ-0612).
5. On `permission.requested`: answer `deny` through `stations.answer_permission` (REQ-0614).
6. On turn end: with an accepted report, end the turn with its outcome; with none and no corrective prompt sent yet, send one (key `<run>:t<k>c`) naming the missing `report` call and keep waiting; otherwise end the turn and fail `missing_report`.
7. `stations.dispose` (key `<run>:d<k>`) and return.

A report rejected by validation leaves the turn open (REQ-0610): the agent sees the errors as its tool result and calls `report` again in the same turn.

**Suspending (REQ-0611, REQ-0627).** `work.suspend(run, turn, request)` is called by SPEC-07's `ask(need="operator")` and `request_permission`. In one unit of work it:
- records the turn's report with outcome `waiting` and moves the turn to `suspended`;
- moves the run to `suspended` and the task to `waiting`;
- raises a `question` or `permission` decision with the agent's recommendation and the continuation `work.resume_run`;
- sends the turn workflow a `suspended` message.

The tool returns its confirmation; the turn workflow disposes the session and frees the lane; the run workflow ends. The workspace and the agent user stay bound (part 1). When the decision is answered, its continuation runs `run-<run>-r<decision>`, which moves the run back to `active` and goes straight to turn `k+1` with the answer, or the permission outcome, at the top of the prompt. Because SPK-5 found that a client may not see a result delivered as its call is cut, the answer lives in the decision and the resumed prompt, never only in a tool result. `request_permission` suspends for the same reason `ask` does: the Concepts tab's lane rule, now stated in the foundation's suspending tools.

**Liveness (REQ-0612).** The seed is 20 minutes, from `[limits].liveness_timeout`; SPEC-17 owns the seeds and per-capability overrides. Activity is any host event for the session and any kernel tool call. Stall handling: cancel, dispose, fail `stalled`. No session waits on an ACP permission request in M1 (REQ-0614), so no pending request can hold a lane.

**Failures (REQ-0613).**

| Cause | Detected by | M1 handling |
| --- | --- | --- |
| `host_lost` | Part 1's reconciliation | Turn `k+1` in a new session on the same workspace; a second loss fails the run, and the task retries once with a fresh run, then blocks |
| `rate_limited`, `provider_error` | Host `error` events with that kind | Run `parked`; `DBOS.sleep` with exponential backoff (1, 2, 4 … 30 min); then a new turn; after 6 attempts, block |
| `context_exhausted` | Host `error` event | Block, with an escalation |
| `stalled`, `missing_report` | The turn workflow | Block, with an escalation |
| `storage_limit` | A blob put at record or collect (SPEC-02) | Block, with an escalation (`cap_reached` is SPEC-17's) |
| `checks_failed` | SPEC-08's gate, a refused collect, or a denied collect permission | Block, with an escalation carrying the failing evidence or the refused paths |
| `cancelled` | An escalation answer | Cancel the session if any, discard the workspace |

Escalations carry the cause, the run and the recommendation: `retry` for `host_lost`, `rate_limited` and `provider_error`; `cancel` otherwise, with the reason. `retry` queues the task again, and its next run gets a fresh workspace.

**Collect (REQ-0615).**
1. `stations.collect(run)` returns the `CollectOutcome` (part 1). A refusal fails the run `checks_failed` with the refused paths.
2. The output contract's declared files are read from the collected subject through its resolver (`read_file`), so checks and delivery see only what the subject holds, and stored as blobs with a lease root for the run.
3. If the run has proposals, `work` writes them as a blob and emits `change.draft_requested` (SPEC-04) with source `task output`, trust `trusted`, the task in the provenance, and client key `run:<run>`. `work` never calls `change`.
4. Each permission request raises a `permission` decision with the continuation `work.collect_answered`; the task is `waiting` until all are answered. Any `deny` fails the run `checks_failed`.
5. The task moves to `verifying`: `work` resolves each check's prover need with its matcher and calls `evidence.plan_checks(task, subject, maker, delegators, specs + extra_checks, resolved)` (SPEC-08, the one signature), which records the task's current subject and the checks; each mechanical check is started with `evidence.start_mechanical`, and each review check becomes a `check`-mode task (REQ-0622) whose accepted report `work` hands to `evidence.record_review`.
6. The workspace is discarded through part 1 when the run ends, except while the task waits on a decision of this run.

**Delivery hand-over.** On a passing gate for a task with a delivery target, `work` moves it to `delivering`; the `task.transitioned` event carries the target and subject, and SPEC-08's consumer prepares the delivery. `work` consumes `delivery.delivered` and `delivery.failed` and moves the task on, reading the task's current state first (REQ-0319).

**State and ownership.** Schema `work`: `tasks` (`state` by transition function), `task_runs` (`state` by transition function; manifest JSONB), `turns` (`state` by transition function), `reports` (insert-only), `template_runs`, `context_packs`. Readiness and "waiting on" are computed (FF-09).

**Interfaces.** `start_template`, `create_task`, `submit_report(run, turn, report) → errors | accepted`, `add_proposals(run, turn, items)` (SPEC-07's `propose`: stored on the run, insert-only, and read at collect step 3), `suspend`, `context_for(run)` (task, mode, pins, capability, current turn and its state, for SPEC-07), the continuations `resume_run` and `collect_answered`, the consumers of SPEC-08's evidence and delivery events, `set_token_minter`.

**Configuration** (instance sections owned here): `[agents.<preset>]` (`models`: slot → model), `[agents].force_preset`; `[limits]` (`liveness_timeout`, `corrective_prompts` = 1, `park_backoff`).

**Security.**
- B1: agents reach `work` only through SPEC-07's tools with a per-turn token, which is dead once its turn ends or suspends. Their writes reach intent only through a draft request, and checks only as the collected subject.
- Output files are read from the subject, never from the workspace, so nothing the agent left outside the subject is stored.

**Make and prove.**
- A `work` task makes; its proof is a separate `check`-mode task or job (REQ-0622). SPEC-08 refuses a check whose performer is the maker.
- A maker's own test runs are tool calls in its transcript: working notes, never evidence (M1-07, the working-notes clause, which SPEC-08 delivers).

**Fitness functions.**
- FF-08: `tasks.state`, `task_runs.state` and `turns.state` are registered with their transition functions (SPEC-04's single-writer check).
- FF-10: run record, corrective prompt, output-file copy-out and the draft request are registered external or transactional steps with crash-and-resume tests; part 1 registers the station steps.
- FF-07 covers `work`; FF-09: readiness is not a column.

## 6. Decisions

DEC-0601: In M1 a template is linear, and a `deliver` step attaches its adapter to the task before it · The task lifecycle already has `delivering`, so one task carries make, prove and deliver without a template engine · Rejected: building SPEC-19's graph engine now (M4 scope); a separate delivery task (a second lifecycle for the same work).
DEC-0602: Turns are child workflows on the lanes, and runs wait on them off-lane · The lane is held only while a session runs, so suspending or failing frees it at once (ADR-14) · Rejected: whole runs on lanes (a run waiting on a decision would hold the lane).
DEC-0608: In M1 an agent's own permission request is denied at once, and capabilities that would raise a decision for it are refused at load · A pending ACP permission request keeps the session waiting in its turn, so it would hold a lane until someone answers, and expiry to deny is SPEC-15's (review 1, F5) · Rejected: a timeout per request in M1 (a second expiry mechanism before SPEC-15's); raising decisions with no timeout (a lane held for days).
DEC-0609: Output files are read from the collected subject, not the workspace · Checks and delivery see only the subject, and the workspace may already be gone (review 1, F10) · Rejected: a second read path on the workspace provider (two sources for the same bytes).

## 7. Tickets and acceptance criteria

TKT-0601: Task, run and turn lifecycles, reports, matching, templates, context pack, manifest with configuration hashes · implements REQ-0601 to REQ-0605, REQ-0610, REQ-0627 · depends on TKT-0403, TKT-0302 · paths `packages/grindstone/src/grindstone/work/`, `packages/grindstone/src/grindstone/contracts/work.py`, `packages/grindstone/tests/work/`.
TKT-0603: Run and turn workflows: corrective prompt, suspend and resume, liveness, failure causes, permissions, collect, check tasks, delivery hand-over · implements REQ-0607, REQ-0608, REQ-0611 to REQ-0615, REQ-0622, REQ-0628 · depends on TKT-0601, TKT-0602, TKT-0802, TKT-0406 · `work` paths.
TKT-0606: Live run of the kernel's execution path with a real agent: a fixture capability on the Claude preset · implements REQ-0603, REQ-0607 · depends on TKT-0603, TKT-0503 · paths `packages/grindstone/tests/live/`, `docs/live/`.

AC-0601-1: Over random sequences of events (property test), the task state changes only through the table's transitions, and FF-08 finds no other writer of `tasks.state` · verifies REQ-0601 · property · `test_task_lifecycle_transitions`.
AC-0602-1: A queued task whose pinned revision no longer exists, or whose scope has an open blocking decision, is not ready; readiness has no column · verifies REQ-0602 · unit · `test_readiness_is_computed`.
AC-0603-1: With one fixture capability offering `notes.write` in `delegate` mode, a `work` task needing `notes.write` matches it; with two from different factories, the requesting factory's wins; with two in the same factory, or none, the task blocks with `match_ambiguous` or `match_none` in an escalation and no run exists · verifies REQ-0603 · unit · `test_thin_matching`.
AC-0604-1: A fixture template `task` → `deliver` creates one task whose output names the adapter, and the template run ends when that task is done · verifies REQ-0604 · unit · `test_linear_template_attaches_delivery`.
AC-0605-1: With the scripted preset, the run's manifest exists and holds every M1-06 field and both configuration hashes before the host receives `create_session` (asserted from the fake host's request log against the database's commit order) · verifies REQ-0605 · integration · `test_manifest_written_before_session`.
AC-0605-2: A host `model` event naming a different model from the configured one is recorded on that turn, and the manifest keeps the configured one · verifies REQ-0605 · unit · `test_turn_records_served_model`.
AC-0607-2: A run's turns, including those after a suspension and after a host loss, all run as the agent user its workspace was prepared for · verifies REQ-0607 · scripted agent · `test_turns_run_as_the_runs_user`.
AC-0607-1: With the writing lane at 1, a second writing turn starts only after the first disposes its session, and a turn that suspends frees the lane before the decision is answered · verifies REQ-0607 · integration · `test_turn_holds_lane_only_while_running`.
AC-0608-1: Scripted: a turn that ends without `report` receives exactly one corrective prompt; if it reports then, the run continues; if not, the run fails `missing_report` and an escalation is open · verifies REQ-0608 · scripted agent · `test_corrective_prompt_then_missing_report`.
AC-0610-1: Scripted: a report missing a required field is refused with `report_invalid` and a JSON pointer to the field, and a corrected report in the same turn is accepted and ends it · verifies REQ-0610 · scripted agent · `test_invalid_report_fixed_in_same_turn`.
AC-0611-1: Scripted: `ask(need="operator")` leaves the task `waiting`, the run `suspended` and an open `question` decision carrying the agent's recommendation, the session disposed and the lane free; answering it starts a new session on the same workspace whose first prompt begins with the answer, and the agent finds the file it wrote before asking; `request_permission` behaves the same with a `permission` decision · verifies REQ-0611 · scripted agent · `test_ask_operator_suspends_and_resumes`.
AC-0612-1: With the liveness timeout at 2 minutes, a scripted session that goes silent with no open kernel call fails `stalled` within one check interval after the timeout · verifies REQ-0612 · scripted agent · `test_silent_run_fails_stalled`.
AC-0612-2: With the same timeout, a scripted session holding a kernel call open for 5 minutes (a test-only slow tool) is not failed · verifies REQ-0612 · scripted agent · `test_open_kernel_call_pauses_liveness`.
AC-0613-1: Each failure cause, injected through the fake host or a full blob store, follows its retry rule in the table, and `retry` on an escalation starts a run with a fresh workspace · verifies REQ-0613 · integration · `test_failure_causes_follow_rules`.
AC-0614-1: A scripted ACP permission request is answered deny at once, no decision is raised, and the turn continues · verifies REQ-0614 · scripted agent · `test_agent_permission_requests_denied`.
AC-0615-1: When a scripted maker reports `done`, the fake provider's outcome is applied: the declared file is read from the subject and stored with a lease root for the run, one `change.draft_requested` is emitted for the proposals, the task is `waiting` while the permission decision is open, and it enters `verifying` with the extra check in its plan only after the decision is answered allow · verifies REQ-0615 · integration · `test_collect_hands_over_to_verifying`.
AC-0622-1: A review check for a maker's subject is a separate task in `check` mode with its own run, workspace, agent user and session · verifies REQ-0622 · integration · `test_checks_run_as_separate_tasks`.
AC-0627-1: After a suspension, the run is `suspended`, the turn `suspended`, and `context_for` reports the turn not open; after the answer the run is `active` at turn `k+1` · verifies REQ-0627 · unit · `test_run_and_turn_states_on_suspend`.
AC-0628-1: A check task created for a subject whose collect outcome carries a prover-context blob pins it and includes its content in the first prompt · verifies REQ-0628 · unit · `test_prover_context_reaches_check_task`.
AC-0603-2: Live run: a fixture template's task, needing `notes.write`, is matched to a fixture capability on the Claude preset, runs as Claude Code on the operator's subscription in its own workspace, writes its declared file and reports `done`; the run log, manifest and transcript are kept · verifies REQ-0603, REQ-0607 · live run · `live_m1_01_kernel_execution`.

## 8. Test plan

- **Unit:** AC-0602-1, AC-0603-1, AC-0604-1, AC-0605-2, AC-0627-1, AC-0628-1.
- **Property:** AC-0601-1.
- **Integration**, on real Postgres and DBOS with a fake host: AC-0605-1, AC-0607-1, AC-0613-1, AC-0615-1, AC-0622-1.
- **Scripted agent**, through the real host in its container (ADR-19): AC-0607-2, AC-0608-1, AC-0610-1, AC-0611-1, AC-0612-1, AC-0612-2, AC-0614-1.
- **Live run:** AC-0603-2.

## 9. Open items and risks

OQ-0602: Is 60 s the right `recv` interval for liveness checks? · Default: yes; QS-15 asks for action within one minute of the limit · Resolved by AC-0612-1's timing.

Risks mitigated: stalls and missing reports (liveness, corrective prompt); a waiting task holding a lane (suspend frees it; agent permission requests denied in M1); a lost host costing correctness (reconciliation, new session); configuration a run used left unrecorded (configuration hashes in the manifest).
Risk added: denying every agent permission request in M1 can stop work a capability needed. Mitigation: capabilities declare the categories they need up front (SPEC-09), the denial is in the transcript, and SPEC-15 adds decisions with expiry.

## 10. Rollout

The first migration creates schema `work`. No stored data exists before M1. `work`'s workflows start at `WORKFLOW_VERSION` "1" (SPEC-02).
