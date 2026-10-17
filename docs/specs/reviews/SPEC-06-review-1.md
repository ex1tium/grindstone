# SPEC-06 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist, the foundation v4.5, SPK-1, SPK-2 and SPK-5, and SPEC-05's file layout. Cross-cutting findings are in `M1-specifications-review-1.md`. The judgment on the SPEC-06 and SPEC-08 cycle, the author's question 3, is in the summary: split this specification into two parts.

**Verdict: changes required.** Four blocking findings: F1, F2, F3, and X1 (two of its four module-map violations are here). Three more items apply: the split (X6, question 3), X4 (configuration hashes in the manifest) and X2.

The core design is right:
- turns as child workflows on lanes, with runs waiting off-lane;
- suspension that frees the lane;
- liveness paused by open kernel calls;
- reconciliation from `list()`;
- signed, canonical host events;
- a host core that ADR-42 can live with.

## Blocking

**F1. A run's workspace belongs to one agent user, but its turns may get another.** SPEC-05 puts each run's workspace under its lane slot's subtree, `agents/<agent>/<run>/`. Only that agent user can write it, and no other agent user can read it. In SPEC-06:
- run step 1 prepares the workspace with `host.prepare_workspace(run, slot, archive)` before any slot is acquired;
- each turn then acquires "a slot", skipping locked rows (turn step 1).

Two consequences follow. When a run resumes after suspension or host loss (AC-0611-1, AC-0619-1), the next turn can land on a different slot, whose user cannot open the workspace. On the read-only lane, with four slots, a test reviewer's turn can run as a different user from the one that owns its workspace. With the seed configuration (one writing slot) the writing lane hides the defect, but the read-only lane does not.
*Change:* bind a run to one slot for its life. The run claims its slot at prepare, and every turn of that run waits for that slot. A run's lane concurrency is then the number of slots, which SPEC-05 already equates with agent users. Releasing the slot when the run ends, on every path, is a step of its own. Add a criterion: two read-only runs that each suspend and resume keep their own agent users and workspaces.

**F2. The run lifecycle has no state for a suspended run, and the kernel MCP token relies on one.** The run lifecycle is `preparing → active → collecting → succeeded`, with `parked` and `failed`. On suspension "the run workflow ends", and nothing moves the run out of `active`. SPEC-07 revokes tokens "by state": a token is valid while "the run is active and its current turn equals" the token's turn. A suspended run is still `active` at the same turn, so the turn's token stays valid for as long as the decision is open. Collect also waits on permission decisions with the run and task in states that do not say so (F7).
*Change:* add `active → suspended` (on suspension) and `suspended → active` (on resume) to the run lifecycle. Give turns their own end state (ended, with outcome), and have SPEC-07 check that the token's turn is open, not only that the run is `active`.

**F3. The run manifest lacks configuration hashes (X4).** REQ-0605 should add the instance and project configuration hashes (SPEC-01 review 2, N5), and AC-0605-1 should assert them.

**X1 here.** Collect step 3 calls `change` to draft. `work` must emit an event that `change` consumes instead, and must not call `delivery.prepare`. "Depends on: SPEC-08 … the delivery port" then reduces to the evidence gate and `plan_checks`.

## Minor

**F4. A Claude-specific option set in the kernel.** Turn step 3 sets `MCP_TOOL_TIMEOUT` in `work`, and the backend wrapper's environment list names it. ADR-41: "no Claude-specific path may enter the host or the kernel." *Change:* the kernel passes a neutral `tool_timeout_seconds` option, and the Claude preset (SPEC-05) maps it to `MCP_TOOL_TIMEOUT` in its environment allow-list.

**F5. ACP permission requests can hold a lane without bound.** When a capability says `otherwise: decision`, an agent's permission request raises a decision while the session waits. The turn is never failed for inactivity (REQ-0612), and expiry to deny is SPEC-15's. So in M1, one unanswered request holds the writing lane indefinitely, against the Concepts tab's "no task ever holds a lane while it waits". No M1 capability uses `decision` (SPEC-09 denies), so this is latent. *Change:* in M1, either refuse `otherwise: decision` at load, or give pending ACP permission requests a timeout that answers deny. The reviewer recommends refusing it at load until SPEC-15.

**F6. `request_permission` as a suspending tool.** This is consistent with the lane rule, but the Components tab lists only `delegate` and `ask(need="operator")` as suspending (summary, X7). Cite the lane rule as the reason in REQ-0611 or REQ-0614.

**F7. States while collect waits on permission decisions.** "The task enters `verifying` only once all are answered." Meanwhile the task stays `running` with no run in a lane. *Change:* the task goes `running → waiting` while collect's permission decisions are open, and back when they are answered, as for any other wait on a person.

**F8. The failure table lacks `storage_limit`.** M1 can hit it: SPEC-02 refuses puts over the limits. *Change:* add it as "block, with an escalation" (Concepts, "Failure causes"), with `cap_reached` noted for SPEC-17.

**F9. Host event ordering.** Out-of-order events are refused, and the host retries until it gets a 2xx. *Change:* say that the host delivers each session's events one at a time, in `seq` order, so a refused event never blocks behind a later one.

**F10. Reading output files.** Collect step 2 reads files "by the provider's `read_file`", but `read_file` is on SPEC-08's `SubjectResolver`, not on `WorkspaceProvider`. *Change:* read declared output files from the collected subject through its resolver. Checks and delivery use only the subject, and the workspace may already be gone.

**F11. Thinned readiness.** REQ-0602 drops prerequisite tasks and the project cap, and replaces "a free lane" with "configured", leaving the lane to the queue. That is acceptable, but say it is a thinning and name SPEC-17 and SPEC-19 for the rest.

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement | pass |
| 4 | Exit criteria mapped | pass (M1-01 kernel side, M1-03, M1-06 recording; supports M1-04) |
| 5 | Citations, no contradiction | **fail**: F2 (token revocation), F4 (ADR-41), X4 (configuration hash on every run) |
| 6 | Dependencies | **fail**: the cycle with SPEC-08 (question 3); X1 |
| 7 | Ownership | pass; station registry row (X3) |
| 8 | Idempotency and crash tests | pass (keys per run and turn; AC-0609-1, AC-0616-1, AC-0621-1) |
| 9 | Typed boundaries | pass (host control API versioned; generated contracts on both sides) |
| 10 | Migration | pass |
| 11 | Trust boundaries | **fail**: F2 |
| 12 | Derivations computed | pass |
| 13 | Dependencies pinned from a primary source | pass: every npm pin matches the registry's latest on 17 October 2026 |
| 14 | Cross-module choices as records | pass |
| 15 | Typed errors | pass |
| 16 | Test plan | pass (scripted agent for mechanisms; one live run where Claude Code is the point) |
| 17 | Terms | pass |
| 18 | One sitting | borderline: about twice the playbook's four pages; the split (question 3) fixes it |
| 19 | Kernel names no factory name | minor: F4 |
| 20 | Factory 5F | n/a |
| 21 | Maker and prover | pass (REQ-0622) |
| 22 | Cooperation | pass: only `ask(operator)`; need, mode and what crosses are stated |
| 23 | Irreversible actions | n/a |
| 24 | Fitness functions | pass for FF-10; FF-08 itself is X2 |
