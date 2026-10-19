# M1 specifications, re-check 1: C1 to C4 of confirmation 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10, none of their reviews, neither revision, and not confirmation 1 (19 October 2026). Its one edit to these specifications is ADR-47's two-sentence change to SPEC-09's model slots (foundation v4.7), which touches none of C1 to C4. This is the re-check that `M1-specifications-revision-2.md` asks for. As confirmation 1 recommended, it covers C1 to C4 only, and looks hardest at the two places where revision 2 departed from the proposals: the gate-state queue (C3) and the second process stop at release (C4).

Everything was checked against the specifications in `docs/specs/` at foundation v4.7, and against the module map in `scripts/ff/module_map.py`.

## Verdict

**C1 to C4 are closed.** Each now has a requirement, a design paragraph, a decision record and an acceptance criterion that would fail if the defect came back. Both departures from confirmation 1's proposals are sound:
- **C3:** posting only from passes on one queue closes the window between check and post that the proposal left open.
- **C4:** the second stop, at release, closes a cross-run leak that confirmation 1 did not name.

**Recommendation:** the operator can approve the ten specifications. Two small observations follow. Neither blocks approval; both belong to the tickets that implement the mechanisms.

## The four items

| Item | Where it is closed | Result |
| --- | --- | --- |
| **C1** New bases of a re-walked ChangeSet (SPEC-04) | REQ-0415; `WalkResult.bases`; the `walk_rounds.bases` column; "effective bases" in Walk; "Rules in M1", last bullet; "Approval and apply" steps 1–3; DEC-0407; AC-0415-1 | Closed. A ChangeSet's effective bases are its latest walk round's, and drafts keep round 1's, so provenance is preserved. The rules, the approval's context hash and the apply re-check all read the effective bases. A re-raised approval therefore passes the rules and applies when answered, and a base that moves again starts a new round. An answer to the superseded approval cannot apply the old round, because superseding refuses the answer. AC-0415-1 now covers both apply-after-re-raise and move-again. |
| **C2** Where the protocols live (SPEC-03, SPEC-06 part 1, SPEC-08) | SPEC-03 REQ-0316, "Where the protocols live", DEC-0308, AC-0316-2, TKT-0301; SPEC-06 part 1 REQ-0624; SPEC-08 "SDK ports", TKT-0804 | Closed. In `MODULE_MAP`, `platform`, `stations`, `evidence` and `delivery` may all import `contracts` and none may import `sdk`, so placing the protocols in `grindstone.contracts.ports` is exactly what lets them type their calls. The SDK may import `contracts`. AC-0316-2 checks object identity, an FF-01 fixture, and a schema bundle with no protocols in it. No specification still places a protocol in the SDK. |
| **C3** Stale `success` posted last (SPEC-08) | REQ-0813–REQ-0815, REQ-0818; "Delivering" step 3; "Verification state"; DEC-0806; OQ-0804; AC-0815-1, AC-0818-1; SPEC-02 REQ-0206 and DBOS setup step 3 | Closed. See the trace below. |
| **C4** Collect follows a swapped symlink (SPEC-06 part 1, SPEC-05, SPEC-09) | SPEC-06 part 1 REQ-0617, REQ-0629, "Workspaces" steps 2–3, `POST /v1/users/<user>/stop`, `agent_user_busy`, DEC-0610, AC-0629-1, TKT-0602; SPEC-05 TKT-0502 (`stopAll`); SPEC-09 REQ-0912, collect step 4, Security, DEC-0908, AC-0912-4 | Closed. See the trace below. |

### C3 traced

Confirmation 1's interleaving: a pass started by `evidence.recorded` computes `success`, then a ChangeSet changes a target criterion. Under revision 2's design:
1. The ChangeSet commits. Its consumer of `changeset.applied` then enqueues `gate-<delivery>-<event>` on `delivery.gate`, so the request always comes after the change.
2. The queue has global concurrency 1, so the `pending` pass cannot start until the `success` pass, including its post, has finished.
3. The `pending` pass reads current state when it starts, and so sees the changed criterion. It inserts a row because `pending` differs from the last row for that head, and it posts.

