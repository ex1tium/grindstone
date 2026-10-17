# SPEC-08 — Check station, evidence and the delivery port
Status: draft · Milestone: M1
Kind: kernel · Owns:
- `grindstone.evidence`: check plans, check runs, evidence records, the freshness function, the gate, mechanical check execution, the `SubjectResolver` and `CheckMethod` ports, JUnit parsing.
- `grindstone.delivery`: deliveries, the idempotency ledger, mode observations, verification state, status posts, observe polling, bypass intake, the `DeliveryAdapter` port.
- The runner program's executors (`runner/`).

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

"Done" must mean that someone other than the maker proved the work against the exact intent and subject it claims, and that this proof goes stale on its own when either changes (ADR-11, ADR-12). Verified output must leave Grindstone only through a port that checks that proof again and records every effect once (ADR-26). This specification builds both halves for M1:
- check plans that refuse a maker as its own prover;
- mechanical checks on the credential-less check station;
- review verdicts from separate check tasks;
- evidence bound to input hashes, subject and environment;
- a freshness function that names what changed;
- the gate that moves a task on;
- a delivery port that asks for a decision, delivers, posts a verification state that follows freshness, merges itself only where the remote cannot enforce the gate, and reports every merge made outside it.

## 2. Scope

In scope:
- **Check plans.** Plans with the plan-time make-and-prove guard, and acknowledgement lists for explicit passes.
- **Mechanical checks.** Execution for the shapes `command` and `test`: job building, the runner's executors, JUnit parsing, the method's interpretation.
- **Review checks.** Evidence from check tasks' verdict reports; the kernel's review verdict contract.
- **Evidence.** Records, freshness for the inputs, subject and environment, and the task gate.
- **Delivery.** The port, deliveries and their lifecycle, the idempotency ledger, `delivery` decisions, mode observation and the switch escalation, verification state and its re-evaluation, Grindstone-performed merges in unenforced mode, observe polling and `delivery_bypass` intake.
- **Ports.** The SDK ports `SubjectResolver`, `CheckMethod` and `DeliveryAdapter`.

Out of scope:
- **Other shapes.** `reproduce` and `cross_tool` execution: R1. The `manual` method and its decision: SPEC-15 (M3).
- **Staleness at scale.** The regression sweep, re-check tasks, reopening done tasks, and freshness property tests over every subject kind: SPEC-12 (M2). M1's freshness covers the M1 subject kinds and is the function SPEC-12 extends.
- **Advisory checks** raising `suggestion` decisions: SPEC-15.
- **Observe beyond bypass.** Review comments and external check failures as findings: SPEC-24 (M5).
- **Ledger housekeeping.** Retention and archival of evidence and the delivery ledger: SPEC-27.
- **The GitHub adapter, the SDLC check method and the SDLC check plan:** SPEC-09.

## 3. Foundation links

Implements:
- **ADR-12.** Checks prove a target item for a typed subject by a kernel method or a factory method mapped to one. Gating evidence comes only from a credential-less check station or a different capability in read-only mode. A maker's own runs are working notes.
- **ADR-11.** Each evidence record stores its input hashes, subject version and environment fingerprint. Freshness compares them on read and names any mismatch; it is never stored. Environment changes stale only methods that declare the environment relevant.
- **ADR-26.** The kernel owns the port (`prepare`, `deliver`, `observe`), the `delivery` decision and the idempotency ledger. Adapters are factory code. Only verified subjects are delivered.
- **ADR-40, port side.** The mode is observed, recorded with its time, and shown on every delivery decision. In unenforced mode the kernel re-checks freshness and has the adapter merge with the verified head. A merge or published change outside a delivery becomes a high-severity `untrusted` `delivery_bypass` finding. A switch from enforced to unenforced raises an escalation before the next delivery.
- **I-04.** A task leaves `verifying` for `done` or `delivering` only through the gate.
- **I-05.** No freshness column exists anywhere; one function computes it.
- **I-08.** Agents never deliver. Adapters deliver only after a decision and only subjects the gate passes; the port re-checks immediately before delivering and before merging.
- **I-15.** A check plan refuses a prover equal to the maker, and evidence refuses a performer equal to the maker.
- **QS-01, QS-02, QS-03.** A weakened test fails the reviewer's check, so the task stays in verifying. A changed criterion makes evidence stale on the next read and the verification state pending. The check station holds no credential (SPEC-05).

