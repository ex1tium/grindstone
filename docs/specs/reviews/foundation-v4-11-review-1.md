# Foundation v4.11 review 1: ADR-55, ADR-56 and the M1 spec amendments

24 October 2026 · Independent specification review (the reviewer wrote none of the change)

## Scope

- Commits `eef0262` (PR #13, v4.11 proposed) and `0ae62c4` (PR #14, accepted by the operator).
- `docs/foundation/grindstone-foundation.md`: ADR-55 and ADR-56, with the edits to QS-05, the threat model, residual risks, the failure model, runs and sessions, the retry table, SDLC toolboxes, the ADR index, the risks table and the revision history.
- `docs/specs/SPEC-05-deployment-users-secrets.md`, `SPEC-06-1-stations-agent-host.md`, `SPEC-06-2-task-runs.md` and `SPEC-09-sdlc-skeleton-factory.md`.
- Checked against the Planning playbook validation checklist, the rest of the foundation, the M1 specs, `docs/spikes/SPK-1-host-claude-vscode.md` and `docs/m1/backlog.md`.
- FF-13 (`python -m scripts.ff.traceability`) reports 0 violations, so every cited ID resolves.
- Process note: the amendments were accepted the same day without an independent review (CLAUDE.md, playbook step 2). This record is that review, done after the fact.

Line numbers refer to the files at commit `0ae62c4`.

## Findings

### Blocking

**BL1. The resume that REQ-0630 asks for cannot work in M1: the session configuration directory does not survive a host restart.**
- Where: SPEC-06-1:80 (REQ-0630), SPEC-06-1:237 (AC-0630-1), ADR-56 (foundation:1949), against SPEC-05:109, SPEC-05:74 (REQ-0507), SPEC-05:120 and DEC-0503 (SPEC-05:209).
- Problem: SPEC-05 puts the session configuration area, which is each session's `CLAUDE_CONFIG_DIR` and holds Claude Code's transcript, on a tmpfs at `/run/gs-sessions`.
  - REQ-0507 and DEC-0503 make the container stop whenever the host exits (Docker's init is PID 1, with the host as its only child).
  - So every host restart is a container restart, and the tmpfs is wiped with it. The entrypoint then recreates `/run/gs-sessions/<agent>/` empty.
  - Nothing is left to resume. REQ-0630's resume path is therefore unreachable, and AC-0630-1 can never pass its resume branch.
  - ADR-56's statement that "the host keeps a lost session's configuration directory" is false for the deployment SPEC-05 specifies.
- Fix: SPEC-05 should move the session configuration area onto a named volume that only `agent-host` mounts (mode 0700 per agent user, still outside `workspaces`, so REQ-0510 and FF-06 still hold).
  - Extend FF-05 and FF-06 to allow that one volume and to forbid it anywhere else.
  - Add an accepted-risk note: transcripts, which may contain the agent-readable model token, now persist at rest until they are swept.
  - Alternatively, if a volume is unwanted, ADR-56 needs a new amending record saying native resume is unavailable in M1 under DEC-0503, and REQ-0630 and AC-0630-1 are withdrawn.

**BL2. REQ-0630 has no design. The control API, contracts, keys, records and disposal are all unstated.**
- Where: SPEC-06-1:70 (REQ-0617), :88 (`SessionOptions`), :129–140 (host client table), :154 (reconciliation), :184 (`sessions` table), :190 (interfaces), :192 (configuration). Also SPEC-06-2:144 (turn step 2). No design paragraph covers REQ-0630. This fails checklist items 1, 7, 8, 9 and 15.
- Problems:
  1. **No resume operation or option.**
     - REQ-0617's operation list and `POST /v1/sessions` are unchanged.
     - Nothing says how `stations` asks for a resume: no `resume` field, and no agent-native session ID to load.
     - The `sessions` table records neither Claude Code's own session ID nor the configuration directory's name. The host names that directory per host session UUID (SPEC-05:109) and remembers nothing after a restart (SPEC-06-1:140).
  2. **No idempotency keys.**
     - REQ-0609 derives keys from the run and turn, and part 2 uses `<run>:s<k>`.
     - A failed resume followed by a fallback new session needs two distinct keys. Otherwise replaying the key returns the failed attempt, or the fallback is refused.
  3. **Replay is not deterministic.** The "younger than the window" test reads the wall clock. Unless the choice is recorded inside a step, DBOS replay can choose differently (FF-10, checklist 8).
  4. **Disposal has no owner.**
     - "The host keeps … until the window passes, then disposes" cannot be done by a host that remembers nothing after it restarts.
     - Nothing disposes the kept directory when the run is cancelled, fails, or retries with a fresh run inside the window. `discard_workspace` (SPEC-06-1:125) does not mention it.
  5. **"Resume fails" is undefined.** It could mean a refusal of the create call, an ACP load error, or an `error` event after the session starts. ADR-56 says a failed resume "is not a second loss", but only a precise definition keeps that boundary testable.
  6. **Replayed history is unhandled.** An ACP session load replays history as updates. Nothing says whether the host re-emits it as `tool.call` events, which would duplicate the run's transcript.
  7. **"The run records" crosses ownership.** Runs belong to `work` (part 2), and `stations` cannot write them (checklist 7).
  8. **No configuration key.** The resume window is in no configuration section; SPEC-06-1:192 lists only `[host].transcript_truncate`.
- Fix: add a design paragraph and contracts to SPEC-06-1. The simplest form:
  - Record `agent_session_id` and `config_dir` on `stations.sessions`, taken from a `session.started` payload field.
  - Add an optional `resume: {agent_session_id, config_dir}` to the `POST /v1/sessions` body and `SessionOptions` (additive, same protocol version), and state in REQ-0617 that `create_session` takes it.
  - Give `stations.open_session` a `continue_from` parameter. Make the resume-or-new choice inside the keyed external step, with keys `<run>:s<k>` for the attempt and `<run>:s<k>n` for the fallback.
  - Define resume failure as a typed refusal of the create call before any prompt, with a new transient error `resume_unavailable`.
  - Record a reason on the session (`resumed`, `window_passed`, `resume_failed`, `unsupported`), which part 2 shows on the run timeline.
  - Dispose of kept directories in `discard_workspace`, and sweep at host start and on a timer any directory whose mtime is older than the window.
  - Declare `[host].resume_window` (seed 60 min).
  - Do not re-emit replayed history as events.
  - Add a crash-and-resume AC for the step.

### Should fix

**SF1. ADR-55's default (implementer always exposed from M3) quietly cuts across an M5 exit criterion, the shipped L2 rules and a success measure, yet the record says exit criteria are unchanged.**
- Where: ADR-55 (foundation:1941–1943); revision history 4.11 (foundation:2358); M5-01 (foundation:2036); foundation:761 ("an implementer proposes a learning"); the SDLC L2 rules (foundation:1370 and the `suggestion` row); Decision load (foundation:172); ADR-54's propagation bullet (foundation:1929).
- Problem:
  - Under ADR-54, every item an exposed run proposes is `untrusted`, and `untrusted` is class `never`.
  - From M3, the SDLC implementer holds `web` by default, so every learning and finding it proposes is `untrusted`. M5-01 ("At L1 a learning that meets the tag rule is accepted by policy") and the shipped rule "approve learnings only" can then never fire on implementer learnings under the defaults.
  - ADR-54 also propagates exposure to "the reviewers of that subject". So from M3 the test, code and security reviewers of every implementer subject are exposed too, even without `web`. Their suggestions are flagged and their reports are withheld from unexposed runs.
  - ADR-55 mentions only R2 routine delivery as a consequence. The "Decision load … falling once L2 is available" target and M5-07 at L2 are weakened in ways the record never states.
  - The playbook treats a change to success measures as a scope change ("Changing the foundation").
- Fix: add a new amending record (append-only) or a stated M2-review item that picks one of these:
  - (a) The implementer's `web` default holds through M2, and SPEC-17 makes it a per-project choice with an explicit default.
  - (b) Keep the default and restate M5-01's source of learnings, the SDLC L2 table and the Decision-load target as a flagged scope change.
  - Either way, add to ADR-55's consequences that from M3 the reviewers of a web-holding implementer's subject are exposed by propagation.

**SF2. "A project may grant `web` to reviewers by configuration" has no mechanism.**
- Where: ADR-55 (foundation:1941), SPEC-09:161, against foundation:624 ("Where capabilities come from"), SPEC-03:94 and SPEC-03:157.
- Problem: project overrides are limited to model, effort, limits, extra skills and extra prompt. Permissions are not overridable, so the grant ADR-55 and SPEC-09 promise contradicts the Concepts tab and SPEC-03.
- Fix: either name the owner and milestone (for example, "from SPEC-17, a project may add `web` to a capability's `permissions.allow`; exposure is read from the effective capability, whose hash it changes") and update foundation:624 and SPEC-03's override list in the same edit, or drop the clause from ADR-55 and SPEC-09 until then.

**SF3. Architecture tabs still say agents reach only model providers and registries.**
- Where (foundation):
  - :323 (system-context caption);
  - :330–332 (the registries row and "Nothing else is contacted");
  - :343 (`agent-host` can reach "model providers; package registries");
  - :344 (`runner` reaches "Package registries only", which already contradicts DEC-0505 and ADR-55's "the runner keeps no network");
  - :640 (station `network` is `none`, `registries` or an allow-list, with no value for open egress).
- Also: SPEC-05:166 (`agent-egress` "to model providers and package registries").
- Problem: these tabs state the decision ADR-55 changes and were not updated ("update every tab that states the decision").
- Fix:
  - Add a system-context row: "The web | searches and page reads out, pages in | Both | None | Untrusted; reached from the agent station (open egress at T1, ADR-55)". Reword "Nothing else is contacted".
  - Set `agent-host` to "any host (open egress at T1, ADR-55)" and `runner` to "Nothing (no network)".
  - Add `open` to the station `network` values as the T1 agent-station default.
  - SPEC-05:166 becomes "`agent-egress` carries `agent-host`, with open egress (ADR-55)".

**SF4. No acceptance criterion proves the `web` mapping or its absence.**
- Where: SPEC-06-1:78 (REQ-0626) and AC-0626-1 (:235); SPEC-05:152; SPEC-09:161.
- Problem: ADR-55's safety argument rests on "reviewers without web tools by default", and no test shows it.
  - AC-0626-1 checks only the grep and the tool timeout.
  - Nothing shows that the Claude preset turns `web` into allow rules for its search and fetch tools, or that a capability without `web` (the test reviewer) has those tools denied rather than left to a permission prompt.
- Fix: extend AC-0626-1, or add AC-0626-2 (contract, `test_web_category_mapping`): with `web`, the preset's tool rules allow search and fetch; without it, both are denied in the security-floor list. Add a SPEC-09 manifest test that `sdlc.test_reviewer` lacks `web`.

**SF5. Ticket assignment and test method for AC-0630-1 are wrong, and a missing adapter capability is not planned for.**
- Where: SPEC-06-1:219, :221, :237, :242; docs/m1/backlog.md:66 and :90; SPK-1:126.
- Problems:
  - AC-0630-1 needs the real host (TKT-0605) and the Claude preset (TKT-0503, SPEC-05). TKT-0602 also implements REQ-0630 but depends on neither, and sits in an earlier backlog layer.
  - The AC needs a real model credential, so it is a live run (checklist 16) and cannot be a CI integration test.
  - REQ-0630 drops ADR-56's condition "where its adapter supports it". The scripted preset (TKT-0604, REQ-0620), which CI forces for every capability, has no resume.
  - SPK-1 never tested resume. `claude-agent-acp` accepts session load and resume (SPEC-05:150, AC-0508-1), but whether `@ahpd/agent-acp` 0.12.0 and `createHost` expose a way to load a session is unknown.
  - If they do not, the work either collides with ADR-42 ("packages unmodified") or leaves an AC that cannot close.
- Fix:
  - Split the AC into three:
    - AC-0630-1 (integration, fake host, TKT-0602): the choice, keys, reasons and disposal.
    - AC-0630-2 (scripted agent, TKT-0604): the scripted preset gains a `load` that reads a marker from its configuration directory.
    - AC-0630-3 (live run, with TKT-0606 or a new ticket depending on TKT-0605 and TKT-0503): Claude resumes. The observable is that the agent recalls a token given only in the lost turn's prompt and never written to the workspace.
  - Add a preset flag `supports_resume`; REQ-0630 applies only when it is true.
  - Add an open item with default "unsupported → new session" and resolver "TKT-0605's first step", plus a risk line naming ADR-42.

**SF6. SPEC-06-2's retry and prompt rules are not settled for resume.**
- Where: SPEC-06-2:79 (REQ-0613), :144 (turn step 2–3), :167 (`host_lost` row), AC-0613-1 (:232).
- Problems:
  - REQ-0613 does count a resume as the "continues once", which is good. But it does not carry ADR-56's "a resume that fails falls back to a new session … and is not a second loss", and the table's "a second loss fails the run" reads as if a failed resume might count.
  - Nothing says what turn `k+1` is prompted with. A new session needs the full initial prompt. A resumed session should get a short continuation notice ("your previous turn was interrupted by a host restart; continue and end with `report`"), not the whole pack again.
  - AC-0613-1 does not distinguish the two branches.
- Fix:
  - Add to REQ-0613 and the table: "a refused resume is not a loss; the fallback new session is the same continuation".
  - Define both prompts in the turn workflow.
  - Extend AC-0613-1 to assert one retry at most across resume → refused → new session.

**SF7. ADR-56's rationale rests on an uncited fact.**
- Where: ADR-56 Why (foundation:1951); OQ-0601 (SPEC-06-1:250, "while the prompt cache is warm"); status.md.
- Problem: the one-hour window is justified by a prompt cache staying warm for an hour.
  - Anthropic's prompt-caching documentation gives a 5-minute default lifetime and an optional 1-hour lifetime.
  - The record does not cite which one Claude Code uses on the subscription (playbook rule 8).
  - Reconciliation alone can take up to 60 s, and the turn then waits for a lane.
- Fix: cite the primary source for Claude Code's cache lifetime. If it is 5 minutes, restate the window as a cost-and-staleness trade-off the operator chose, not cache warmth. The decision itself can stand.

**SF8. Counts, cites and status lines were not updated.**
- Foundation:1440 still says "Fifty-four records", and its accepted-dates sentence omits ADR-55 and ADR-56 (24 October 2026). Fix: "Fifty-six records … and ADR-55 and ADR-56 (24 October 2026), from the operator's decisions before M1's build".
- Spec map: SPEC-17 (foundation:2100) should cite ADR-55 and ADR-56, since both records say SPEC-17 delivers them at M3. SPEC-06 (:2087) should cite ADR-56, SPEC-09 (:2090) ADR-55, and SPEC-05 (:2086) ADR-55.
- I-07 (foundation:403): the verification column should add "M3 for capabilities holding `web`".
- Foundation links (checklist 5): SPEC-06-1 §3 should cite ADR-56 and ADR-55; SPEC-06-2 §3 ADR-56; SPEC-09 §3 and SPEC-05 §3 ADR-55.
- SPEC-05:2 and SPEC-06-2:2 status lines lack the "amended 24 October 2026 (v4.11)" note that SPEC-06-1 and SPEC-09 carry.

### Notes

- **N1.** ADR-55 (foundation:1941) and SPEC-05:38 refer to "R3's network profiles" for restricting egress per project. R3 (foundation:2164) lists "network sandbox profiles" for T2 microVM stations only, and nothing commits to restricting T1 egress per project. Either add it to R3's scope (it needs the egress proxy ADR-55 rejects for M1) or say "T2 stations' network profiles".
- **N2.** QS-05 (foundation:269), the failure-model row (:499) and the retry table (:703) hard-code "an hour". The window is a seed the spec owns ("What binds"). Say "within the resume window (seed one hour)".
- **N3.** Runs and sessions (foundation:694) opens with "a new session after a host restart … continues from the workspace", then says it continues by native resume. Reword the first clause to "a later session after a host restart …".
- **N4.** QS-07 (foundation:270) lists issue, review comment and binary as sources of injected text. A web page could be added for parity with the threat row, though ADR-55 does not name QS-07 among its consequences.
- **N5.** Consistency checks that pass:
  - REQ-0623 and DEC-0606: the binding lives in the control plane, so the resumed session runs as the same user, and the workspace path, which Claude Code's transcript lookup needs, is unchanged.
  - REQ-0629: the container restart kills every leftover process, and the entrypoint check confirms none remains.
  - REQ-0619: reconciliation is the trigger.
  - OQ-0603 is updated consistently.
  - ADR-48 and ADR-54 carry correct "Amended by" pointers, and the ADR index marks both.
- **N6.** The last-activity test uses the last host event. A session sitting in a long open kernel call (a consult, from M3) emits no host events and is judged stale. That matches ADR-56's rationale, but SPEC-17 should state it when it applies the rule to suspensions.
- **N7.** A kept configuration directory can be written by the agent. On resume, the credential self-test (REQ-0509) refuses one that holds a login or settings that select credentials. Say that this refusal counts as a failed resume (BL2, item 5).

## Verdict

**Changes required.**
- BL1 makes ADR-56's M1 rule unreachable in the deployment SPEC-05 specifies.
- BL2 leaves REQ-0630 without the contract, key, replay and ownership design the checklist requires. Fix both before TKT-0602 or TKT-0605 start their REQ-0630 work.
- ADR-55's M1 effect (open egress, `web` on the implementer) can go ahead once SF3 and SF4 are fixed.
- SF1 and SF2 must be settled by an amending record before SPEC-03's overrides or the M3 specs (SPEC-15, SPEC-17) are written.
- The rest are minor edits that can go in the same pull request.
