# Foundation v4.11 revision 1: answers to review 1

24 October 2026 · By the author of v4.11, answering `foundation-v4-11-review-1.md` with the operator's two decisions. The result is foundation v4.12, proposed: ADR-57 and ADR-58 amend ADR-55 and ADR-56, because accepted records are never edited.

## The operator's decisions

- **BL1:** persist session directories on a volume only the agent host mounts, swept after the resume window, with resume best-effort per preset. Withdrawing resume from M1 was declined.
- **SF1:** the implementer keeps `web` at every milestone, and the targets it touches are restated as a scope change. The reviewer's option (a), decide per project at M3, and making `web` off by default from M3 were declined.

## Findings and changes

| Finding | Change |
| --- | --- |
| BL1 | ADR-58. Foundation volume table gains `sessions` (`agent-host` only). SPEC-05: the session area moves to the `sessions` volume; ADR-01's link names five volumes; FF-05 refuses `sessions` in any other service and FF-06 refuses it at or under a workspace path; AC-0501-1 gains a fixture. Transcripts at rest are added to the accepted residual risks. |
| BL2 | SPEC-06-1: REQ-0630 rewritten (preset support, recorded agent session ID and directory, choice inside the keyed step, fallback key) and REQ-0631 added (disposal and sweep); `resume` on `POST /v1/sessions`; `session.started` carries the agent's session ID and directory; transient code `resume_unavailable` defined as a refusal before any prompt, including the credential self-test's refusal (N7); `sessions` gains `agent_session_id`, `config_dir` and `resume_reason`, which part 2 shows on the timeline; `open_session` takes `continue_from`; keys `<run>:s<k>` and `<run>:s<k>n`; replayed history is not re-emitted; `[host].resume_window` declared; a design paragraph covers all of it. The reviewer proposed adding `resume` to `SessionOptions` as well; it stays on the create call only, because it describes this call, not the agent's settings. |
| SF1 | ADR-57. M5-01, the SDLC L2 rule for learnings, the Decision-load measure and both statements of R2's scope are restated for exposed work; ADR-57 states that reviewers of a web-holding implementer's subject are exposed by propagation. |
| SF2 | ADR-57: from M3 (SPEC-17) a project may add or remove `web` as a bounded override, exposure read from the effective capability; the Concepts tab's override list says so. SPEC-03's M1 override list is unchanged. SPEC-09 points the reviewer's grant to SPEC-17. |
| SF3 | System context gains the web and rewords "Nothing else is contacted"; the container table gives `agent-host` open egress and `runner` no network; the station `network` values gain `open`; SPEC-05's `agent-egress` line follows. |
| SF4 | SPEC-05: REQ-0515 and AC-0515-1 (the Claude preset maps `web` to allowed search and fetch and denies both without it; TKT-0503). SPEC-09: REQ-0906 states which capability holds `web`, and AC-0906-2 tests the manifest. These sit with the preset and the manifest that own them, not under REQ-0626 as the reviewer proposed. |
| SF5 | SPEC-06-1: `supports_resume` per preset; the scripted preset gains a load marker; proof split into AC-0630-1 (crash-and-resume, fake host, TKT-0602), AC-0630-2 (scripted agent, TKT-0604) and AC-0630-3 (live run at the M1 close, if OQ-0605 finds the Claude preset can resume); OQ-0605 opened, resolved by TKT-0605's first step, default unsupported; a risk line names ADR-42; AC-0631-1 covers disposal. |
| SF6 | SPEC-06-2: REQ-0613 and the `host_lost` row say a refused resume and its fallback are one continuation, not a loss; turn step 3 defines the full prompt for a new session and a continuation notice for a resumed one; AC-0613-1 asserts at most one retry across resume, refusal and new session. |
| SF7 | ADR-58 restates the window as a cost-and-staleness choice, not cache warmth, and records what October 2026 reporting says (one hour on a subscription within plan usage, five minutes otherwise), noting that no primary documentation confirms it. OQ-0601's text follows. |
| SF8 | Records count (fifty-eight) and dates; ADR-55 to ADR-58 cited in the spec map rows of SPEC-05, SPEC-06, SPEC-09 and SPEC-17; I-07's verification adds capabilities holding `web` at M3; foundation links added to SPEC-05, both SPEC-06 parts and SPEC-09; status lines of all four specs carry the amendment. |
| N1 | ADR-57: T1 egress restriction is committed to no release; R3's profiles are T2 only. SPEC-05's scope line follows. |
| N2 | QS-05, the failure-model row, the retry table and runs and sessions say "the resume window (seed one hour)". |
| N3 | Runs and sessions reworded ("a later session … continues the same workspace"). |
| N4 | QS-07 names a web page an agent reads. |
| N5 | No change needed. |
| N6 | ADR-58's consequences ask SPEC-17 to state it. |
| N7 | Folded into BL2: the credential self-test's refusal is a `resume_unavailable`. |

`make check`'s traceability step (FF-13) reports no violations. A confirmation pass by a session that wrote none of this comes next; then the operator accepts v4.12 or sends it back.