Delivers:
- **M1-02**, the kernel clauses → AC-0806-1, AC-0806-2, AC-0814-1, AC-0814-2, AC-0815-1, AC-0816-1:
  - "the verification status succeeds only when every criterion's … test passes on the check station at the subject commit against the … current item hashes";
  - "a new head commit or a changed criterion sets it back to pending";
  - in unenforced mode, the port "detects the unenforced mode, merges only itself with the verified head SHA, and reports a merge made outside it as a `delivery_bypass` finding".

  SPEC-09 delivers the GitHub side and the enforced ruleset on the test repository.
- **M1-07**, the plan-time and evidence clauses → AC-0801-1, AC-0804-1, AC-0807-1:
  - a check plan whose prover is the maker is refused, at plan time as well as at load (SPEC-03);
  - "the implementer's own test runs are stored as working notes and never satisfy a required check";
  - every required check, a review included, "must pass before the status can succeed".

  SPEC-09 makes the test reviewer required in the SDLC plan.

Depends on:
- **SPEC-01:** `SubjectRef`, `ItemRef`, `BlobRef`, errors.
- **SPEC-02:** workflows, external steps, blobs, the check lane, schedules.
- **SPEC-03:** registries (check methods and shapes, adapters, resolvers), the SDK, project configuration.
- **SPEC-04:** current hashes, check-dependency edges, ChangeDrafts for intake, decisions and continuations.
- **SPEC-06:** `stations.dispatch_job` and the runner envelope, `stations` only.

Scenarios: K1 step 6 (a check runs read-only against the blob and records evidence against inputs, subject and environment) and step 8 (fresh, passing evidence moves the task on). K4 step 3 (evidence pinned to the old item is stale).

## 4. Requirements

