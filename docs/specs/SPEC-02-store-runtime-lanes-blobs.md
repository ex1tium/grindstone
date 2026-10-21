# SPEC-02 — Store, runtime, lanes and blob store
Status: accepted (by the operator, 19 October 2026, after the reviews in `docs/specs/reviews/`) · Milestone: M1
Kind: kernel · Owns: `grindstone.store` (database access, schema migrations, unit of work, DBOS setup and workflow version, external-step idempotency helper, lanes as queues, blob store and its roots, crash harness, FF-07 table ownership, FF-09 no stored derivations)

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

Everything Grindstone records lives in one PostgreSQL (ADR-02), every workflow runs on DBOS Transact in the control-plane process (ADR-03), and every file that is not a commit lives in a content-addressed blob store (ADR-04). This specification gives the other modules the substrate they build on:
- a unit of work that commits a module's writes together with the workflow checkpoint that made them;
- a rule for external effects that makes a crash cost time, never a duplicate (QG-2, QS-04);
- lanes that serialize writing work and bound read-only work;
- a blob store in which no blob is ever without a root.

SPK-2 proved each mechanism with DBOS 3.3.0 in FastAPI; this specification fixes how Grindstone uses them.

## 2. Scope

In scope:
- Database access and per-module schema migrations.
- The unit of work.
- DBOS configuration in the FastAPI lifespan, with an explicit workflow version and a start-up guard against stranded workflows.
- The external-step rule and its helper.
- Lanes as DBOS queues.
- The blob store: put, open, roots, limits.
- The crash harness and the coverage check that every external step has a crash-and-resume test (FF-10).

Out of scope:
- **Lanes per agent account** (ADR-48, proposed in foundation v4.10): SPEC-17 (M3) adds an optional account to `LaneSpec`. M1 and M2 run one account, so the lanes here are that account's.
- Blob garbage collection, the `blob.stored` and `blob.collected` events, backup, restore and upgrade runbooks: SPEC-27 (M5). In M1 the store never deletes a blob.
- The station registry's sessions, jobs and workspaces, and dispatch onto lanes: SPEC-06.
- Instance configuration files and their validation: SPEC-03, which hands the store its settings.
- The event outbox: SPEC-03.
- Scheduled workflows' business logic: their owners (SPEC-08 polls deliveries). This specification sets only the backfill rule.

## 3. Foundation links

Implements:
- ADR-02: one database; each module owns one schema named after it; only that module's SQL touches it (FF-07).
- ADR-03: DBOS runs every workflow; workflow and step IDs are idempotency keys; agent sessions run as child workflows on lanes (writing, one at a time by default; read-only, small concurrency); waits on people never hold a workflow.
- ADR-04: content-addressed blobs on the `blobs` volume, written only by the control plane, rooted from the moment they are written, metadata in Postgres.
- I-06: the run record is written before a session opens. This specification gives SPEC-06 the transactional write that makes the guarantee survive a crash.
- QS-04, QG-2: the external-step rule (section 5).
- ADR-37: storage limits are a limit; exceeding one is `storage_limit`. The foundation's blob store paragraph still names `budget_exhausted`, which ADR-37 removed; this specification uses `storage_limit` as ADR-37 and the Limits table require.

Delivers:
- M1-04, the mechanism and its coverage: the external-step rule, deterministic workflow IDs and the crash harness → AC-0204-1, AC-0204-2, AC-0205-1, AC-0213-1, AC-0213-2. Each external action M1-04 names (session, prompt, copy-out, push, pull request, status) and the replay of duplicate host events is registered as an external step by its owning specification (SPEC-06, SPEC-08, SPEC-09), with its own crash-and-resume test; FF-10, added here, fails the build while any registered step lacks one.

Depends on: SPEC-01 (`BlobRef`, `ErrorEnvelope` and its codes, record IDs).

Scenarios: K1 step 5 (blob write keyed by content hash) and "killed at any step, the workflow resumes … with no second session, blob, check or decision".

## 4. Requirements

