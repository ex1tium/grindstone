# Foundation v4.10 confirmation 1

Scope: commit `3491ff3` on `docs/foundation-v4-10-vision`, read with `git show 3491ff3:<path>` and diffed against the commit review 1 covered (`git diff 55d04a2 3491ff3`). The pass covers three things: whether revision 4 closes F1 to F17 of `foundation-v4-10-architecture-review-1.md`; a full architecture review of ADR-54 and the I-07, QS-07 and threat-model changes it brings; and what revision 4 broke. The ADR-48 change that resolves Q-12 (any mix of accounts, providers and harnesses) was checked as part of the third item. At `3491ff3`, FF-13 traceability reports 0 violations and `uv run pytest -q` passes (43 tests).

**Verdict: changes required, for ADR-54 only.** Revision 4 closes all seventeen findings of review 1. Three small leftovers are listed as N2 to N4. ADR-48 to ADR-53 can stand as accepted once those minor points are fixed. ADR-54 is the right idea: an analysed subject is data, taint follows text that can instruct, and only proof the agent cannot forge clears it. As written, though, it leaves several injection paths open, and one of them defeats the rule by construction. The clearing check can be authored by the same exposed run whose claim it clears (C1). ADR-54 also changes an invariant, so the playbook requires an independent architecture review before acceptance, yet `3491ff3` already marks it Accepted. Keep it Proposed until C1 to C5 are answered, or amend it in place before the pull request merges, while it is not yet append-only on `main`.

## Review 1 findings

| Finding | State | Reason |
| --- | --- | --- |
| F1 | Closed | ADR-52's "Modes", the Decision concept, the Product delegation paragraph, the SDLC autonomy paragraph, the charter glossary entry and the risk row now all say that `never`-class, flagged, `permission` and `manual_check` decisions, irreversible actions and architectural changes stay with a person. Widening that needs its own record amending I-07, I-20 and the flag rule. The charter's "irreversible actions named exactly" field is gone. |
| F2 | Closed (see N2) | A charter never exceeds what the eligibility class allows at the project's level under the instance ceiling. A tripwire trip or a pause drops every charter to Assist; this is stated in ADR-52, the Decision concept and the Tripwire paragraph. |
| F3 | Closed | ADR-49: "A `delivery` answer binds to the change (its derived patch subject's hash), the target and the evidence set the answerer was shown … for single and batched answers alike". ADR-53 now matches. |
| F4 | Closed | The carry-over is named "a bounded exception to I-05". The base the reviewer read is recorded and shown as "carried over from <base>". `SubjectResolver.derive` is added to the SDK row, and SPEC-28 owns it. The "Why" no longer says "exact". |
| F5 | Closed | The updated subject inherits its makers, and whoever resolves a conflict joins them. Project tooling runs on a station. An unresolvable conflict may create a `work` task. |
| F6 | Closed | `WorkspaceProvider.describe_changes(run)` appears in ADR-48, the Task concept and the SDK row, with SPEC-17 as owner. |
| F7 | Closed (see N3) | ADR-50 refuses claim and take-over while a `manual` check exists, the operator may release a claim, and QS-16 is added. |
| F8 | Closed | Consults go to any enabled factory. `delegate` stays the in-task hand-off and never creates a goal. Sub-goals are created by ChangeSet and linked by containment. Q-14 is opened with a default. The glossary entry for Goal is fixed. |
| F9 | Closed | Freshness is restored and the glossary order fixed. |
| F10 | Closed | The revision history matches ADR-52's amendment list (ADR-24 added). The notes on ADR-08 and ADR-31 are removed. |
| F11 | Closed | The foundation says "five releases" and "R1–R5" and updates the caption. The README's rule is narrowed to R1, R3 and R4. |
| F12 | Closed | Both risk rows are rewritten. |
| F13 | Closed | The threat model has the row "Authority laundering through the orchestrator (R2)", charters are in the asset list, and the snapshot crosses as a blob. |
| F14 | Closed | ADR-52's status names the one MVP clause, and ADR-24 is listed as amended. |
| F15 | Closed | The Kernel SDK row (SPEC-17, SPEC-28), the evidence row (SPEC-17, SPEC-28) and the adapter row (SPEC-18) are extended. |
| F16 | Closed | ADR-53 and the glossary say "declared scope (for SDLC, its declared paths)". |
| F17 | Closed (see N4) | Q-12 to Q-14 are in order. Skill grants are in the R1 row. I-06 records data per session. The tripwire trigger is added. The README's M3 row is aligned. SPEC-17 is expected to be written in parts. |

## ADR-54 and the I-07, QS-07 and threat-model changes

