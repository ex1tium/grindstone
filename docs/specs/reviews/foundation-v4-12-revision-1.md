# Foundation v4.12 revision 1: answers to confirmation 1

24 October 2026 · By the author of v4.12, answering `foundation-v4-12-confirmation-1.md`. ADR-57 and ADR-58 are still proposed, so their text is revised in place; accepted records only gain status pointers.

| Finding | Change |
| --- | --- |
| D1 | REQ-0631 and the design's disposal bullet: the sweep skips sessions the host holds as live and ages a lost session by an event marker the host touches on each event it emits, not by directory mtime; ADR-58 says the same. AC-0631-1 asserts that a live session's directory survives the timer sweep however old, and that a lost one inside the window survives the start-up sweep. |
| D2 | SPEC-06-1's resume design is three steps: a checkpointed choice with no external effect, a create under `<run>:s<k>` (with `resume` only if chosen; the no-resume path uses the same key), and a fallback create under `<run>:s<k>n` only after a recorded refusal. `open_session` returns `resume_reason`, and SPEC-06-2's step 3 branches on it. AC-0630-1 kills at each step's kill points and asserts one session. |
| D3 | `resume_unavailable` moves to class `rule`, not retryable; the run falls back. ADR-58 says it is not retryable. |
| D4 | ADR-57: R2's policy delivery, L3 auto-merge and R5's autonomous delivery apply only to subjects unexposed runs made; the style-only `suggestion` rule applies only to unexposed reviewers; an escalation the kernel raises after a run fails is the kernel's, so exposure does not flag it. The R2 outcome, the R5 outcome and the `suggestion` row follow. |
| D5 | SPEC-05: REQ-0506, AC-0506-1 and the security tests cover other agents' session directories; a layout table gives the volume root (`root:root` 0711), `<agent>/` and `<agent>/<run>/<session>/` (0700, the agent user). |
| D6 | ADR-57: a delivery is `elevated` when any required check was performed by an exposed run (SPEC-28). ADR-57 now amends ADR-53, which gains a status pointer. |
| D7 | The residual-risk line states transcripts' whole lifetime, that they can hold the model credential, and the mitigations; SPEC-05's "Risks added" gains the line. |
| D8 | Session directories are `<agent>/<run>/<session>/`, so a restarted host finds a run's directories; the host refuses a `resume` naming a directory outside the bound user's directories for the run (REQ-0631, AC-0631-1). |
| D9 | (a) AC-0510-1 gains the `sessions`-under-a-workspace fixture. (b) AC-0630-2 covers a removed directory and a planted login, each refused before any prompt. (c) TKT-0606 owns AC-0630-3, implementing REQ-0630 and depending on TKT-0605. (d) OQ-0605: TKT-0605 sets the Claude preset's `supports_resume`, a change to TKT-0503's paths named in its pull request. |
| D10 | All applied: the comma, OQ-0601's wording, the Toolboxes line ("from M3, if the project adds `web`"), ADR-55 in the SPEC-06 map row, REQ-0617 names the optional `resume`, REQ-0515 in numeric order, "not" in AC-0906-2. ADR-57 also amends ADR-23, which gains a status pointer. |

FF-13 reports no violations. The reviewer asked for a short re-check of D1 to D6 before the operator accepts v4.12.