REQ-0201: The control plane launches DBOS inside the FastAPI lifespan with an explicit application version, its system tables in schema `dbos` of the same database, and only DBOS's asynchronous calls while the event loop runs.
REQ-0202: Each kernel module's tables live in a schema named after the module and are created and changed only by numbered SQL migrations the module ships; at start-up the store applies pending migrations in module-map order, in one transaction per migration, before DBOS launches.
REQ-0203: A unit of work is one SERIALIZABLE transaction, retried on serialization failure; inside a workflow it is a DBOS datasource transaction, so its writes and the step's checkpoint commit together or not at all.
REQ-0204: Every workflow step with an effect outside the database passes its effect an idempotency key derived from the ID of the record that caused the workflow, carried as a workflow input, and the step name; the effect's target finds the earlier result by that key, or by a lookup on the causing record that the target documents, before creating it, so a re-executed or forked workflow causes each effect once.
REQ-0205: Every workflow started for a record has an ID derived from that record, so starting it twice runs it once.
REQ-0206: Each station lane is a DBOS queue named `lane.<station>.<lane>` with the global concurrency its configuration gives; lanes are registered at start-up from the lane list the composition root passes in, together with any other named queue a module declares there with its concurrency (SPEC-08's `delivery.gate`, concurrency 1).
REQ-0207: At start-up, if workflows of another application version are pending, the control plane recovers its own, starts no new dispatch, and reports each stranded workflow with its ID, name and version.
REQ-0208: CI fails when the code of a registered workflow changes while `WORKFLOW_VERSION` stays the same, unless the change is recorded as compatible in `docs/upgrades.md`.
REQ-0209: `put_blob` streams content to the `blobs` volume, verifies its SHA-256, stores it once under a two-level fan-out of its hash, and in the same transaction records the blob and a lease root owned by the producing run or job; putting existing content adds only the root.
REQ-0210: Every blob row has at least one root from the moment it is committed; modules add and release roots only through the store's interface, inside their own unit of work.
REQ-0211: A blob over the per-blob limit, or one that would take its project over the per-project limit, is refused with `storage_limit`, and nothing is recorded.
REQ-0212: Opening a blob returns exactly the bytes stored under its hash; a stored file whose content does not match its hash is never served and is reported as `invariant_violated`.
REQ-0213: A crash harness kills the control plane with SIGKILL at a named kill point and restarts it; every external step is registered with its kill points, and FF-10 fails while a registered step has no idempotency key or no crash-and-resume test.
REQ-0214: Every scheduled workflow states whether missed periods are backfilled; the default is to skip them.
REQ-0215: SQL in a kernel module, in its code and its migrations, names only tables in its own schema, schema-qualified; FF-07 fails the build otherwise, exempting only DBOS's outputs table in schema `store` and DBOS's own schema `dbos`, which DBOS writes.
REQ-0216: No migration creates a column whose name says it stores a value the foundation defines as computed (freshness, staleness, readiness, coverage, a gate or verification state, a total); FF-09 fails the build otherwise.

## 5. Design

**Contracts** (in `grindstone.contracts.store`, schema version 1 each):

| Model | Fields |
| --- | --- |
| `LaneSpec` | `station: str`, `lane: writing \| readonly \| check`, `concurrency: int` (≥ 1) |
| `StoreSettings` | `database: DatabaseSettings` (the M0 dataclass becomes this contract), `blobs_dir: str`, `max_blob_bytes: int` (seed 2 GiB), `max_project_bytes: int` (seed 20 GiB) |
| `BlobRoot` | `blob: BlobRef`, `project: ProjectId`, `owner_module: str`, `owner_kind: str`, `owner_id: str`, `lease: bool` |

The kernel error codes `storage_limit` (limit class), `database_unavailable` (transient), `workflow_version_mismatch` (internal) and `migration_failed` (internal) are declared here, in `grindstone.contracts.errors` (SPEC-01), which `store` can import.

**Database access.** SQLAlchemy Core over psycopg 3 (`postgresql+psycopg://`), with one engine and pool for the process. Modules write SQL text through the unit of work; nothing uses the ORM. SQLAlchemy is already in the lockfile because DBOS depends on it; this specification pins it directly (DEC-0201).

**Table ownership (REQ-0215, FF-07).** Every kernel SQL statement names its tables schema-qualified (`intent.items`, never `items`). `scripts/ff/table_ownership.py` reads every string literal that holds SQL in each module's code and every statement in its migrations, and fails on a schema other than the module's own, or on an unqualified table name. Exempt: DBOS's outputs table in schema `store`, which every module's datasource transactions write through DBOS, and schema `dbos`. Cross-schema foreign keys are refused the same way.

**No stored derivations (REQ-0216, FF-09).** `scripts/ff/no_stored_derivations.py` reads every migration and fails on a column whose name matches a deny-list owned here: `fresh`, `stale`, `freshness`, `ready`, `readiness`, `coverage`, `covered`, `gate`, `verified_state`, `verification_state`, `total`, `usage`. Lifecycle state columns are not derivations and are FF-08's (SPEC-04). A fixture migration with each denied name fails it. The deny-list grows with the specifications that define new computed values.

**Migrations.** Each module ships `migrations/NNNN_<slug>.sql` inside its package. The store's runner reads `store.migrations (module, number, sha256, applied_at)` and applies pending files in module-map order (`store`, `platform`, `intent`, `evidence`, `decisions`, `memory`, `stations`, `change`, `work`, `delivery`, `surface`), each in its own transaction with `SET LOCAL lock_timeout`. An applied file whose hash later changes fails start-up with `migration_failed`, because migrations are append-only. A statement in module A's migration that names schema B fails FF-07 (above).

**Unit of work.**
- Inside workflows: a DBOS `SQLAlchemyDatasource` on the same database, with its outputs table in schema `store`. Steps that only write to the database are `@store.transaction` functions, which wrap `datasource.transaction()` at SERIALIZABLE isolation. DBOS records each one's result in the same transaction as its writes, so a step that committed never runs again (DEC-0202).
- Outside workflows (REST reads, start-up, the loader): `with store.unit_of_work() as uow:`, a SERIALIZABLE transaction retried up to five times on serialization failure with jittered backoff.

Both give the caller one object (`Uow`) with `execute`, `fetch_one` and `fetch_all`; modules never see a raw connection. Per-project serialization (ChangeSet apply, SPEC-04) uses a transaction-scoped advisory lock taken through `uow.lock(key)`.

**DBOS setup.** In the lifespan, as SPK-2 ran it:
1. `DBOS(config={...})` with `name="grindstone"`, the database URL, `dbos_system_schema="dbos"` and `application_version=WORKFLOW_VERSION`.
2. `DBOS.launch()`.
3. `await DBOS.register_queue_async(...)` for every lane and every declared module queue.
4. `await DBOS.apply_schedules_async(...)` for every schedule.

`WORKFLOW_VERSION` is a constant in `grindstone.store`, starting at `"1"`. DBOS recovers only workflows of its own version, and its default is a hash of the workflow source, which would strand every workflow in flight on any code change (SPK-2, experiment 8). So the version is explicit and changes only when workflow code changes incompatibly.

**Start-up guard (REQ-0207).** After launch, `DBOSClient.list_workflows(status=PENDING)` is filtered to other versions. If any remain, the process serves health, read-only status and the operator API, refuses to dispatch, and raises `workflow_version_mismatch` with the list. The operator then either runs the previous image until those workflows drain, or moves each one with `grindstone workflows fork <id>`, a thin wrapper over `fork_workflow(id, start_step, application_version=current)` that re-sends a pending message to the new ID, as SPK-2 found necessary. Waits on people never strand, because they live outside workflows as decision continuations (ADR-03, SPEC-04).

**Workflow-version check (REQ-0208).** Workflows register through `@store.workflow(name)`, a thin wrapper over `DBOS.workflow` that adds the function to a registry. `scripts/ff/workflow_versions.py` hashes each registered workflow's source (its body and the steps it calls by name) into `packages/grindstone/workflow-versions.json`. CI fails when a hash changes and neither `WORKFLOW_VERSION` rose nor `docs/upgrades.md` has an entry for that workflow saying the change is replay-compatible: steps only added after every existing step, none removed or reordered.

**External steps (REQ-0204).** The pattern from SPK-2, experiment 1:
- Every workflow started for a record takes that record's ID as its first input (`store.start` checks it). `@store.external_step(name, effect="…")` wraps `DBOS.step` and passes the step an `IdempotencyKey`, `<causing record ID>:<step name>[:<n>]`. A fork (`fork_workflow`) copies the inputs, so a step re-executed under a forked workflow ID gets the same key, and its target finds the earlier effect (review 1, F1). The DBOS workflow ID is never part of a key.
- The step hands the key to its target, which finds by it, or by a lookup on the causing record that the target documents, before it creates: the agent host by client key, a delivery adapter by its documented lookup, the blob store by content hash.
- A step runs at least once; the key makes its effect happen once.
- The registry of external steps (name, owning module, effect, kill points) is what FF-10 reads.

**Deterministic workflow IDs (REQ-0205).** Every `start_workflow` and `enqueue` goes through `store.start(workflow, id=…)`, which refuses a call without an ID and sets it with `SetWorkflowID`. IDs name the causing record, for example `run-<task>-<n>` and `turn-<run>-<k>` (SPEC-06), `decision-<decision>` (SPEC-04), `evt-<consumer>-<event>` (SPEC-03). Child workflows started inside a workflow get DBOS's deterministic `<parent>-<step>` IDs, so recovery never starts a second child (SPK-2, experiment 3). Messages between workflows (`DBOS.send`) always carry an idempotency key, for example a host event's ID, so a duplicate message is delivered once (SPK-2, experiment 5).

**Lanes (REQ-0206).** One queue per station lane, `lane.<station>.writing`, `lane.<station>.readonly` and `lane.<station>.check`, created with `global_concurrency` from `LaneSpec`. Seeds: writing 1, read-only 4, check 1, matching the capacity envelope. The store creates and names lanes; SPEC-06 decides what runs on them. A writing parent never waits on a child on its own lane. It ends its turn, as ADR-14 requires and SPK-2, experiment 7, showed deadlocks otherwise. SPEC-06 enforces this, and this specification's lane test keeps the control case as a regression test.

**Blob store.**

| Table (schema `store`) | Columns | Write pattern |
| --- | --- | --- |
| `blobs` | `sha256` (primary key, `sha256:<hex>`), `size`, `media_type`, `first_seen` | Insert only |
| `blob_roots` | `id` (UUIDv7), `blob`, `project`, `owner_module`, `owner_kind`, `owner_id`, `lease`, `created_at`, `released_at` | Insert; `released_at` set once |

How each operation works:
- **Put.** Stream to a temporary file in `blobs/.tmp/`, hashing and counting as it goes; refuse at once on passing the per-blob limit. `fsync`, then `rename` to `blobs/<h0h1>/<h2h3>/<hex>`. Then, in one unit of work, insert the row (`ON CONFLICT DO NOTHING`) and the lease root, after checking the project's rooted total against its limit. A lease root is unique per blob and owner while unreleased, so a put repeated by the same owner returns its existing root instead of adding a second one. A crash after the rename leaves a file with no row, which the next put of the same content reuses; garbage collection (SPEC-27) removes it otherwise.
- **Roots.** `add_root(uow, blob, owner)` and `release_root(uow, root)` run inside the caller's unit of work, so a reference and its root commit together (ADR-04). `release_leases(uow, owner_kind, owner_id)` ends a run's or job's leases when it is archived.
- **Open.** `open_blob(hash)` returns a reader that hashes as it streams and fails with `invariant_violated` at end of stream if the content does not match. A blob is not served from a file whose row is missing.
- **Project totals** are a view: the sum of the sizes of the distinct blobs with at least one unreleased root in the project, each blob counted once however many roots it has there. Nothing is stored (FF-09).

**State and ownership.** Schema `store`: `migrations`, `blobs`, `blob_roots`, DBOS's datasource outputs table. Schema `dbos`: managed by DBOS. No lifecycle columns.

**Behaviour and failure.**
- Postgres unavailable: the unit of work raises `database_unavailable` (transient class). Health turns red, and DBOS resumes workflows when the database returns (Failure model).
- Blob store full (`ENOSPC`): the put fails `storage_limit` with the cause, and the temporary file is removed.

**Crash harness (REQ-0213).**
- `GRINDSTONE_KILL_AT=<point>` makes `store.kill_point(name)` SIGKILL the process the first time execution reaches that point, with a marker file in a test directory, as in SPK-2.
- `tests/crash/` provides a fixture that starts the control plane as a subprocess against a test database, kills it at a point, restarts it and returns the recorded effects.
- Each external step declares its points: by default `before:<step>` and `after:<step>`, between the effect and its checkpoint.

**Interfaces.**
- Python, `grindstone.store`: `unit_of_work()`, `transaction`, `workflow`, `external_step`, `start`, `kill_point`, `put_blob`, `open_blob`, `add_root`, `release_root`, `release_leases`, `project_usage`, `lanes`, `WORKFLOW_VERSION`.
- CLI: `grindstone migrate` (apply and exit) and `grindstone workflows list|fork`.

**Configuration.** `StoreSettings` and the `LaneSpec` list come from SPEC-03's instance configuration (`[store]`, `[stations]`); the store reads no files itself, except the database password file named in its settings.

**Security.**
- The `blobs` volume is mounted only in `grindstone` (ADR-01, FF-05).
- Blob contents are untrusted bytes. The store never interprets them, and media types are recorded, not trusted.
- The database password is read from its secret file and never logged. Errors carry only the exception class, as in M0.

**Make and prove.** The store produces no subjects. Its code is made by an implementer and proven by CI and a reviewer who did not write it.

**Fitness functions.**
- FF-10 is added: every registered external step has an idempotency key and a crash-and-resume test that names it.
- FF-07 is added (REQ-0215), over code and migrations of every kernel module; the specifications that own schemas rely on it.
- FF-09 is added (REQ-0216); `blob_roots` stores no total.
- The workflow-version check (REQ-0208) runs with FF-10 in `make ff`.

## 6. Decisions

DEC-0201: SQLAlchemy Core over psycopg 3, pinned `sqlalchemy==2.1.5` (PyPI, released 16 October 2026; already resolved through DBOS) · DBOS's transactional datasource needs a SQLAlchemy engine, and one engine for both keeps one pool and one transaction API · Rejected: psycopg alone (two connection paths, and database steps would lose exactly-once commits); the SQLAlchemy ORM (models would duplicate the Pydantic contracts, ADR-05).
DEC-0202: Database-only workflow steps are DBOS datasource transactions · Their writes and checkpoint commit together, so they never run twice, and modules need no idempotency code for their own tables · Rejected: plain steps with idempotent upserts everywhere (correct, but every write needs its own key and conflict rule). The fallback if OQ-0201 fails is exactly that.
DEC-0203: Plain numbered SQL migrations per module, run by the store · Each module owns its schema and migrates alone (Components, "Data model"); no generator is needed without ORM models · Rejected: Alembic (its strength, autogeneration, needs ORM metadata we do not have, and it adds a dependency).
DEC-0204: One explicit `WORKFLOW_VERSION`, a start-up guard, and drain or fork on an incompatible change · SPK-2 showed that DBOS strands workflows of any other version; the guard makes it visible instead of silent · Rejected: DBOS's default source-hash version (every release strands work); DBOS's workflow patching (`enable_patching`, `DBOS.patch`), which SPK-2 did not test. It is left to SPEC-27 to evaluate for upgrades (OQ-0202).
DEC-0205: Missed scheduled periods are skipped by default · Every M1 schedule is a poll whose next run covers the missed one · Rejected: backfill by default (a burst of identical polls after downtime).

## 7. Tickets and acceptance criteria

TKT-0201: Database access, migrations runner, unit of work · implements REQ-0202, REQ-0203 · depends on — · paths `packages/grindstone/src/grindstone/store/`, `packages/grindstone/tests/store/`, `pyproject.toml`.
TKT-0202: DBOS in the lifespan, workflow registry and version check, start-up guard · implements REQ-0201, REQ-0205, REQ-0207, REQ-0208, REQ-0214 · depends on TKT-0201 · same paths plus `packages/grindstone/src/grindstone/app.py`, `scripts/ff/workflow_versions.py`.
TKT-0203: External-step helper, kill points, crash harness, FF-10 · implements REQ-0204, REQ-0213 · depends on TKT-0202 · same paths plus `tests/crash/`, `scripts/ff/`, `tests/fitness/`.
TKT-0204: Lanes · implements REQ-0206 · depends on TKT-0202 · store paths.
TKT-0205: Blob store and roots · implements REQ-0209 to REQ-0212 · depends on TKT-0201 · store paths.
TKT-0206: FF-07 table ownership and FF-09 no stored derivations, with fixtures · implements REQ-0215, REQ-0216 · depends on TKT-0201 · paths `scripts/ff/`, `tests/fitness/`, `Makefile`.

AC-0201-1: The app starts against a fresh database with DBOS's tables in schema `dbos`, application version `WORKFLOW_VERSION`, and no synchronous DBOS call inside the lifespan · verifies REQ-0201 · integration · `test_lifespan_launches_dbos`.
AC-0202-1: A fresh database migrates in module-map order; a second start applies nothing; changing an applied migration file fails start-up with `migration_failed` · verifies REQ-0202 · integration · `test_migrations_apply_once_in_order`.
AC-0202-2: A migration of module A that names module B's schema fails FF-07 · verifies REQ-0202 · contract · `test_ff07_migrations_stay_in_their_schema`.
AC-0203-1: A datasource transaction step killed after commit is not re-run on recovery, and one killed before commit leaves no rows and is re-run once · verifies REQ-0203 · crash-and-resume · `test_transaction_step_commits_with_checkpoint`.
AC-0203-2: Two concurrent units of work that conflict both complete, one after a retried serialization failure · verifies REQ-0203 · integration · `test_unit_of_work_retries_serialization_failures`.
AC-0203-3: A DBOS datasource transaction step runs at SERIALIZABLE, and when two such steps conflict, the one that fails serialization is retried and completes with one checkpoint · verifies REQ-0203 · integration · `test_datasource_transaction_isolation_and_retry`.
AC-0204-1: An external step killed after its effect and before its checkpoint re-runs on restart with the same idempotency key, and the fake target records one effect · verifies REQ-0204 · crash-and-resume · `test_external_step_effect_once`.
AC-0204-2: An external step registered without an idempotency key fails FF-10 · verifies REQ-0204 · contract · `test_ff10_requires_idempotency_key`.
AC-0204-3: An external step killed after its effect and before its checkpoint, whose workflow is then forked from that step with `grindstone workflows fork`, passes the same key, and the fake target records one effect · verifies REQ-0204 · crash-and-resume · `test_forked_step_keeps_its_key`.
AC-0205-1: Starting a workflow twice with the same record ID runs it once; starting one without an ID is refused; a child started inside a killed parent exists once after recovery · verifies REQ-0205 · crash-and-resume · `test_workflow_ids_are_deterministic`.
AC-0206-1: With `writing` at concurrency 1, fifty workflows from two projects enqueued in parallel never run two at once, and the read-only lane never exceeds its concurrency · verifies REQ-0206 · integration · `test_lanes_bound_concurrency`.
AC-0206-2: A writing parent that waits on a child on its own lane is still pending when the test's timeout ends, and one that ends its turn lets the child run · verifies REQ-0206 · integration · `test_writing_parent_must_not_wait_on_its_lane`.
AC-0207-1: With a workflow pending under version `v1`, a start as `v2` dispatches nothing, reports the workflow, and `grindstone workflows fork` moves it so that it finishes once on `v2` · verifies REQ-0207 · integration · `test_stranded_workflows_block_dispatch`.
AC-0208-1: Changing a registered workflow's body without raising `WORKFLOW_VERSION` or adding an upgrade note fails the check; adding the note passes · verifies REQ-0208 · contract · `test_workflow_change_needs_version_or_note`.
AC-0209-1: Putting the same content for two owners stores one file, one row and two lease roots, and putting it again for the first owner adds no root; the file sits at its fan-out path, and its bytes hash to its name · verifies REQ-0209 · unit · `test_put_blob_is_content_addressed`.
AC-0209-2: A put killed after the rename and before the commit leaves no row; repeating the put records the blob once · verifies REQ-0209 · crash-and-resume · `test_put_blob_crash_records_once`.
AC-0210-1: For any sequence of puts, root additions and releases (property test), every blob row has at least one root at every commit, or had one at its own commit · verifies REQ-0210 · property · `test_every_blob_is_rooted`.
AC-0211-1: A put over the per-blob limit, or over the project's remaining allowance, fails `storage_limit` and leaves no file, row or root · verifies REQ-0211 · unit · `test_storage_limits_refuse_cleanly`.
AC-0212-1: A stored file altered on disk is refused when opened, with `invariant_violated` · verifies REQ-0212 · unit · `test_open_blob_detects_corruption`.
AC-0213-1: The harness kills at `after:<step>` for a registered step and restarts; the matrix runner runs every registered kill point of every registered external step · verifies REQ-0213 · crash-and-resume · `test_crash_matrix_runs_every_registered_step`.
AC-0213-2: Registering an external step with no crash-and-resume test naming it fails FF-10 · verifies REQ-0213 · contract · `test_ff10_requires_crash_test`.
AC-0215-1: FF-07 passes on the kernel, and fixtures with a query on another module's table, an unqualified table name, a cross-schema foreign key in a migration and a write to DBOS's outputs table (exempt, so it passes) behave as stated · verifies REQ-0215 · contract · `test_ff07_table_ownership`.
AC-0216-1: FF-09 passes on the kernel's migrations, and a fixture migration adding a column with each denied name fails it · verifies REQ-0216 · contract · `test_ff09_no_stored_derivations`.
AC-0214-1: A schedule declared without a backfill choice skips missed periods; one declared with backfill runs them · verifies REQ-0214 · integration · `test_schedule_backfill_is_explicit`.

## 8. Test plan

- Unit: AC-0209-1, AC-0211-1, AC-0212-1.
- Property: AC-0210-1, on Hypothesis sequences of operations against a real database.
- Integration, on real Postgres and DBOS: AC-0201-1, AC-0202-1, AC-0203-2, AC-0203-3, AC-0206-1, AC-0206-2, AC-0207-1, AC-0214-1.
- Crash-and-resume, with the harness: AC-0203-1, AC-0204-1, AC-0204-3, AC-0205-1, AC-0209-2, AC-0213-1. Fast set on every commit; the full matrix nightly.
- Contract, as fitness fixtures: AC-0202-2, AC-0204-2, AC-0208-1, AC-0213-2, AC-0215-1, AC-0216-1.

## 9. Open items and risks

OQ-0201: Do DBOS 3.3.0's datasource transactions keep exactly-once commits across SIGKILL, as SPK-2 showed for steps, run at SERIALIZABLE, and retry a serialization failure without a second checkpoint? · Default: yes, per DBOS's design (the output row commits in the user's transaction; the decorator defaults to SERIALIZABLE and retries serialization errors) · Resolved by TKT-0201's AC-0203-1 and AC-0203-3; on failure DEC-0202's fallback applies, with keyed upserts in every database step.
OQ-0202: Should incompatible workflow changes use DBOS patching instead of drain-or-fork? · Default: drain or fork (DEC-0204) · Resolved by SPEC-27, which owns upgrades (M5-06).

Risks mitigated: duplicate or lost side effects across crashes (external-step rule, FF-10); workflows silently stranded by an upgrade (explicit version, guard, CI check); a blob collected while referenced (roots from the first write); the writing-lane deadlock (lane test kept as a regression).
Risk added: SERIALIZABLE isolation can retry often under contention. Mitigation: the capacity envelope is small (one writing lane per station), and retries are counted in logs. A hot spot found in M1 is fixed locally with an advisory lock.

## 10. Rollout

There is no stored data before M1, so the first migration of each schema creates it. `WORKFLOW_VERSION` starts at `"1"`. `docs/upgrades.md` gains a section for workflow changes beside SPEC-01's schema changes. The M0 `DatabaseSettings` dataclass and `ping` move into `StoreSettings` and the unit of work with no behaviour change to `/readyz`.
