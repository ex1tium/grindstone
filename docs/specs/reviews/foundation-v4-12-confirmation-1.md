# Foundation v4.12 confirmation 1: answers to review 1 of v4.11

24 October 2026 · Independent confirmation review. The reviewer wrote none of the material under review.

## Scope

- Branch `docs/foundation-v4-12` at `8a8ff71` (PR #18): `git diff origin/main...origin/docs/foundation-v4-12`, leaving out the backlog state lines and `.gitignore`.
- Files: `docs/foundation/grindstone-foundation.md` (v4.12, ADR-57 and ADR-58), `SPEC-05`, `SPEC-06-1`, `SPEC-06-2`, `SPEC-09`, `docs/m0/status.md`, `docs/specs/reviews/foundation-v4-11-revision-1.md`.
- Checked against `foundation-v4-11-review-1.md` (BL1, BL2, SF1–SF8, N1–N7), the rest of the foundation, SPEC-02's external-step rule (REQ-0204, AC-0204-1) and `docs/m1/backlog.md`.
- The operator's two choices are taken as given and not reopened: BL1 → an agent-host-only `sessions` volume (ADR-58); SF1 → the implementer keeps `web` permanently, with the affected targets restated (ADR-57).
- `uv run python -m scripts.ff.traceability` reports **FF-13: 0 violations**.
- Line numbers refer to the files at `8a8ff71`. "Fdn" means the foundation file.

## Append-only rule and bookkeeping

- **ADR-55 and ADR-56:** only their Status lines changed, each gaining an "Amended by ADR-57/58 (proposed)" pointer (Fdn:1943, Fdn:1951). Their Decision, Why and Rejected text is unchanged.
- **ADR index:** rows 55 and 56 are marked "(amended by 57/58)", and rows 57 and 58 are added (Fdn:1508–1511).
- **Records count:** "Fifty-eight", and ADR-57 and ADR-58 are stated as Proposed (Fdn:1442). One comma is missing (D10).
- **Revision history:** row 4.12 is added (Fdn:2378).
- **Spec map:** rows SPEC-05, SPEC-06, SPEC-09 and SPEC-17 now cite the new records (Fdn:2106–2120).
- **Status lines:** all four specs carry the v4.12 amendment.
- **status.md:** updated.

## Findings of review 1

| Finding | Status | Evidence |
| --- | --- | --- |
| BL1 | **Closed** | ADR-58 (Fdn:1965–1971). Volume table row `sessions`, `agent-host` only (Fdn:354). SPEC-05:111 moves the session area to `/var/lib/grindstone/sessions`, and the entrypoint creates the per-agent directories (SPEC-05:119). FF-05 refuses `sessions` in any other service (SPEC-05:201), FF-06 refuses it under a workspace (SPEC-05:206), and AC-0501-1 has a fixture (SPEC-05:224). The residual risk is added (Fdn:492). Remaining gaps: D5, D7, and the test gap in D9. |
| BL2 | **Partly closed** | Done: REQ-0630 rewritten and REQ-0631 added (SPEC-06-1:82–83); a "Resume after a host loss" paragraph (:159–164); `resume` on `POST /v1/sessions` (:137); keys `<run>:s<k>` / `<run>:s<k>n` (:143); `session.started` carries the agent session ID and directory (:147); `resume_unavailable` defined (:107); `sessions` gains `agent_session_id`, `config_dir`, `resume_reason` (:195); `open_session(continue_from)` (:201); `[host].resume_window` (:203); replayed history is not re-emitted (:163); ownership is right (stations records the reason, work shows it, SPEC-06-2:145). **Still open:** the replay determinism the paragraph claims does not hold under SPEC-02's step rule (D2); the error class contradicts the fallback (D3); the sweep can delete live sessions' directories (D1); after a restart the host cannot tell which directories belong to a run (D8). |
| SF1 | **Partly closed** | Restated: ADR-57 (Fdn:1957–1963), M5-01 (Fdn:2056), the L2 learnings row (Fdn:1372), Decision load (Fdn:172), and both R2 scope statements (Fdn:155, Fdn:2183). These agree with ADR-53 as amended by ADR-54 (Fdn:1917, "a subject an exposed run made is never routine"). The propagation to reviewers is stated (Fdn:1961). **Not restated:** the `suggestion` row (Fdn:1375); the R2 outcome and L3/auto-merge, and R5's autonomous builds, which also cannot deliver an exposed implementer's work without a person (D4). |
| SF2 | **Closed** (one nit) | The Concepts override list gains `web` from M3 (Fdn:626). SPEC-09:162 points to SPEC-17. ADR-57 names SPEC-17 as owner. SPEC-03's M1 list is unchanged, which is correct. Nit: the SDLC Toolboxes line still says "web tools only if the project grants them" without "from M3" (Fdn:1326; D10). |
| SF3 | **Closed** | System-context caption and new "The web" row (Fdn:323, Fdn:331). Registries row and "Nothing else is contacted on purpose" (Fdn:330, Fdn:333). `agent-host` "any host" and `runner` "Nothing" (Fdn:344–345). Station `network` gains `open` (Fdn:642). SPEC-05:168. No other "registries only" statement remains. |
| SF4 | **Closed** | REQ-0515 and AC-0515-1 `test_web_category_mapping` (SPEC-05:78, :233), assigned to TKT-0503. REQ-0906 and AC-0906-2 (SPEC-09:75, :297). Placing them with the preset and the manifest is sound. |
| SF5 | **Mostly closed** | `supports_resume` per preset and the scripted load marker (SPEC-06-1:176, :183). The proof is split into AC-0630-1 (crash-and-resume, fake host), AC-0630-2 (scripted agent) and AC-0630-3 (live run) (:248–250). OQ-0605 is opened with default "unsupported" (:266). A risk line names ADR-42 (:270). AC-0631-1 covers disposal (:251). Ticket split: TKT-0602 / 0604 / 0605 (:230–232). **Remaining:** AC-0630-3 has no owning ticket, and nothing says who sets the Claude preset's flag (D9). |
| SF6 | **Closed** | REQ-0613 (SPEC-06-2:80) and the `host_lost` row (:168) say a refused resume is not a loss. Step 3 defines both prompts (:146). AC-0613-1 asserts at most one retry (:233). Part 2 still needs the resume outcome returned to it (D2). |
| SF7 | **Closed** (wording nit) | ADR-58 restates the window as a cost-and-staleness choice and marks the cache claim as unconfirmed by primary documentation (Fdn:1969). OQ-0601 still opens with "while the prompt cache is warm" before contradicting it (SPEC-06-1:265; D10). |
| SF8 | **Closed** (nits) | Count and dates (Fdn:1442). Spec map (Fdn:2106–2120). I-07 verification (Fdn:405). Foundation links in all four specs. Status lines. Nits: a missing comma; the SPEC-06 map row does not cite ADR-55 although SPEC-06-1 implements `web` (D10). |
| N1 | Closed | ADR-57 (Fdn:1961); SPEC-05:38. |
| N2 | Closed | Fdn:269, Fdn:501, Fdn:696, Fdn:705. |
| N3 | Closed | Fdn:696. |
| N4 | Closed | Fdn:271. |
| N5 | Closed (no change needed) | Still holds: REQ-0623 and DEC-0606 keep the user, and REQ-0629 is untouched. |
| N6 | Closed | ADR-58's consequences (Fdn:1971). |
| N7 | Closed in the design; not tested | SPEC-06-1:161 and ADR-58 count the self-test refusal as `resume_unavailable`. No real-host test covers it (D9). |

## New findings

**D1 — blocking. The timer sweep deletes the configuration directories of live sessions.**
- **Where:** SPEC-06-1:83 (REQ-0631), :164 (step 5), :251 (AC-0631-1); ADR-58 (Fdn:1969); SPEC-05:111.
- **Problem:** every quarter window, the host removes "every directory last written longer ago than the window", and nothing exempts sessions that are still live.
  - A directory's mtime changes only when entries directly inside it change. Claude Code writes its transcript in nested files, so any session older than the window soon qualifies.
  - A quiet session also qualifies, for example one running a long test command with no transcript write.
  - Either way, `CLAUDE_CONFIG_DIR` and `HOME` are deleted under a running agent.
  - The same mtime rule can remove a lost session's directory at host start even though `stations` judges it inside the window, because it measures from the last host event. That case falls back safely, but resume then fails needlessly for every session older than the window.
- **Fix:**
  - The sweep skips every directory the host holds as a live session.
  - Age is the newest mtime in the directory tree, or a marker file the host touches on each event it emits for the session.
  - Extend AC-0631-1: a live session older than the window survives the timer sweep, and a lost session younger than the window by its last event survives the start-up sweep.

**D2 — should fix. The resume choice is not deterministic under SPEC-02's step rule, and the step mixes two effects.**
- **Where:** SPEC-06-1:160–162, :248 (AC-0630-1); SPEC-02 AC-0204-1; SPEC-06-2:145–146.
- **Problem:**
  - An external step killed after its effect and before its checkpoint runs again (AC-0204-1). So "reading the clock once inside the step so a replay decides the same" is false: the re-run reads the clock again.
  - Example: the first run resumes under `<run>:s<k>`, then the re-run, past the window, decides "new". The spec never says which key the no-resume path uses.
    - If it uses `<run>:s<k>`, the host returns the resumed session but `resume_reason` says `window_passed`, and the full prompt goes into a resumed context.
    - If it uses `<run>:s<k>n`, a second live session opens on the same user and workspace, against REQ-0609.
  - If a resume refusal is not checkpointed, a re-run may retry the resume, have it succeed, and leave two sessions.
  - One registered step with two keys also does not fit SPEC-02's registry (one key and kill points per step).
  - Part 2 needs to know whether the session resumed in order to pick its prompt (SPEC-06-2:146). Nothing returns that to it.
- **Fix:** split the work into three steps.
  - (a) A choice step with no external effect. It reads the clock and the lost session's record and checkpoints the choice and reason.
  - (b) A create step under `<run>:s<k>`, with `resume` only if the recorded choice was to resume. Its checkpointed output is the session or the typed refusal.
  - (c) Only after a recorded refusal, a create step under `<run>:s<k>n`.
  - State that the no-resume path uses `<run>:s<k>`.
  - `open_session` returns `resume_reason`, and part 2's step 3 branches on it.
  - AC-0630-1 kills at each step's kill points.

**D3 — should fix. `resume_unavailable` is classed `transient`, but transient errors are retried.**
- **Where:** SPEC-06-1:107; Fdn:1109 (transient: "Retried with backoff by the step's policy"); SPEC-01 `ErrorEnvelope.retryable`.
- **Problem:** the design wants an immediate fallback to a new session. Under the documented class handling, the workflow would retry the resume with backoff, possibly until the window passes.
- **Fix:** make it a non-retryable refusal (`retryable: false`, class `limit` or `rule`) that the step handles by falling back. Or state explicitly that this code's step policy is "fall back, never retry".

**D4 — should fix. Targets that still assume policy can act on an exposed implementer's work.**
- **Where:**
  - the `suggestion` row (Fdn:1375);
  - the R2 outcome "verified pull requests can merge without a person" and "autonomy L3 and auto-merge" (Fdn:2183, Fdn:155);
  - R5's autonomous builds (Fdn:2186);
  - the `escalation` row (Fdn:1374).
- **Problem:**
  - Under ADR-54, an exposed run's subject is `elevated` and its delivery decision is flagged `untrusted`, waiting "at every autonomy level and in every charter mode" (Fdn:1927).
  - So with SDLC's defaults, L3 auto-merge and Autonomous-mode delivery never apply to implementer pull requests, not just R2's routine policy delivery, which is the only one ADR-57 restates.
  - Reviewers of implementer subjects are exposed, so their suggestions are flagged, and the shipped rule "dismiss style-only suggestions" never fires on them.
  - Whether an escalation the kernel raises after an exposed run fails counts as "raised by" that run is unstated. If it does, "retry once" never fires for implementers either.
- **Fix:**
  - Add a sentence to ADR-57's decision and consequences.
  - Qualify the R2 outcome and the R5 row with "for projects whose implementer does not hold `web` (ADR-57)".
  - `suggestion` row: "dismiss style-only suggestions from unexposed reviewers; flagged suggestions go to a person".
  - State that kernel-raised escalations are not flagged by exposure, or restate that row too.

**D5 — should fix. Isolation between agent users on the `sessions` volume is neither required nor tested.**
- **Where:** SPEC-05:74 (REQ-0506), :111, :183 (security tests), :230 (AC-0506-1).
- **Problem:**
  - REQ-0506 and AC-0506-1 cover `workspaces` only.
  - The security test's "other agents' subtrees" does not clearly include `sessions/<other agent>/`.
  - Transcripts of other runs now persist on disk.
  - The mode and owner of the volume root are unstated, while the `workspaces` layout states its own.
- **Fix:**
  - REQ-0506 adds "or another agent user's session directories".
  - The security test list and AC-0506-1 add `/var/lib/grindstone/sessions/<other agent>/`.
  - Add a layout row for the volume root (for example `root:root` 0711) and for `<agent>/` (`<agent>:<agent>` 0700).

**D6 — should fix. The new `web` override lets an exposed reviewer's verdict feed a routine delivery.**
- **Where:** ADR-57 (Fdn:1961), ADR-53's routine rule (Fdn:1919), ADR-55's Why (Fdn:1947).
- **Problem:**
  - ADR-57 lets a project add `web` to a reviewer, and remove it from the implementer.
  - ADR-53's routine facts check only that "no run that made the change was exposed".
  - So a passing verdict from a reviewer steered by a page counts toward a routine, policy-deliverable change from R2. That is exactly the danger ADR-55 gives for keeping reviewers off the web.
- **Fix:** in ADR-57, or as a stated duty of SPEC-28: a delivery is `elevated` when any required check was performed by an exposed run.

**D7 — note. The residual-risk line on transcripts at rest is understated.**
- **Where:** Fdn:492; SPEC-05:258–261.
- **Problem:**
  - Transcripts are on disk for every live session's whole life, not only "up to the resume window".
  - After a loss they stay until the sweep (window plus up to a quarter) or the run's discard.
  - They can hold the model credential. ADR-58 says so (Fdn:1971), but the risk tab does not.
  - No mitigation is listed, and SPEC-05's "Risks added" lacks the line.
- **Fix:** restate the line with this content and its mitigations (agent-host-only volume, 0700 per agent user, disposal and sweep), and add it to SPEC-05 §9.

**D8 — note. A restarted host cannot find a run's session directories, and `config_dir` is not validated.**
- **Where:** SPEC-06-1:83, :164; SPEC-05:111 (`<agent>/<session>/`).
- **Problem:**
  - `DELETE /v1/workspaces/<run>` must remove "a run's directories".
  - Session directories are named by host session UUID, and a restarted host remembers nothing.
  - The `resume.config_dir` it is given is also not checked against the bound user.
- **Fix:**
  - Either name the directories `<agent>/<run>/<session>/`, or state that discard removes all of the bound user's session directories (exact under DEC-0606).
  - The host refuses a `config_dir` outside `sessions/<bound user>/`.

**D9 — note. Test and ownership gaps.**
- **(a)** AC-0510-1 (SPEC-05:237) has no fixture for the new FF-06 clause (`sessions` under a workspace path).
- **(b)** No real-host test covers the refusal paths. Add to AC-0630-2: with the directory removed, and with a login planted in it, the host fails `resume_unavailable` before any prompt (this also tests N7).
- **(c)** AC-0630-3 has no owning ticket. TKT-0605 does not depend on TKT-0503. Name TKT-0606 (add REQ-0630, the live run) as its owner.
- **(d)** OQ-0605 is resolved in TKT-0605, but the Claude preset's `supports_resume` lives in TKT-0503's paths. Say which ticket sets it.

**D10 — note. Wording.**
- Fdn:1442: add a comma after "ADR-47 (19 October 2026)".
- SPEC-06-1:265: drop "while the prompt cache is warm" from OQ-0601's resolution.
- Fdn:1326: "web tools only if the project grants them" → "from M3, if the project adds `web` (SPEC-17, ADR-57)".
- Fdn:2107: the SPEC-06 map row should also cite ADR-55.
- SPEC-06-1:72: REQ-0617 could say `create_session` takes an optional `resume`.
- SPEC-05:78, :233: REQ-0515 and AC-0515-1 sit out of numeric order.
- SPEC-09:297: "none" → "not".
- Optional: ADR-57 could list ADR-23 among the records it amends, following ADR-52's precedent for override changes.

## Verdict

**Changes required, all small and local.**
- **ADR-57:** consistent with ADR-53 and ADR-54 once D4 and D6 are added.
- **ADR-58 and SPEC-05:** carry out the operator's BL1 choice soundly.
- **SPEC-06-1's resume design:** needs D1 (the sweep must spare live sessions) and D2 and D3 (a recorded choice step, non-retryable refusal, explicit keys, the reason returned to part 2) before TKT-0602 or TKT-0605 start their REQ-0630 or REQ-0631 work.
- **D5:** should go in the same pull request.
- **D7 to D10:** minor edits.

A short re-check of D1 to D6 is enough before the operator accepts v4.12.
