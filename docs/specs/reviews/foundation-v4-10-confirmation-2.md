# Foundation v4.10 confirmation 2

Scope: commit `e07f52f` on `docs/foundation-v4-10-vision`, read with `git show e07f52f:<path>` and diffed against `3491ff3` (`git diff 3491ff3 e07f52f`). This pass covers three things: whether revision 5 closes C1 to C6 and N1 to N4 of `foundation-v4-10-confirmation-1.md`; whether the rewritten ADR-54 opens any new injection path; and whether revision 5 broke anything. At `e07f52f`, FF-13 traceability reports 0 violations and `uv run pytest -q` passes (43 tests).

**Verdict: changes required. ADR-54 is close, but it cannot be accepted yet.** Revision 5 closes every finding of confirmation 1. The rewritten ADR-54 has the right structure: exposure is computed statically and propagates; subjects and decisions of exposed runs are `untrusted`; only kind-declared typed fields clear, and only by checks no exposed run wrote; interface items clear only by their own check. Three major gaps remain, each with a short fix:
- the record never says when taint ends, which leaves MVP flows either laundering or permanently tainted (D1);
- kernel read tools let a run read `untrusted` content after its exposure was fixed (D2);
- the consult cache can hand an exposed run's answer to an unexposed caller (D3).

The "person approved its definition" route does not reopen laundering, provided the approval goes through a decision flagged `untrusted` (D4, minor). Once D1 to D3 are fixed, ADR-54 can be accepted.

## Confirmation 1 findings

| Finding | State | Reason |
| --- | --- | --- |
| C1 | Closed | A check clears a field only if "no exposed run authored the check": the factory derives it by fixed code, or a person approved its definition. "A check an exposed run wrote is itself `untrusted` and clears nothing." The RE sketch now makes the analyst's script a working note. |
| C2 | Closed (see D2) | Exposure is computed before the session opens, from the pack, the inputs or workspace (so the shell is covered) and the toolbox declaration, "never from tool output the control plane cannot see". |
| C3 | Closed (see D1, D3) | Propagation through `delegate`, `ask`, `progress` notes, decision payloads and snapshots. Proposals of exposed runs are `untrusted`, their decisions are flagged `untrusted`, and their subjects are `elevated` with the delivery flagged. ADR-53 gains the fact "no run that made the change was exposed". |
| C4 | Closed (see D5) | Kinds declare the provable fields. A field clears only if its value equals the evidence. All other text from an exposed run is external-marked, and reading it exposes the reader. Interface items clear only by their own conformance check, "never by citing cleared claims". |
| C5 | Closed | I-07 is split into two sentences. M3 applies the `untrusted`-in-pack rule (SPEC-16, SPEC-17, SPEC-28 cite ADR-54). The R1 owners are named (`store`, `intent`, `platform`) and rows added. |
| C6 | Closed | QS-07 and the threat row name the self-confirming script and why it clears nothing. |
| N1 | Closed | ADR-54 is Proposed, and "accepted once its architecture review confirms it". `status.md` and the README say which records the review covered. |
| N2 | Closed | Assist "answers escalations when the project is at L2 or above, and otherwise recommends". |
| N3 | Closed | "A `manual` check added after a claim … raises an escalation that offers to change the check or return the task to an agent." |
| N4 | Closed | The Task concept records provider, account, harness and model per session. The Delivery port concept states the carry-over exception and the answer binding. ADR-48 and the Agent accounts concept say "harness". |

## Findings on revision 5

**D1 (major). Taint has no defined end, so MVP flows either launder injected text or taint the project for good.**
Location: ADR-54, "A person's approval. An item a person approved in an `untrusted` ChangeSet carries their approval, but its external-marked text stays marked and still exposes runs that read it"; "When it applies. From M3, `untrusted` items in a context pack make a run exposed"; ADR-32, "Everything derived from a signal stays `untrusted`"; M5-03, "then a ChangeSet a person approved".
Problem: M3 has no external-marked fields, which arrive in R1, so the approval bullet does not say what happens to an approved `untrusted` item in M3. Take the main MVP flow. A review-comment finding (ADR-32, and SDLC `observe` from M1) becomes an approved ChangeSet that amends a requirement, and `/repair` makes a commit that a person delivers. Two readings are possible:
- **The approved revision stays `untrusted`.** Every later run pinned to that requirement is exposed. The same holds if "text an exposed run wrote" covers code merged into the repository, which every later run reads. Every such run's decisions are then flagged `never`, and its subjects are never routine. Taint spreads through the item graph and the repository, L2 policy (M5-04) answers less and less, and the decision-load measure cannot fall.
- **Approval clears it.** Then a person who approves a finding has also cleared the injected sentence in its summary. That is consistent with I-07 ("need a person"), but the text should say so, and the card should help the person see it.
The same question applies to subjects. Neither reading is stated, and each specification would pick its own.
Fix: add an end rule to ADR-54, for items and subjects alike:
- "A person's approval of an `untrusted` ChangeSet clears the `untrusted` state of the revisions it applies, and a person's `delivery` answer clears the exposure of the subject it delivers. Exposure is a property of runs and of unapproved output, never of the ledger or the repository after a person approved it. From R1, text an exposed run wrote stays external-marked in the approved revision and exposes its readers, but the rest of the revision does not."
- The approval card for an `untrusted` ChangeSet shows the external text verbatim and marked, and is never batched with trusted ones.
- Add "subjects and workspaces an exposed run made" to the propagation list for the time *before* that approval. This covers a retry starting from the previous run's diff (M3-06), rework rounds, the conflict-resolution work task (ADR-49) and reviewers of the subject.
- Update ADR-32's "stays `untrusted`" to match.

