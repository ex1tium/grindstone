# SPEC-08 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist, the foundation v4.5, ADR-40 and SPK-4. Cross-cutting findings are in `M1-specifications-review-1.md`. The DEC-0805 thinning, the author's question 2c, is judged in the summary: acceptable with two conditions, listed here as F5.

**Verdict: changes required.** Blocking:
- F1;
- X1 (two of the four module-map violations, and the freshness read, are here);
- the delivery-port record (architecture review, A2), which this specification's port needs before TKT-0804.

The proof half is the strongest part of the M1 set:
- two doors to the evidence table;
- the maker refused at plan time and again at recording;
- freshness as a pure function that names every mismatch;
- a gate that treats stale as "not yet";
- JUnit parsed safely;
- the gate re-checked right before delivering and before merging.

## Blocking

**F1. The status-post key repeats when a state returns at the same head.** `publish_status` is keyed `<delivery>:status:<head>:<state>`. Take a head whose state goes `success` → `pending` (a criterion edit) → `success` (the edit is reverted by a later ChangeSet, or evidence is refreshed by a retry on the same subject). The second `success` reuses the first key. The adapter finds the earlier `success` post by that key and sends nothing, so the remote keeps showing `pending`, and merge stays blocked although the gate passes. That breaks M1-02's "succeeds only when…" in the other direction. SPEC-09's `publish_status` looks up the App's latest status on the context, which would catch it, but the key ledger answers first.
*Change:* key the post by the delivery, the head and the sequence number of the `status_posts` row it creates (or the `evidence_hash` plus the state), so each change of state at a head is a new key. Add a criterion for success → pending → success at one head, with three posts.

**X1 here.**
- Bypass intake must not call `change.draft` from `delivery`: emit `delivery.bypass_observed`, which `change` consumes.
- Preparing must start from `delivery` consuming `task.transitioned` to `delivering`, not from `work` calling `delivery.prepare`.
- Freshness must not read the task's current subject from `work`: `evidence` records the current subject per task when `plan_checks` runs for it.

## Minor

**F2. Bypass detection only while a delivery is open.** ADR-40 has `observe` report "any change to a published file on the default branch that did not come through a delivery". REQ-0816 and REQ-0817 watch the target branch only through "delivered, unmerged deliveries", so a push when no delivery is open is never seen. M1-02 asks only for outside merges, so M1 is covered. *Change:* add an open item that names the specification watching the default branch continuously (SPEC-24, which owns observe beyond bypass, or SPEC-27), with default "M1 detects bypass only while a delivery of that project is open", and say so on the delivery card.

**F3. The mode at project setup.** ADR-40 observes the mode "at project setup and before every delivery". REQ-0812 covers the second. *Change:* observe once when a project's configuration names a delivery target (a `project.configured` consumer), and show it on the project.

**F4. Error outcomes and OQ-0802.** The gate treats a latest fresh `error` as a failure, which blocks the task with `checks_failed`. That matches OQ-0802's default. Fold the answer into REQ-0807 and close OQ-0802.

**F5. Conditions for DEC-0805 (summary, question 2c).**
- A delivery observed `closed` without merge after its task is `done` raises an `escalation` naming the task.
- The specification states the M1 path for a delivered task whose evidence goes stale: the status goes `pending`, nothing re-checks before SPEC-12, and the operator re-runs the command.

**F6. Neutral wording (summary, X8).** "Pull request" in the risk and observe text becomes "a delivery's external change".

**F7. The port's shape.** Recorded by the proposed record on delivery-port operations (architecture review, A2). After it is accepted, the `DeliveryAdapter` table follows its names and marks the optional operations.

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement | pass |
| 4 | Exit criteria mapped | pass (M1-02 kernel clauses, M1-07 plan and evidence clauses) |
| 5 | Citations, no contradiction | **fail**: A2 (ADR-26); F2 is an acknowledged gap against ADR-40 once stated |
| 6 | Dependencies | **fail**: the cycle with SPEC-06 (question 3); X1 |
| 7 | Ownership | pass |
| 8 | Idempotency and crash tests | **fail**: F1 |
| 9 | Typed boundaries | pass |
| 10 | Migration | pass |
| 11 | Trust boundaries | pass (B2, B3; JUnit and logs bounded) |
| 12 | Derivations computed | pass (freshness, gate and verification state are functions; `status_posts` records only what was sent) |
| 13 | Dependencies | pass (none new; ElementTree over CPython's expat) |
| 14 | Cross-module choices as records | **fail**: A2 |
| 15 | Typed errors | pass |
| 16 | Test plan | pass |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory name | minor: F6 |
| 20 | Factory 5F | n/a |
| 21 | Maker and prover | pass (REQ-0801, REQ-0804; table in section 5) |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | pass: a delivery always waits for a person in M1; merges are revertible by a later change, as the foundation's L3 auto-merge assumes |
| 24 | Fitness functions | pass for FF-10; FF-08 and FF-09 themselves are X2 |