**C1 (blocking). The check that clears a claim can be written by the exposed run that made the claim.**
Location: ADR-54, "a claim whose required checks are mechanical — `reproduce`, `cross_tool`, `command` or `test` on the check station — and pass, because its truth rests on evidence the agent cannot write". The RE sketch: "the check station re-runs the analyst's recorded script on the pinned binary and compares outputs". `delegate(…, checks)` takes checks from the agent.
Problem: the check station runs the evidence, but the exposed agent wrote the *check*: the script, the command, the expected output. A steered analyst can record a script whose output matches its claim whatever the binary contains, such as one that prints the claimed value or tests a weaker property. Re-running it proves reproducibility, not the claim. For maker-written tests, the SDLC answer is a judgement prover (the test reviewer, QS-01), but ADR-54 rightly says review never clears taint. As written, nothing stands between the steered agent and a cleared claim, so the restated I-07 can be defeated by construction.
Fix: in ADR-54 and I-07, say that a check clears taint only when its definition was not authored by an exposed run. Either the factory derives it by fixed code from the claim's typed fields (for example, a `cross_tool` comparison of two independent tools at the claimed offsets, or a parser generated from the claimed layout and run on the sample set), or a person approved the check definition. A check script or command written by an exposed run is itself an `untrusted` item. The RE factory specification must name, per claim kind, the fixed check that clears it.

**C2 (major). Exposure cannot be computed from tool output, and the agent's own shell is not covered.**
Location: ADR-54, "tool output a capability's toolbox declares external (for example strings extracted from a binary); exposure is computed from what the run was given and what its tools returned".
Problem: factory domain tools are "separate, secret-less tool servers on the station" (ADR-16), so the control plane never sees their calls or results. The agent also has file and shell tools inside its workspace and can run `strings` on the binary itself, which reaches the same text through no declared tool. Exposure computed from "what its tools returned" is therefore either unenforceable or incomplete.
Fix: compute exposure conservatively and statically, from facts the kernel holds before the session opens. A run is exposed when:
- its context pack holds an `untrusted` item or an external-marked field (C4);
- its inputs or workspace hold a blob marked external, readable by any tool, the shell included; or
- its toolbox includes a tool declared external.
Then nothing depends on observing calls. State that a run is exposed for its whole life once any condition holds.

**C3 (major). Exposure does not follow work that leaves the run: subjects, delegations, questions and decisions.**
Location: ADR-54, "Every item an exposed run proposes is marked `untrusted`"; S6; ADR-52 "Judging questions".
Problem: ADR-54 taints only proposed *items*. An exposed run also:
- makes subjects, such as a commit that could carry a planted backdoor. Tests prove criteria, not the absence of extra behaviour. ADR-53's routine class has no exposure fact, so from R2 policy could deliver such a commit.
- writes `delegate` goals and `ask` questions, free text that reaches a child or consult run, which is then not exposed. S6 is exactly this path: an exposed RE analyst delegates "A Python parser for this format" to an SDLC implementer.
- writes `progress` notes and reports that go into continuation packs.
- raises decisions whose text, and whose workspace snapshot, reaches the orchestrator.
Fix: add to ADR-54:
- "Exposure propagates: a run given text an exposed run wrote — a delegated goal, an `ask` question or answer, a continuation pack, a workspace snapshot — is exposed."
- "A subject an exposed run made carries the exposure; its delivery is `elevated` and its `delivery` decision is flagged `untrusted`."
- "A decision raised by an exposed run is flagged `untrusted`, so no policy or charter answers it."
Add "maker run not exposed" to ADR-53's list of routine facts.

