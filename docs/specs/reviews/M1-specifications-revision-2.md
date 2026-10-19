# M1 specifications, revision 2: how confirmation 1 was answered

Author: a session that reviewed the M1 specifications (review 1) and judged C1 to C4 before writing this revision. It did not write the specifications, their revision 1 or confirmation 1 (18 October 2026). It answers `M1-specifications-confirmation-1.md`: its four findings C1 to C4, and its eight small inconsistencies.

For C3 and C4, this revision takes the author's own judgment over the confirmation's proposed fixes. The reasons are given below. Because this session reviewed the same material earlier, the re-check of C1 to C4 must come from a session that wrote none of it.

## C1 to C4

| Finding | Change | Where |
| --- | --- | --- |
| **C1** New bases of a re-walked ChangeSet | A re-walk is a new walk round whose `bases` are the items' current hashes. The latest round's bases are the ChangeSet's *effective bases*, and the M1 rules, the approval's context hash and the apply re-check all read them. Drafts stay insert-only and keep the round-1 bases. AC-0415-1 now requires that answering the new approval applies the ChangeSet, and that a base which moves again asks again. | SPEC-04 REQ-0415, `WalkResult.bases`, `walk_rounds` columns, "Walk", "Rules in M1", "Approval and apply" steps 1–3, DEC-0407, AC-0415-1 |
| **C2** Where the protocols live | `Context`, its extensions and service handles, and the four port protocols are `typing.Protocol` classes in `grindstone.contracts.ports`, re-exported by the SDK as the same objects. `platform`, `stations`, `evidence` and `delivery` type against them without importing the SDK. The schema bundle exports no protocol. | SPEC-03 REQ-0316, "Where the protocols live", DEC-0308, AC-0316-2, TKT-0301 paths; SPEC-06 part 1 REQ-0624, TKT-0607 paths; SPEC-08 "SDK ports", TKT-0801 and TKT-0804 paths |
| **C3** Stale `success` posted last | **Fix differs from the confirmation.** The confirmation's mechanism, two computations ordered against an apply, would mostly be caught by SERIALIZABLE isolation. The race that remains is in the posts, which are external steps that complete after their rows commit, so an older post can land after a newer one. Its "post only if still the latest" check leaves a gap between check and post, and it missed a fourth poster, the `deliver` continuation. Now nothing posts directly: all four callers request a gate-state pass on one queue, `delivery.gate`, of concurrency 1. Each pass computes from current state when it starts, and posts only if the state changed for that head. Passes never overlap, and every change requests a pass after it, so the last post always matches the current state. | SPEC-08 REQ-0813–REQ-0815, new REQ-0818, "Delivering" step 3, "Verification state", DEC-0806, OQ-0804, AC-0815-1, new AC-0818-1, FF-10 line, TKT-0804; SPEC-02 REQ-0206 and DBOS setup step 3 (module queues besides lanes) |
| **C4** Collect follows a swapped symlink | **Both parts the confirmation proposed, plus one it missed.** The host stops every process of the run's agent user, and confirms none remain, before collect and again before the user is released. The second stop closes a leak the confirmation did not name: a process left behind by one run would otherwise survive into the next run bound to the same user. Collect then reads only through directory descriptors with `O_NOFOLLOW` at every path component, so a swap that happens anyway fails the run instead of redirecting the read. | SPEC-06 part 1: REQ-0617, new REQ-0629, "Workspaces" steps 2–3, `POST /v1/users/<user>/stop`, `agent_user_busy`, Security, DEC-0610, AC-0629-1, FF-10, TKT-0602. SPEC-05: the helper's `stopAll` (TKT-0502). SPEC-09: REQ-0912, collect steps 2 and 4, Security, DEC-0908, AC-0912-4 |

## The eight small inconsistencies

| Item | Change |
| --- | --- |
| Run directories "under the slot's subtree" | SPEC-05: under the bound agent user's subtree. |
| Two `plan_checks` signatures | SPEC-06 part 2 uses SPEC-08's single signature, with `work` resolving prover needs first. |
| `work.add_proposals` | Added to SPEC-06 part 2's interfaces (stored on the run, insert-only, read at collect). |
| `prepare_workspace(run)` needs task data | SPEC-06 parts 1 and 2: `prepare_workspace(run, task, mode, provider_or_subject)`, filled in by `work`. |
| `task_subjects` under the `delivery` bullet | SPEC-08: listed under schema `evidence`. |
| A cancelled task leaves its `delivery` decision open | SPEC-08: the `task.transitioned` consumer also handles `cancelled`, moving the delivery to `cancelled` and superseding its decision; the lifecycle table and AC-0811-1 follow. |
| A truncated diff passed unseen | SPEC-09: the test reviewer's prompt fails a truncated diff unless the reviewer acknowledges the truncation explicitly, with a reason. |
| Phase 2 refuses in one direction only | SPEC-03: stated as deterministic and safe; the start-up report names the other factory's capability or need for every refusal. |

## Checks

- `make check` passes: lint, pyright, tests, and fitness functions FF-01, FF-02, FF-04 and FF-13.
- No ID is defined twice (checked by FF-13).

## Next

1. A re-check of C1 to C4 only, by a session that wrote none of the M1 specifications, their reviews, their revisions or confirmation 1. It should look in particular at:
   - the gate-state queue (C3), whose design differs from the confirmation's;
   - the second process stop at release (C4).
2. The operator approves the ten specifications, with SPEC-06 in two parts.