**D2 (major). Exposure is fixed before the session, but kernel read tools reach `untrusted` content during it.**
Location: ADR-54, "Exposure is fixed for the whole run, decided by the kernel from these facts"; MCP tools `read_items(query)` (M2) and `search(text)` (M5): "Full-text search over the project", whose index covers findings and report summaries (ADR-31).
Problem: an unexposed run can call `search` or `read_items(query)` and receive the text of an `untrusted` review-comment finding, or the report summary of an exposed run, in the middle of the session. The control plane serves these tools itself, so this is not the "station-local, invisible" case C2 excluded. As written, the run stays unexposed, and what it proposes or makes is trusted.
Fix: add to ADR-54: "The kernel's own read tools either withhold `untrusted` items, external-marked text and output of exposed runs from an unexposed run, or mark the run exposed from that call on, with the consequences above; the result says which." Withholding by default is simpler and keeps exposure decidable before the session. Make the agent ask for the content explicitly to accept exposure.

**D3 (major). The consult cache can launder an exposed consult's answer.**
Location: ADR-38, "its answer is cached by `(capability hash, question hash, input hashes)`, and an identical ask joins a consult already in flight"; ADR-54, "Exposure propagates … an `ask` question".
Problem: a consult run answering an exposed caller is exposed. Its answer is free text from an exposed run, but it is cached under a key that ignores exposure. A later unexposed caller asking the same question with the same inputs receives that answer, from the cache or by joining the in-flight consult, and is not exposed.
Fix: add to ADR-54 (and note it on ADR-38's status as amended by ADR-54): "A consult answer from an exposed run is served only to exposed callers. Exposure is part of the cache key and of the single-flight join."

**D4 (minor). The "person approved its definition" route needs a named vehicle.**
Location: ADR-54, "or a person approved its definition".
Problem: the route itself is sound, since I-07 lets a person decide. But check definitions are `evidence` records, not items, so the "untrusted ChangeSet" path does not obviously carry them. Agents also set checks directly through `delegate(…, checks)`. Without a named vehicle, a specification could let policy or a charter approve a definition. It could also apply an approval that does not bind to the exact definition. Either would reopen laundering.
Fix: say "a check definition an exposed run wrote is approved only through a decision flagged `untrusted` (class `never`), which shows the full definition and binds to its hash; any change re-raises it."

**D5 (minor). Free text inside a typed contract is not addressed.**
Location: ADR-54, "A kind declares which of its typed fields a check proves". The interface item's `contract` field is one typed field holding JSON (an OpenAPI fragment or a format layout) that can contain `description` and name strings.
Fix: state that provable fields may be declared at member granularity inside a typed field, and that free-text members of a typed value (descriptions, names, examples) written by an exposed run are external-marked like any other free text.

**D6 (minor). Accepted ADR-53 now states a proposed rule as accepted.**
Location: ADR-53, Status "Amended by ADR-54: a subject an exposed run made is never routine". Its decision text gains "no run that made the change was exposed (ADR-54)". The index row reads "(amended by 54)", while ADR-32's row says "(amended by 54, proposed)". I-07, QS-07 and the threat row likewise state ADR-54's rule while ADR-54 is Proposed.
Fix: add "(proposed)" to ADR-53's status line and index row, as for ADR-32. Record that ADR-54 must be accepted, or these tab changes reverted, before the pull request merges.

**D7 (minor). One risk row still says everything derived stays `untrusted`.**
Location: risk "Prompt injection through external signals or analysed content": "everything derived stays `untrusted` and needs a person".
Fix: align it with ADR-54 and D1: "derived output stays `untrusted` until a person approves it, except typed fields proven by checks no exposed run wrote (ADR-54)".

## MVP flows under the M3 exposure rule

None becomes impossible, provided D1 is resolved the way proposed:
- A `/repair` run (M5) reads `untrusted` findings, so it is exposed. Its proposals wait for a person (as ADR-32 already requires). Its decisions are flagged, so no L2 policy answers its escalations. Its subject is `elevated`, and every MVP delivery has a person anyway.
- A review-comment finding a person approved stops exposing readers once approved (D1's rule), so tickets and requirements built on it run normally.
- `delivery_bypass` findings (ADR-40) are `untrusted`. A run that investigates one is exposed, which is the intended behaviour.

Without D1's rule, the second flow taints every downstream run for good, which in practice makes M5-04's policy answers unavailable on any requirement that ever touched outside text.

## Checked and found sound

- C1's clearing rule: a field clears only when the value equals the evidence, the check is mechanical on the check station, and its author was not exposed. Together these defeat a self-confirming script without trusting any model, and review rightly never clears.
- Static exposure from pack, inputs or workspace, and toolbox is decidable before the session and covers the agent's shell.
- The propagation list now reaches the orchestrator (snapshots, decision payloads), so charters cannot answer anything an exposed run raised. This holds together with ADR-52's "never anything `untrusted`".
- ADR-53's new routine fact and ADR-49's answer binding work together: an exposed maker can never reach policy delivery in R2.
- I-07's split wording no longer lets mechanical evidence clear scope expansion or outside content itself.
- Ownership rows, the SPEC-16, SPEC-17 and SPEC-28 citations, the index row 54, Q-13's status, and the README and status pointers are consistent.