REQ-0801: `plan_checks` turns a task's check specifications into checks with their method, shape, performer (a check station, or a capability resolved by need), required flag, targets, parameters and acknowledgement list, and refuses with `maker_cannot_prove` any check whose performing capability is the task's maker or one that delegated to it.
REQ-0802: Each check target's inputs are its semantic hash and the hashes of the items its check-dependency edges reach in one hop, captured when the check runs.
REQ-0803: A mechanical check runs as one runner job on the project's check station, with the subject materialized read-only by its resolver; its method builds the job and interprets the result; an `error` outcome is retried once with a new job and then recorded as `error`.
REQ-0804: Evidence is recorded only from a runner job's result or from the accepted report of a `check`-mode task, never from a maker's run, report or transcript; a performer equal to the maker is refused.
REQ-0805: An evidence record is immutable and stores its check, method, performer (capability hash, or station and image digest), station tier, subject, input hashes, environment fingerprint, result per target (`pass`, `fail`, `error`, `inconclusive`), details, output blobs and timings.
REQ-0806: `freshness(record)` returns fresh, or stale with every mismatch named: an input hash that differs from the item's current hash, a subject that differs from the task's current subject, or, for methods that declare the environment relevant, a fingerprint that differs from the station's current one.
REQ-0807: The gate for a task passes only when every target of every required check has a latest fresh record with `pass`, and every acknowledgement of that check is explicitly passed; it fails when any such latest fresh record is `fail` or `error`; otherwise it is not yet decided.
REQ-0808: A review verdict report gives a verdict and a reason for every target of its check and for every acknowledgement listed, and is refused with `report_invalid` otherwise.
REQ-0809: The runner executes one job at a time as its own user, in the read-only subject, with an environment built from the job's declaration, writing only to the job's `out/`, and reports each step's exit code, duration and log, truncated to a configured size.
REQ-0810: JUnit XML results are parsed with entity expansion off and a size limit, and become test outcomes with name, class, file, status and duration; an unparseable file is an `error` result, never a pass.
REQ-0811: `prepare` records a delivery once per delivery key, which its adapter derives from the task, target and subject, and raises a `delivery` decision with the fixed recommendation `deliver` only when the gate passes, its reason, the evidence with freshness and the mode just observed.
REQ-0812: Before each delivery decision the port observes the target's mode and records it with its time; a change from enforced to unenforced since the last observation raises an escalation instead, and the delivery decision is raised only after that escalation is answered.
REQ-0813: The `deliver` continuation re-checks the gate, then calls the adapter's `deliver` and `publish_status` as external steps keyed by delivery, and in unenforced mode re-checks the gate again and calls `merge` with the verified subject; a gate that no longer passes stops the delivery and returns the task to `blocked` with the reason.
REQ-0814: The verification state of a delivery is `success` exactly when the gate passes for the delivery's subject and the target's head equals that subject, `failure` when the gate fails, and `pending` otherwise; the port posts it whenever it differs from the last state posted for that head.
REQ-0815: The port re-evaluates every open delivery's verification state when a ChangeSet changes any of its evidence inputs, when evidence is recorded for it, and on every observation of a new head.
REQ-0816: Observing a merge of a delivery's change not performed by the port, or a change to a published path not made by a delivery, drafts one `untrusted` ChangeSet with a high-severity `core.finding` of type `delivery_bypass` about the delivery's task, whose approval is flagged `untrusted`.
REQ-0817: Observe polls every delivered, unmerged delivery on a schedule without backfill, and each adapter call is an external step whose repeated observation records nothing new.

## 5. Design

**Contracts.**