The remote ends at `pending`, whatever order the requests arrived or the posts completed in. A pass killed between its row and its post remains a pending workflow that occupies the queue's single slot, so on recovery it finishes before the next pass starts, and its post is idempotent by key. AC-0818-1 covers the interleaving with a delayed first post and the crash between row and post. The `deliver` continuation is a fourth caller that confirmation 1 missed; it also only requests a pass. The queue is declared through SPEC-02's module-queue registration.

Each reason DEC-0806 gives for rejecting the alternatives holds:
- SERIALIZABLE isolation orders rows, not the external posts that follow them.
- "Still latest before posting" leaves a gap between check and post.
- Per-delivery queues would have to be declared at start-up, and M1 sees a few posts a minute.

The cost of the design is that one slow `publish_gate_state` call holds every delivery's posts behind it. That is acceptable at M1's volume, and OQ-0804 measures it at the M1 review.

### C4 traced

The attack in confirmation 1 needs a live process of the agent user to swap a directory for a symlink while collect reads.
1. **No live process survives.** Before `provider.collect` runs, the host's `POST /v1/users/<user>/stop` runs `kill -KILL -1` as the bound user and returns only once `/proc` lists none of that user's processes. On Linux, `kill(-1)` signals every process the caller may signal in one pass that a concurrent `fork` cannot slip past, and a killed process cannot fork again. The stop is refused unless the user is bound to that run. Under DEC-0606 a user belongs to one run, so the kill is exact. If the stop does not finish within its bound wait, collect does not run (`agent_user_busy`, retried).
2. **A swap that happens anyway fails closed.** Collect opens every path component relative to its parent with `O_DIRECTORY | O_NOFOLLOW`, and the file itself with `O_NOFOLLOW`. A component that is, or has become, a symlink fails the run, naming the path. AC-0912-4 reproduces confirmation 1's fixture, a swap between listing and reading, and requires that the sentinel's content appear in no blob, commit or diff.
3. **The second stop, at release, is right.** Without it, a detached process (`setsid`, `nohup`) left by one run would survive into the next run bound to the same user. It could then read or tamper with that run's workspace, which is a cross-run leak. AC-0629-1 checks that the next run sees no process from the previous one.

Agent users run only in the `agent-host` container, and the reader runs in `grindstone`. A process of the agent user can reach the reader only through the shared `workspaces` volume, and once the user's processes are stopped nothing changes that volume during collect.

## Observations for the implementing tickets

These are not findings against the specifications. Each is a sentence for the ticket, or a test for it to add:
1. **Opening a FIFO (TKT for SPEC-09 collect).** REQ-0912 refuses FIFOs, and AC-0912-2 requires that a FIFO fail the run. But an `open()` of a FIFO with no writer blocks, and after the stop there is no writer, so a reader that opens before checking the type would hang. Either check the type with `fstatat(..., AT_SYMLINK_NOFOLLOW)` relative to the parent descriptor before opening, or open with `O_NONBLOCK`, then `fstat` and refuse anything that is not a regular file.
2. **Hard links in the workspace (TKT-0502, TKT-0602).** `O_NOFOLLOW` does not apply to hard links. An agent user that hard-links another run's file into its own workspace would have collect read that file as the control plane's user and commit it. The file must sit on the same `workspaces` volume, and the attack needs `fs.protected_hardlinks` to be off, because the agent user cannot read the target. It is on by default on current Linux kernels and Docker Desktop's WSL2 kernel. A start-up check that it is on, or refusing regular files whose `st_nlink` is greater than 1 at collect, would close this without relying on the host's setting. Only another run's workspace is exposed, not control-plane secrets, because those are not on that volume.

## Next

1. The operator approves SPEC-01 to SPEC-10, with SPEC-06 in two parts. Each specification's status then moves from "in review" to "approved".
2. The tickets in each section 7 become the M1 backlog, in the order of the specification graph.
