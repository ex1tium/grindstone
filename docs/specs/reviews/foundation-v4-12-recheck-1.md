# Foundation v4.12 re-check 1: answers to confirmation 1

24 October 2026 · Independent re-check. The reviewer wrote none of the material under review.

## Scope

- Branch `docs/foundation-v4-12` at `b6ea0aa` (PR #18). The answering commit is `git diff b6ea0aa~1 b6ea0aa`. It touches the foundation, SPEC-05, SPEC-06-1, SPEC-06-2, SPEC-09 and `docs/m0/status.md`, and adds the confirmation and revision records.
- Checked against `foundation-v4-12-confirmation-1.md` (D1 to D10) and `foundation-v4-12-revision-1.md`. Also checked against SPEC-02's external-step rule (REQ-0204, AC-0204-1, the key format and the FF-10 registry), the Components tab's error model (Fdn:1102–1112), and ADR-53, ADR-54 and ADR-55.
- D1 to D6 were re-checked in full. D7 to D10 were checked briefly.
- `uv run python -m scripts.ff.traceability` reports **FF-13 traceability: 0 violation(s)**. It was run on the local checkout, which matches `origin/docs/foundation-v4-12` at `b6ea0aa`.
- Line numbers refer to the files at `b6ea0aa`. "Fdn" means `docs/foundation/grindstone-foundation.md`, and "S06-1" means `SPEC-06-1-stations-agent-host.md`.

## Append-only rule and bookkeeping

- **Accepted records:** ADR-23 (Fdn:1673) and ADR-53 (Fdn:1917) changed only in their Status lines, each gaining an "Amended by ADR-57 (proposed)" pointer. Their Decision, Why and Rejected text is unchanged. ADR-55 and ADR-56 are untouched in this commit.
- **Proposed records:** ADR-57 and ADR-58 are revised in place, which is allowed while they are proposed. ADR-57's Status names ADR-23 and ADR-53 among the records it amends (Fdn:1959).
- **Records count:** the comma is fixed (Fdn:1442).
- **Revision history:** row 4.12 records confirmation 1 (Fdn:2378).
- **Gaps:** the ADR index rows for 23 and 53, and the SPEC-28 row of the spec map, do not follow (E5).

## Status of D1 to D10

| Finding | Status | Evidence |
| --- | --- | --- |
| D1 (blocking) | **Closed for plain sessions; a resumed session can still lose its directory (E2), and the marker is under-specified (E1)** | REQ-0631 (S06-1:83) and the disposal bullet (S06-1:168) say three things: the sweep skips sessions the host holds as live, age is an event marker the host touches on each event it emits, and a lost session inside the window survives. ADR-58 matches (Fdn:1969). AC-0631-1 (S06-1:255) asserts that a live directory survives the timer sweep however old, that a lost one inside the window survives the start-up sweep, and that a `resume` naming another run's directory is refused. Age no longer depends on directory mtime. |
| D2 | **Closed in substance; stale wording remains (E3, E4)** | The design is now three steps (S06-1:161–166): (1) Choose, with no external effect, checkpointed; (2) Create under `<run>:s<k>`, with `resume` only if chosen, whose checkpointed result is the session or the refusal; (3) Fall back under `<run>:s<k>n`, only after a recorded refusal. The no-resume path's key is stated (S06-1:163). The keys fit SPEC-02's `<causing record ID>:<step name>` format and give one key per external step. `open_session` returns `resume_reason` (S06-1:166). SPEC-06-2 step 2 says step 3 branches on it (SPEC-06-2:145–146). AC-0630-1 kills at each step's kill points and asserts one session (S06-1:252). REQ-0630 (S06-1:82) and ADR-58 (Fdn:1969) still say the choice is made "inside the keyed step that opens the session" (E3). |
| D3 | **Closed** | `resume_unavailable` moves to `rule`, not retryable, and the run falls back (S06-1:109). ADR-58 says it is not retryable (Fdn:1969). The error model's rule "workflows map transient errors to retries and everything else to recorded outcomes" (Fdn:1112) fits a checkpointed refusal that the next step reads. Nit: the Rule row's "who sees it / handling" column is ChangeSet-oriented (Fdn:1105), so see E7(c). |
| D4 | **Closed** | ADR-57 now says three things (Fdn:1961): R2's policy delivery, L3 auto-merge and R5's autonomous delivery apply only to subjects unexposed runs made; the style-only rule applies only to unexposed reviewers; kernel-raised escalations are not flagged. The R2 outcome (Fdn:2183), the R5 outcome (Fdn:2186) and the `suggestion` row (Fdn:1375) follow. These agree with ADR-54's rule that an exposed run's subject is `elevated` and its delivery is flagged at every level. The SDLC `escalation` row (Fdn:1374) needs no change under the new sentence. Nit: Fdn:155 and the R2 additions column still list "autonomy L3 and auto-merge" unqualified. That is acceptable as a feature inventory, since the outcome column is qualified. |
| D5 | **Closed; layout table defects remain (E6)** | REQ-0506 covers session directories (SPEC-05:74). The security-test list adds them (SPEC-05:188). AC-0506-1 names `/var/lib/grindstone/sessions/<other agent>/` (SPEC-05:236). The new layout table has root `root:root` 0711, `<agent>/` 0700, and `<agent>/<run>/<session>/` 0700 (SPEC-05:113–117). This is consistent with three things: the entrypoint creates `sessions/<agent>/` with `CHOWN` (SPEC-05:125); the helper creates session directories as the agent user (SPEC-05:111); and FF-05 and FF-06, which are unchanged (SPEC-05:207, :212). |
| D6 | **Closed; bookkeeping gaps remain (E5)** | ADR-57: "A delivery is `elevated` when any of its required checks was performed by an exposed run … (SPEC-28)" (Fdn:1961). ADR-53's Status pointer states it (Fdn:1917). ADR-57's Consequences name ADR-53's routine facts (Fdn:1963). |
| D7 | Closed | Risk tab (Fdn:492) gives the whole lifetime, the credential and the mitigations. The line is added to SPEC-05's risks (SPEC-05:265). ADR-58's Consequences still say "for up to the window" (E7(a)). |
| D8 | Closed | `<agent>/<run>/<session>/` (SPEC-05:111, S06-1:168). The host refuses a `resume` outside the bound user's directories for the run (REQ-0631, S06-1:83; AC-0631-1, S06-1:255). |
| D9 | Closed | (a) Fixture added (SPEC-05:243). (b) AC-0630-2 covers a removed directory and a planted login (S06-1:253). (c) TKT-0606 owns AC-0630-3 and depends on TKT-0605 (SPEC-06-2:218). (d) OQ-0605 says TKT-0605 sets the flag in TKT-0503's paths (S06-1:270). |
| D10 | Closed (one nit) | Comma (Fdn:1442). OQ-0601 (S06-1:269). Toolboxes (Fdn:1326). SPEC-06 map row cites ADR-55 (Fdn:2107). REQ-0617 (S06-1:72). REQ-0515 is in order (SPEC-05:83). ADR-23 is amended with a pointer. The AC-0906-2 wording now reads badly (E7(b)). |

## New findings

**E1 — should fix. The event marker is not defined well enough to implement, and the host cannot reach it as specified.**
- **Where:** REQ-0631 (S06-1:83); disposal bullet (S06-1:168); SPEC-05 layout (SPEC-05:113–117, :125).
- **Problem:**
  - Neither spec says where the marker lives or who owns it.
  - `gs-host` keeps only `CAP_SETUID` and `CAP_SETGID`, with no `DAC_READ_SEARCH` (SPEC-05:125). It therefore cannot list `<agent>/` (0700, agent-owned), touch a file in it, or enumerate directories to sweep, except through the helper as each agent user.
  - Touching a marker through a spawned helper on every event is costly.
  - A marker inside the agent-owned directory can be changed by the agent. A future timestamp keeps its transcript indefinitely; deleting it leaves the age undefined.
  - Nothing says how a directory without a marker is aged, for example after a crash between `mkdir` and the first event.
  - The host ages by emit time, while `stations` updates `last_activity` at intake (S06-1:153), which can lag by the delivery backoff. The two windows can disagree. This fails safe, but it is unstated.
- **Fix:**
  - Keep markers in a host-owned place outside the agent directories, for example `/var/lib/grindstone/sessions/.host/<agent>/<run>/<session>` with `gs-host` 0700, created by the entrypoint. The marker records the directory path and is touched by the host itself.
  - State that the sweep enumerates the marker tree, and removes each matching agent directory through the helper as its user.
  - Age a directory without a marker as expired.
  - State that both `stations` and the host measure from the event's `at`.
  - Extend AC-0631-1: a marker the agent user tries to alter is unreachable to it.

**E2 — should fix (before TKT-0605 starts REQ-0631). A resumed session can still have its directory swept while live.**
- **Where:** REQ-0630 (S06-1:82) says the resumed session runs "in the same configuration directory". REQ-0631 and S06-1:168 key the sweep's exemption and the marker on "the session".
- **Problem:**
  - A resumed session has a new host session ID, but it runs in `<agent>/<run>/<lost session>/`.
  - If liveness and the marker are keyed by session ID, the directory belongs to a session the host no longer holds as live, and its marker stops being touched.
  - After one window, the timer sweep deletes `CLAUDE_CONFIG_DIR` and `HOME` under the running resumed agent. This is D1's failure mode again.
- **Fix:**
  - State that liveness and markers are keyed by configuration directory, not session ID. The host holds a directory as live while any live session uses it, and each event touches the marker of the directory its session uses.
  - Add to AC-0631-1 (or AC-0630-2): a resumed session older than the window keeps its directory through the timer sweep.

**E3 — minor. REQ-0630 and ADR-58 still describe the old single-step choice.**
- **Where:** S06-1:82 says "the choice is made inside the keyed step that opens the session". Fdn:1969 says "The choice … is made inside the keyed step that opens the next session, from facts recorded on the session, so a replay chooses the same".
- **Problem:** this contradicts the three-step design (S06-1:161–164), where the choice is its own checkpointed step with no external effect. It is also the claim D2 showed false under AC-0204-1.
- **Fix:**
  - REQ-0630: "the choice is recorded by a checkpointed step before the session is created; the create and its fallback are separate keyed steps".
  - ADR-58 (still proposed): the same sentence.

**E4 — minor. Where `open_session`'s steps run, and FF-10's registry.**
- **Where:** SPEC-06-2:145 shows `stations.open_session (key <run>:s<k>)` as one keyed call. FF-10's list names one "session create" step (S06-1:220).
- **Problem:**
  - `open_session` is now up to three DBOS steps. If a caller invoked it from inside a step, the inner steps would run as plain functions and not be checkpointed, which defeats D2.
  - The fallback create is a second registered external step, but it is not named in FF-10's list.
- **Fix:**
  - State that `open_session` runs its steps from the calling workflow's body and is never called from inside a step.
  - SPEC-06-2 step 2: "keys `<run>:s<k>` and, after a refused resume, `<run>:s<k>n`".
  - FF-10's list: name "session create" and "session create fallback" as separate registered steps. The choice step, which has no effect, is not registered there.

**E5 — minor. Bookkeeping for ADR-57's new amendments.**
- **Where:** ADR index rows 23 and 53 (Fdn:1476, Fdn:1506); spec map row SPEC-28 (Fdn:2122).
- **Problem:**
  - Row 55 shows "(amended by 57)", but rows 23 and 53 do not, although both Status lines now carry the pointer.
  - ADR-57 names SPEC-28 as owner of the new `elevated` rule, but SPEC-28's row does not cite ADR-57.
- **Fix:**
  - Row 23 becomes "(amended by 52, 57)" and row 53 becomes "(amended by 54, 57)".
  - Add ADR-57 to the SPEC-28 row.
  - Optional: ADR-54's facts (Fdn:2209 area) and the glossary's "Routine delivery" (Fdn:229) still omit the exposure facts from ADR-54 and ADR-57. This predates the commit, but it is now two facts short.

**E6 — minor. The SPEC-05 session layout table and its prose.**
- **Where:** SPEC-05:111, :113–117.
- **Problems:**
  - The last row carries a fifth cell, "Start skills are copied there read-only … M1 capabilities have none." The table breaks and the sentence is lost in rendering.
  - The `<agent>/<run>/` level has no row, so its owner and mode are unstated.
  - The root's "Who writes" cell says "Nobody lists", which answers a different question. Nothing says who sets 0711; a fresh Docker volume root is `root:root` 0755.
  - The prose still says the host "sweeps any older than the window", without the live and marker rule.
- **Fix:**
  - Move the start-skills sentence below the table.
  - Add a row for `…/<agent>/<run>/`: `<agent>:<agent>` 0700, created by the helper as the agent user.
  - Root row: "the agent-host entrypoint sets the mode; no agent user can list it".
  - Prose: "sweeps lost sessions' directories whose last event is older than the window (REQ-0631)".

**E7 — nits.**
- **(a)** ADR-58 Consequences (Fdn:1971): "transcripts at rest for up to the window" should match the risk tab's whole-lifetime statement (Fdn:492).
- **(b)** AC-0906-2 (SPEC-09:297): "gives `sdlc.implementer` the `web` category and `sdlc.test_reviewer` not" → "… and does not give it to `sdlc.test_reviewer`".
- **(c)** Optional: the error model's Rule row (Fdn:1105) could add "or a workflow step, as a recorded outcome", so `resume_unavailable` fits the row's own wording.

**E8 — low. Kernel-raised escalations and ADR-54.**
- **Where:** ADR-57 (Fdn:1961), "an escalation the kernel raises after a run fails is the kernel's decision … exposure does not flag it". ADR-54 (Fdn:1927), "every decision it raises is flagged `untrusted`".
- **Problem:**
  - The reading is sound, but it narrows how ADR-54 is applied, and only holds if the escalation carries no text the exposed run wrote. Under ADR-54 a decision payload with such text exposes whoever answers it, which matters for an R2 orchestrator.
  - The retry itself is exposed by propagation (retries), which is correct but unstated.
- **Fix:** add to ADR-57: "its payload holds only kernel facts (cause code, run, recommendation), never text the run wrote; the retried run is exposed as before". Either list ADR-54 among the records ADR-57 amends, with a Status pointer, or say this is a reading of ADR-54, not a change to it.

## Verdict

**Approve after minor changes.**
- D1 to D6 are answered, and ADR-57's additions are coherent with ADR-53, ADR-54 and the R2, R5 and SDLC rows. The append-only rule is respected.
- E1 and E2 are small text changes. They must land before the operator accepts v4.12 and before TKT-0605 starts its REQ-0631 work, because E2 recreates D1's deletion of a live directory for resumed sessions.
- E3 to E7 are wording and bookkeeping, and can go in the same edit.
- E8 is optional.
- No further independent pass is needed if the changes stay as described.