`grindstone.contracts.evidence`, schema version 1 each:
- `CheckSpec`: `method`, `by` (`station`, or a need), `required`, `targets` (a selection: kinds among the task's inputs, or explicit IDs), `params` (JSON for the performer), `acknowledge` (keys the prover must pass explicitly).
- `Check`: `id`, `task`, `spec`, `shape`, `performer` (capability or station), `definition_hash`.
- `EvidenceRecord`: the fields of REQ-0805, one per target.
- `TestOutcome`: `name`, `classname`, `file`, `status` (`passed`, `failed`, `error`, `skipped`), `duration_ms`.
- `ReviewVerdict`, the report schema every review capability's own schema must include: `verdict`, `targets` (each `item`, `verdict`, `reason`, `refs`), `acknowledgements` (each `key`, `verdict`, `reason`).

`grindstone.contracts.delivery`:
- `Delivery`: `id`, `project`, `task`, `adapter`, `target`, `subject`, `key`, `state`, `mode`, `external` (adapter-owned references).
- `ModeObservation`: `target`, `mode` (`enforced`, `unenforced`), `detail`, `at`.
- `VerificationState`: `state` (`success`, `pending`, `failure`), `description` (≤ 140 characters), `evidence_hash`.
- `Observation`: `kind` (`head`, `merged`, `closed`, `bypass`), `by_port` (bool), `data`, `external_id`.

Error codes registered here:
- rule: `maker_cannot_prove`, `gate_not_passed`;
- transient: `check_station_unavailable`;
- validation: `resolver_missing`.

Events: `evidence.recorded`, `check.started`, `delivery.prepared`, `delivery.delivered`, `delivery.merged`, `delivery.closed`, `delivery.failed`, `delivery.mode_observed`, `delivery.status_posted`.

**SDK ports** (part of SDK 0.1.0, SPEC-03):

| Port | Methods |
| --- | --- |
| `SubjectResolver` (per subject kind) | `materialize(ctx, subject, dest)` writes the subject's files read-only into `dest`; `read_file(ctx, subject, path)` returns bytes. The kernel ships the resolvers for `blob`, `blob_set` and `item_revision`; a factory registers the one for `git_commit` in projects it serves. A project with two enabled factories resolving one kind is invalid (`grindstone check`) |
| `CheckMethod` | `shape`, `env_relevant`; `build_job(ctx, check, subject) → JobPayload`; `environment(ctx, subject) → fingerprint fields` (toolchain versions it declares); `interpret(ctx, check, result, outcomes, subject) → per-target results` |
| `DeliveryAdapter` | `observe_mode(ctx, target) → ModeObservation`; `prepare(ctx, task, subject, summary) → key, prepared`; `deliver(ctx, delivery, key) → external`; `publish_status(ctx, delivery, head, state, key)`; `merge(ctx, delivery, verified_subject, key)`; `observe(ctx, delivery, etags) → observations` |

Every method that has an effect takes the idempotency key the port passes (SPEC-02). The adapter must find its earlier effect by that key, or by a lookup the adapter documents, before creating anything.

**Plans (REQ-0801).**
1. `work` resolves each check's prover need with its matcher (SPEC-06) and calls `evidence.plan_checks(task, maker, delegators, specs, resolved)`.
2. The kernel adds any `extra_checks` the workspace provider returned at collect.
3. Checks are added, never removed (Concepts, "Required and advisory").

A plan with a prover equal to the maker or a delegator fails `maker_cannot_prove`, and `work` blocks the task with an escalation. This repeats SPEC-03's load-time rule against the actual maker.

**Mechanical checks (REQ-0803).** The workflow `check-<check>-<subject>`:
1. `resolver.materialize` into a staging directory.
2. `method.build_job` produces the payload.
3. `stations.dispatch_job` (SPEC-06) runs it on `lane.<check station>.check`.
4. For shape `test`, parse the JUnit files from `out/` (REQ-0810).
5. `method.interpret` gives the per-target results.
6. Record one evidence row per target, with output blobs (logs and JUnit) rooted by the evidence.

An `error` outcome (job crash, timeout) starts one more job keyed `…:retry1`, then is recorded `error` (Failure model). Environment fingerprint: `{station, image digest from [images], tier, method.environment(…)}`.

**Review checks (REQ-0808, REQ-0804).**
1. `work` creates a `check`-mode task for each review check (SPEC-06, REQ-0622): need by the spec, read-only workspace from the subject, report schema including `ReviewVerdict`, and the check's `params` and `acknowledge` in its prompt.
2. On its accepted report, `work` calls `evidence.record_review(check, subject, performer, verdict)`.
3. That function refuses a performer equal to the maker, validates coverage of targets and acknowledgements, and records one row per target.

Environment is not relevant to `review`.

**Only two doors (REQ-0804).** `record_mechanical` is called only from the mechanical check workflow, and `record_review` only from `work`'s check-task report handler. There is no other function that writes `evidence.evidence`, and FF-08's single-writer test covers the table. A maker's report claiming that tests passed, and its transcript of test runs (working notes, SPEC-06), are never inputs to either.

**Freshness (REQ-0806).** `freshness(record, now)` reads:
- `intent.current_hash` for each input;
- the task's current subject, its latest collected subject;
- for environment-relevant methods, the current fingerprint: the station's configured image digest and `method.environment(subject)`.

It returns `Fresh`, or `Stale([InputChanged(id, was, now), SubjectChanged(was, now), EnvChanged(field, was, now)])`. It is a pure function over those reads, and nothing caches it.

**Gate (REQ-0807).** For each required check and target, take the latest record that is fresh.
- **Pass:** every target passes, and the check's latest fresh report passed every acknowledgement.
- **Fail:** some latest fresh record is `fail` or `error`.
- **Not yet:** anything missing, stale or `inconclusive`.

`work` consumes `evidence.recorded` and moves the task (SPEC-06): pass → `delivering` or `done`, fail → `blocked` (`checks_failed`).

**Runner executors (REQ-0809).** `runner/src/grindstone_runner/`, standard library only (FF-01):
1. Pick the oldest `runs/<job>/` with `job.json` and no `out/STARTED`, and create `STARTED`.
2. Run each step as a subprocess with `cwd` in the subject, an environment of `PATH`, `HOME` and `TMPDIR` under `/tmp/<job>`, `GRINDSTONE_OUT` (the `out/` directory) and the job's declared variables, and a per-step timeout.
3. Logs go to `out/logs/<step>.log`, truncated at 4 MiB.
4. **`command`:** the steps in order, stopping at the first non-zero exit.
5. **`test`:** the gate steps, then the test step, which must write JUnit files under `$GRINDSTONE_OUT`.
6. Write `out/result.json` (SPEC-06's `RunnerResult`, with outputs `{steps, junit}`), then `out/DONE`.

The heartbeat from M0 continues. A job left `STARTED` without `DONE` after a runner restart is recorded `error` by its timeout (SPEC-06).

**JUnit (REQ-0810).** Parsed in the control plane with `xml.etree.ElementTree` over CPython 3.14's expat, which bounds entity amplification and never resolves external entities. Files over 16 MiB are refused. Only `testsuite` and `testcase` elements are read, with their `failure`, `error` and `skipped` children.

**Deliveries.**

| State | Leaves to (writer: `delivery.transition`) |
| --- | --- |
| `prepared` | `awaiting_decision` (decision raised), `awaiting_mode_review` (mode switched) |
| `awaiting_mode_review` | `awaiting_decision` (escalation answered `retry`), `cancelled` |
| `awaiting_decision` | `delivering` (`deliver`), `held` (`hold`), `cancelled` (`cancel`) |
| `held` | `awaiting_decision` (the operator asks again, SPEC-10) |
| `delivering` | `delivered`, `failed` |
| `delivered` | `merged`, `closed` (observed), `merged` (unenforced merge by the port) |

`delivery.delivery_keys (key unique, delivery)` is the idempotency ledger. `status_posts`, `mode_observations` and `observations` are insert-only. `delivered` ends the task (`work` moves it to `done`). Observation continues until `merged` or `closed`.

**Delivering (REQ-0811 to REQ-0813).**
1. `work` calls `delivery.prepare(task)` when the task enters `delivering`.
2. The port observes the mode, then raises the decision (REQ-0811, REQ-0812). Its recommendation is fixed: `deliver`, "every required check is fresh and passing at this subject". Its payload holds the subject, the evidence table with freshness, and the mode, which is shown on the card (ADR-40).
3. The answer's continuation runs `delivery-<id>`:
   - gate;
   - `adapter.deliver` (key `<delivery>:deliver`);
   - `publish_status` for the subject (key `<delivery>:status:<head>:<state>`);
   - if unenforced: gate again, then `adapter.merge` (key `<delivery>:merge`) with the verified subject. A concurrent push makes the remote refuse it (SPK-4, experiment 10), and the delivery then reports `failed` with the cause.

**Verification state (REQ-0814, REQ-0815).** `verification(delivery, head)` follows REQ-0814. Its description names the counts, for example "4/4 criteria fresh and passing" or "1 stale: AC changed". Re-evaluation runs in a consumer of `changeset.applied` (deliveries whose evidence inputs intersect the changed items), of `evidence.recorded`, and of `head` observations. `publish_status` is called only when the state differs from the last post for that head (`status_posts`), so repeats are free.

**Observe (REQ-0816, REQ-0817).** A DBOS schedule, every 60 s with no backfill (SPEC-02), starts `observe-<delivery>-<tick>` for each delivered, unmerged delivery. It calls `adapter.observe(…)` with the ETags it kept; SPK-4 measured an unchanged pull request as free. Then, by observation:
- **New head:** re-evaluate, which posts `pending` at that head.
- **Merged by the port:** state `merged`.
- **Merged by anyone else**, or a **bypass** (a published path changed outside a delivery): `change.draft` with source `intake`, trust `untrusted`, one `core.finding` (type `delivery_bypass`, severity `high`, `about` the task), then submit. Its approval is flagged `untrusted` (SPEC-04, I-07).
- **Closed:** `closed`.

Observations are recorded with the adapter's external ID, unique per delivery and kind. A repeated observation is a no-op.

**State and ownership.**
- Schema `evidence`: `checks`, `check_runs`, `evidence` (insert-only).
- Schema `delivery`: `deliveries` (`state` by transition function), `delivery_keys`, `mode_observations`, `status_posts`, `observations`.

Freshness, the gate and the verification state are never stored (FF-09). `status_posts` records what was sent, not what is true.

**Interfaces.**
- `evidence`: `plan_checks`, `start_mechanical(task, subject)`, `record_review`, `freshness`, `gate(task)`, `summary(task)`.
- `delivery`: `prepare(task)`, `deliver` (continuation), `verification(delivery, head)`, consumers, the observe schedule.

**Configuration.**
- Instance: `[checks].log_truncate`, `[checks].junit_max_bytes`, `[delivery].observe_seconds` (60).
- Project: `[checks].image` (SPEC-03).

**Security.**
- B2: the check station holds no credential (SPEC-05). It receives only the job directory; its results are parsed against a schema and nothing else in the directory is trusted.
- B3: adapter calls happen only in the control plane.
- Delivery happens only after a decision, and only for subjects the gate passes at that moment (I-08).
- Bypass findings are `untrusted`, so they wait for a person (I-07).
- JUnit and logs are untrusted bytes: bounded and parsed safely.

**Make and prove.**

| Subject | Maker | Prover |
| --- | --- | --- |
| The collected subject (a `git_commit` in SDLC) | The `work` task's capability | The check station (`command`, `test`) and each review capability, all different from the maker by REQ-0801 and REQ-0804 |
| Evidence records | The check station and review tasks | None needed: evidence is the proof, and it is immutable |
| Deliveries | The port, through the adapter | Not a subject; gated by evidence and a person's decision |

**Fitness functions.**
- FF-08: `evidence.evidence` has exactly two writers (the evidence doors), and `deliveries.state` one.
- FF-09: no freshness, gate or verification column.
- FF-10: the external steps are registered with crash-and-resume tests: job dispatch, adapter `deliver`, `publish_status`, `merge`, `observe`.
- FF-07 covers both schemas.

## 6. Decisions

DEC-0801: Review checks run as `check`-mode tasks created by `work`, which hands their verdicts to `evidence` · The module map has `work` above `evidence`, so evidence cannot create tasks; this keeps one task model (ADR-14) and keeps `evidence` the only writer of evidence · Rejected: `evidence` creating agent sessions itself (a second run machinery); a callback from `evidence` into `work` (an upward call).
DEC-0802: Acknowledgement lists on checks, passed explicitly by the prover · A provider can require that a prover look at specific things, such as files outside a declared scope, without the kernel knowing what they are · Rejected: factory-specific verdict fields read by the kernel (kernel code would interpret factory data).
DEC-0803: JUnit XML is the result format of shape `test` · It is what most test runners already write, so a project's toolchain needs no adapter of ours · Rejected: a Grindstone result format (every project would need a reporter); interpreting console output (fragile).
DEC-0804: The port orchestrates deliver, status and merge; adapters only perform them · The freshness re-check right before merging, and the keys, stay in kernel code that every adapter shares · Rejected: one adapter call that does all three (each adapter would re-implement the re-check and the ledger).
DEC-0805: In M1 a delivery ends its task at `delivered`; merging is observed afterwards · In enforced mode a person merges on the remote at L0–L2; the task's proof is complete when its verified change is delivered with a success state · Rejected: holding the task in `delivering` until merge (a task would stay open for as long as a pull request does).

## 7. Tickets and acceptance criteria

TKT-0801: Evidence: plans, records, freshness, gate, review recording, SDK ports for resolvers and methods · implements REQ-0801, REQ-0802, REQ-0804 to REQ-0808 · depends on TKT-0401, TKT-0302 · paths `packages/grindstone/src/grindstone/evidence/`, `packages/grindstone/src/grindstone/contracts/evidence.py`, `packages/grindstone/tests/evidence/`.
TKT-0802: Mechanical checks: job building, dispatch, JUnit, interpretation · implements REQ-0803, REQ-0810 · depends on TKT-0801, TKT-0602 · `evidence` paths.
TKT-0803: Runner executors · implements REQ-0809 · depends on TKT-0602 · paths `runner/src/grindstone_runner/`, `runner/tests/`.
TKT-0804: Delivery port: prepare, decisions, modes, deliver, status, merge, observe, bypass intake · implements REQ-0811 to REQ-0817 · depends on TKT-0801, TKT-0403 · paths `packages/grindstone/src/grindstone/delivery/`, `packages/grindstone/src/grindstone/contracts/delivery.py`, `packages/grindstone/tests/delivery/`.

AC-0801-1: A fixture plan whose review check's need resolves to the maker's capability fails `maker_cannot_prove`, and the task blocks with an escalation; with a separate reviewer it plans · verifies REQ-0801 · unit · `test_plan_refuses_maker_as_prover`.
AC-0802-1: A check on a target with one check-dependency edge captures both hashes as inputs, and changing the referenced item makes the record stale · verifies REQ-0802 · unit · `test_inputs_include_check_dependencies`.
AC-0803-1: A fixture `command` method's job runs on the check station; a job that times out is retried once with a new job and then recorded `error`; the job is never dispatched twice for one key after a crash · verifies REQ-0803 · crash-and-resume · `test_mechanical_check_retry_and_once`.
AC-0804-1: A scripted maker whose report says its tests passed, and whose transcript shows a passing test run, leaves the gate not yet decided until the check station's evidence arrives; recording review evidence with the maker as performer fails · verifies REQ-0804 · scripted agent · `test_maker_runs_are_working_notes`.
AC-0805-1: Evidence rows cannot be updated or deleted, and each carries every field REQ-0805 lists · verifies REQ-0805 · integration · `test_evidence_is_immutable_and_complete`.
AC-0806-1: Over generated histories (property test), `freshness` is stale exactly when an input hash, the subject, or a relevant environment field differs, names each difference, and ignores presentation edits and environment changes for `review` · verifies REQ-0806 · property · `test_freshness_names_every_mismatch`.
AC-0806-2: Applying a ChangeSet that edits a target criterion's semantic field makes its evidence stale on the next read with `InputChanged` naming it · verifies REQ-0806 · integration · `test_changed_criterion_stales_evidence`.
AC-0807-1: The gate passes only with every required target's latest fresh record `pass` and every acknowledgement passed; one stale record makes it not yet decided, and one `fail` makes it fail; an advisory check's result never changes it · verifies REQ-0807 · property · `test_gate_requires_fresh_passing_required_checks`.
AC-0808-1: A review report missing a target's verdict or an acknowledgement is refused with `report_invalid` listing it · verifies REQ-0808 · unit · `test_review_verdict_coverage`.
AC-0809-1: In the runner image, a job's steps run as `gs-runner` in the read-only subject with only the declared environment, a write to the subject fails, a log over the limit is truncated, and the result lists each step's exit code · verifies REQ-0809 · integration · `test_runner_executes_job`.
AC-0810-1: Valid JUnit becomes outcomes; a file with an entity-expansion bomb, an external entity or over the size limit gives an `error` result, never a pass · verifies REQ-0810 · security · `test_junit_parsing_is_safe`.
AC-0811-1: Preparing a delivery twice for the same task, target and subject records one delivery and one open decision, whose payload shows the mode, the evidence with freshness and the fixed recommendation · verifies REQ-0811 · integration · `test_prepare_once_with_decision`.
AC-0812-1: With a fake adapter whose mode turns from enforced to unenforced, the next delivery raises an escalation and no delivery decision until it is answered · verifies REQ-0812 · integration · `test_mode_switch_escalates`.
AC-0813-1: With a fake adapter, `deliver` then `publish_status` run once each across a crash after either, and in unenforced mode `merge` is called with the verified subject; when evidence went stale between decision and delivery, nothing is delivered and the task is blocked with the reason · verifies REQ-0813 · crash-and-resume · `test_deliver_rechecks_gate_and_runs_once`.
AC-0814-1: The verification state is `success` only with the gate passing and the head equal to the subject; after a new head is observed it is posted `pending` at that head · verifies REQ-0814 · integration · `test_verification_state_follows_head`.
AC-0814-2: Posting the same state for the same head twice sends one post · verifies REQ-0814 · unit · `test_status_posts_only_on_change`.
AC-0815-1: Approving a ChangeSet that changes a delivered task's criterion re-posts `pending` within one consumer run, with a description naming the stale criterion · verifies REQ-0815 · integration · `test_changed_criterion_sets_pending`.
AC-0816-1: A fake adapter observing a merge not performed by the port drafts one `untrusted` ChangeSet with a high-severity `delivery_bypass` finding about the task, whose approval is flagged `untrusted`; the same observation repeated drafts nothing more · verifies REQ-0816 · integration · `test_bypass_becomes_untrusted_finding`.
AC-0817-1: The observe schedule polls only delivered, unmerged deliveries; a missed period is skipped; an unchanged observation records nothing · verifies REQ-0817 · integration · `test_observe_schedule`.

## 8. Test plan

- **Unit:** AC-0801-1, AC-0802-1, AC-0808-1, AC-0814-2.
- **Property:** AC-0806-1, AC-0807-1.
- **Integration**, on real Postgres and DBOS with fake adapters and resolvers in the `notes` style and the real runner image: AC-0805-1, AC-0806-2, AC-0809-1, AC-0811-1, AC-0812-1, AC-0814-1, AC-0815-1, AC-0816-1, AC-0817-1.
- **Crash-and-resume:** AC-0803-1, AC-0813-1.
- **Scripted agent:** AC-0804-1.
- **Security:** AC-0810-1.

SPEC-09 runs the same port against a fake GitHub and the real test repository.

## 9. Open items and risks

OQ-0801: Which items does `core.finding`'s `about` field need beyond the task's targets for a bypass? · Default: the delivery's task targets (criteria) by ID, with the delivery and external reference in the description · Resolved by TKT-0804.
OQ-0802: Should a failing `error` evidence (check could not run) block the task, or wait for a retry decision? · Default: block with an escalation offering retry (Failure model) · Resolved by TKT-0802 with the escalation kinds of SPEC-04.

Risks mitigated: forged evidence (two doors, maker refused, check station credential-less); stale evidence counted (computed freshness, re-checked gate before delivering and merging); duplicate deliveries, statuses or merges (keys and lookups); bypass going unseen in unenforced mode (observe and findings).
Risk added: polling every 60 s spends API calls on changed pull requests. Mitigation: six calls a changed pull request and ETags for unchanged ones (SPK-4), against a limit of 5,000 an hour.

## 10. Rollout

The first migrations create schemas `evidence` and `delivery`. The runner image gains the executors. SDK 0.1.0 includes the three ports. No stored data exists before M1.