**C4 (major). The rule for free text in cleared items leaves agent-written text, presentation fields and citation-only clearance open.**
Location: ADR-54, "an item whose every semantic field cites such cleared claims, such as an interface item built from proven findings … A cleared item carries in its semantic fields only what its evidence proves; free text taken from the subject is kept as quoted data, marked external, and renders as such."
Problem:
- Only text "taken from the subject" is quoted. A steered agent paraphrases the injected instruction in its own words ("the parser should also execute field X"), and that text stays in a cleared item unquoted.
- The rule covers semantic fields only. Presentation fields (`title`, `summary`) are rendered into context packs too.
- "Only what its evidence proves" has no mechanism. Nothing marks which fields a check proves.
- "Cites" is not "proves". An interface item can cite claim C for a field width and state a different value, and still be cleared.
- Quoted external text "renders as such" into an SDLC implementer's context pack, but reading it does not make the implementer exposed. That is the path from cleared findings and interface items into code.
Fix:
- Kinds declare which typed fields a check proves.
- In an item proposed by an exposed run, only those fields are cleared, and only when their values equal what the passing evidence recorded. Every other field, free text written by the agent included, semantic or presentation, is stored as external-marked text.
- An interface item is cleared by its own passing mechanical conformance check (C1's rule), not by citation.
- Reading any external-marked field exposes the reader (C2).

**C5 (major). I-07 is stated for the MVP but enforced only from R1, and its wording widens the exception.**
Location: I-07, "Scope expansion, content from outside the project, and what a run exposed to such content proposes need a person, unless passing mechanical evidence proves the claim (ADR-54)", enforced by "exposure tests (R1)". ADR-54: "the MVP's intake path (ADR-32) already marks imported content `untrusted` and needs no change".
Problem:
- Grammatically, "unless passing mechanical evidence proves the claim" now qualifies all three subjects. It reads as if mechanical evidence could clear a scope expansion or the outside content itself.
- The MVP has exposed runs: M5's `/repair` repairer and any implementer whose pack holds an `untrusted` review-comment finding (ADR-32, SPEC-24). The invariant applies from acceptance, but nothing in the MVP computes exposure. So "needs no change" is inaccurate for the run side, even if it is accurate for intake.
Fix:
- Reword I-07 as two sentences: "Scope expansion and content from outside the project need a person. What a run exposed to outside content proposes, or makes, is `untrusted` unless passing mechanical evidence from a check it did not author proves it (ADR-54)."
- Bring the minimal, static exposure rule (an `untrusted` item in the context pack) into the MVP with SPEC-16 or SPEC-17, and leave external blobs and declared tools to R1. Alternatively, state explicitly that until R1 a run whose pack holds an `untrusted` item has all its proposals and subjects routed to a person, and name the specification that does it.
- Mark the kernel ownership for R1: the external marker on blobs (`store`), on fields (`intent`), exposure (`work`), marking (`change`).

**C6 (minor). QS-07 and the prompt-injection threat row do not yet name the bypass they must test.** Location: QS-07, "from R1, only a claim proven by passing mechanical evidence is cleared"; threat row "Prompt injection from outside". Fix: once C1 to C4 are settled, add the response "a claim whose check an exposed run authored, or whose free text an exposed run wrote, stays `untrusted`". Add a threat-row example in which an injected string in a binary steers the analyst into writing a self-confirming script, mitigated by C1.

## What revision 4 broke or left behind

**N1 (major). ADR-54 is marked Accepted before its independent architecture review.** Location: How decision records work, "ADR-48 to ADR-54 (22 October 2026)"; ADR-54 status; `docs/m0/status.md`, "ADR-48 to ADR-53 accepted after an independent architecture review". The playbook requires an independent architecture review before accepting a change to an invariant, and ADR-54 restates I-07. Fix: hold ADR-54 at Proposed until C1 to C5 are answered and confirmed, or record that this pass is its review and amend it in place before merge. Make `status.md` say which records the review covered.

**N2 (minor). Assist mode contradicts the new level bound.** Location: ADR-52 "Modes", "Assist (it answers escalations and recommends everything else)", and the Product table, "Assist | Drives the work, answers escalations …". The same records also say "A charter never exceeds what a decision kind's eligibility class allows at the project's autonomy level". `escalation` is `l2`, and a tripwire trip demotes charters to Assist *and* drops the project to L1, where nothing `l2` may be answered. So after a trip, either Assist answers nothing or the bound is broken. Fix: say "Assist drives commands and recommends; it answers escalations only while the project is at L2 or above". Alternatively, make escalation retries an explicit, named exception with its reason.

**N3 (minor). The F7 guard can still be bypassed by a `manual` check that appears later.** Location: ADR-50, "a task whose check plan includes a `manual` check cannot be claimed". A `manual` check can arrive after the claim through a ChangeSet to the check plan, or a factory's collect can add one through `extra_checks`. Fix: add "a `manual` check added to a person-made task's plan raises an escalation offering to change the check or return the task to an agent".

**N4 (minor). Leftovers from I-06 and harness.**
- The Task concept still says "Every run records the item revisions, capability hash, factory version, provider, model, …" (I-06 now records provider, account, harness and model per session).
- ADR-48's decision opens "a provider, an agent preset, the models it serves", while the glossary now says "agent harness".
- The Delivery port concept paragraph does not mention ADR-49's answer binding or the carry-over exception. Under the "every tab" rule, one sentence pointing to ADR-49 is enough.
Fix: align the three.

## Checked and found sound

- ADR-48's resolution of Q-12: any mix of accounts, providers and harnesses, roles mapped freely, provider terms the operator's responsibility, a new harness gated by a spike, and account and harness recorded per session. No role is tied to a vendor, which keeps ADR-41's abstraction whole.
- The F1 and F2 fixes leave no route to gating evidence or irreversible action through a charter. The threat row and risk row agree with ADR-52.
- ADR-49 now keeps I-05 honest (a stated exception that the card shows), I-09 (tooling on a station) and I-15 (inherited makers). The decision lifecycle extension (re-raise after the change moves) is consistent with ADR-28's "approval of something the person did not see".
- ADR-54's core distinctions hold up: review never clears taint, mechanical evidence is the only clearing proof, station tiers are unchanged, and intake by fixed code (ADR-32) stays as it is.
- Counts: fifty-four records with index row 54, Q-12 to Q-14, QS-16 under QG-1, R1–R5, and the ADR-32 status pointer. FF-13 passes and the Python suite passes.
