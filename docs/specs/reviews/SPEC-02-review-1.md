# SPEC-02 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist, the foundation v4.5, SPK-2's report and the M0 code. Cross-cutting findings (X1 to X8) are in `M1-specifications-review-1.md`.

**Verdict: changes required.** One blocking finding (F1), plus X2 (FF-07 and FF-09 must be built here). The design is otherwise strong:
- it turns every SPK-2 lesson into a rule (explicit workflow version, start-up guard, async calls in the lifespan, deterministic IDs, keyed messages);
- the external-step rule with FF-10 is the right enforcement of QS-04;
- roots from the first write make ADR-04's GC promise checkable.

## Blocking

**F1. Idempotency keys derived from the DBOS workflow ID break under `fork`.** REQ-0204 derives the key from the workflow ID and step name (`<workflow ID>:<step name>[:<n>]`). The start-up guard's remedy for a stranded workflow is `grindstone workflows fork <id>`, which re-runs it under a new workflow ID from a chosen step. Take an external step that performed its effect and was killed before its checkpoint, the case the rule exists for. Re-executed under the fork, it gets a new key, and targets that find by key create the effect again: a second session or a second prompt. That breaks QS-04 exactly on the upgrade path the guard is for.

The foundation's Failure model derives keys "from the record that caused it (run ID, turn, ChangeSet ID, delivery key, content hash)", not from an engine identifier.
*Change:* REQ-0204 derives the key from the causing record's ID, which REQ-0205 already makes the workflow ID at first start. That ID is carried as a workflow input, so a fork, which copies inputs, keeps every key. Add a crash-and-resume criterion: an external step is killed after its effect, the workflow is forked, and the fake target still records one effect.

## Minor

**F2. REQ-0204 is stricter than its own design.** It says the target finds the earlier result "by that key". The design lets targets find by their own lookup instead: the GitHub side by branch and pull request, blobs by content hash. Checklist item 8 also allows "an idempotency key or lookup". *Change:* "…finds the earlier result by that key, or by a lookup on the causing record that the target documents".

**F3. A retried blob put adds a second lease root.** A put inside an external step, killed after its unit of work commits and before its checkpoint, runs again. Putting existing content "adds only the root", so the same owner gets two leases. This is harmless, because `release_leases` ends both, but it is a duplicate the store could avoid. *Change:* make lease roots unique on (blob, owner kind, owner ID) while unreleased, and have a repeated put return the existing root.

**F4. OQ-0201 should also cover isolation and retry.** REQ-0203 needs datasource transactions at SERIALIZABLE, retried on serialization failure. OQ-0201 asks only about exactly-once commits. *Change:* extend OQ-0201, and AC-0203-2 or a sibling criterion, to show that a DBOS datasource transaction runs at SERIALIZABLE and that a serialization failure is retried without a second checkpoint.

**F5. FF-07 and DBOS's outputs table.** Every module's datasource transactions write DBOS's outputs table in schema `store`. *Change:* FF-07, built here (X2), exempts that table explicitly.

**F6. Project usage counts distinct blobs.** "The sum of sizes of blobs with an unreleased root in the project" should say each blob is counted once, however many roots it has in the project.

**F7. Error codes below `platform`.** `store` cannot use SPEC-03's registry for `storage_limit`, `database_unavailable`, `workflow_version_mismatch` and `migration_failed` (summary, X5).

**F8. Neutral wording (summary, X8).** "The GitHub adapter by branch and pull-request lookup" becomes "a delivery adapter by its documented lookup".

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement, with method and test | pass |
| 4 | Exit criteria mapped | pass (M1-04, mechanism and coverage; each effect's owner registers it) |
| 5 | Citations, no contradiction | **fail**: F1 (Failure model keys); the `budget_exhausted` clash is correctly noted (X7) |
| 6 | Dependencies | pass (SPEC-01 only) |
| 7 | Ownership | pass; station registry row (X3) |
| 8 | Idempotency and crash tests | **fail**: F1 |
| 9 | Typed boundaries | pass |
| 10 | Migration and upgrade path | pass: guard, version check, drain or fork |
| 11 | Trust boundaries | pass |
| 12 | Derivations computed | pass (project usage is a view) |
| 13 | Dependencies pinned from a primary source | pass: `sqlalchemy` 2.1.5 (2026-10-16) and `dbos` 3.3.0 (2026-10-15) are the latest on PyPI |
| 14 | Cross-module choices as records | pass |
| 15 | Typed errors | pass, F7 aside |
| 16 | Test plan | pass |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory name | minor: F8 |
| 20 | Factory 5F | n/a |
| 21 | Maker and prover | pass |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | n/a |
| 24 | Fitness functions | **fail**: X2 (FF-07 and FF-09 are cited but built nowhere) |
