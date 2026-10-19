# SPEC-04 — Items, thin ChangeSet apply and decision records
Status: accepted (by the operator, 19 October 2026, after the reviews in `docs/specs/reviews/`) · Milestone: M1
Kind: kernel · Owns: `grindstone.intent` (items, revisions, edges from typed references, lifecycles, ID allocation, rendering, the item bundle import format, the `core` kinds), `grindstone.change` (ChangeDrafts, ChangeSets, the one-round walk, verdicts, apply), `grindstone.decisions` (decision records, kernel decision kinds, flags, answers, continuations)

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

Intent is what Grindstone proves work against, so it must be typed, versioned and changed only through a reviewed ChangeSet (ADR-08, ADR-10). Anything that needs a person must be a typed decision with a recommendation (ADR-28). This specification builds the thinnest form of all three that keeps their invariants:
- items with immutable, provenanced revisions;
- an import of hand-written items as a ChangeSet;
- a walk that reaches a fixed point in one round, because M1 accepts only `unaffected` verdicts;
- an atomic, serialized apply;
- decision records whose answers start a continuation exactly once.

M1-01's ticket enters the ledger this way, and every later decision card in M1 rides on it.

## 2. Scope

In scope:
- Items, revisions, provenance and edges derived from typed reference fields.
- Lifecycle declarations interpreted, with one transition function per lifecycle.
- ID allocation and generic Markdown rendering.
- The five `core` kinds in their first form.
- The item bundle import format.
- ChangeDrafts from operator imports, task output and kernel intake.
- A one-round impact walk; operator verdicts given on the approval card, `unaffected` only; M1 rules; approval; apply with a base-revision check.
- Decision records of kinds `approval`, `question`, `permission`, `delivery` and `escalation`: flags, recommendation, context hash, answers, supersession by their owner, and continuations.
- SQL enum generation for kernel lifecycles, added to `make gen` (as SPEC-01 left it).

Out of scope:
- Mentions, embeds, artifacts and their headers, link suggestions, Markdown round-trip and import of rendered Markdown: SPEC-11 (M2).
- Multi-round walks with `amend`, `invalidate` and `escalate` verdicts, group verdicts and the round limit: SPEC-12 and SPEC-16.
- Delivering changes to running tasks at their next turn, and cancelling tasks whose pinned item was removed: SPEC-16 (M3). M1 emits the events they will consume.
- Revert: SPEC-16.
- Presentation-only edits that apply without a walk: SPEC-16. In M1 every ChangeSet is approved.
- Manifest rules beyond those listed here: SPEC-13.
- Batching, expiry of `permission` decisions to deny, a decision superseded three times becoming an escalation, policy, autonomy levels, and the kinds `manual_check`, `suggestion` and `scope`: SPEC-15 and SPEC-25. In M1 every decision waits for a person.
- Writers other than `changeset` for factory lifecycles (the kernel writing a state from task or evidence state): SPEC-11 and SPEC-12.
- Field-level merging of a ChangeSet over a moved base: SPEC-16. In M1 a moved base always asks again (REQ-0415).

## 3. Foundation links

Implements:
- ADR-08 (as amended by ADR-44): namespaced, typed, hashed items; immutable revisions with provenance; lifecycle state stored beside the item and never hashed; the five `core` kinds.
- ADR-09 in part: edges are derived from typed reference fields and stored per revision, never edited separately, with the impact rule their edge type declares.
- ADR-10 in its thinnest form: draft, walk to a fixed point, rules, approval, one atomic apply with a base-revision check, serialized per project.
- ADR-28: one decision record for every question to a person, with kinds as registry entries, a recommendation and its source, kernel-set flags, refusal of answers to superseded or changed decisions, and waiting by typed continuation.
- I-01: `intent` accepts revisions only from ChangeSet apply.
- I-02: append-only revisions with non-null provenance.
- I-03: no agent-facing path applies or transitions anything. `propose` (SPEC-07) only adds to a ChangeDraft.
- I-07: a ChangeSet from intake is `untrusted`, and its approval is flagged `untrusted`.
- I-11: every wait on a person is a decision with a recommendation.
- I-13: apply requires an approved ChangeSet whose walk reached a fixed point.

Delivers:
- M1-01, the intake clause: "a ticket with acceptance criteria, imported from a file as a ChangeSet approved on a decision card" → AC-0409-1, AC-0412-1, AC-0414-1. SPEC-09 supplies the kinds and SPEC-10 the card.

Depends on:
- SPEC-01: `Contract`, `semantic_hash`, typed IDs, `Provenance`, `ItemRef`, the error envelope.
- SPEC-02: the unit of work, migrations, advisory locks, `store.start`.
- SPEC-03: registered kinds (`KindDecl` compiled to contracts), edge types, decision-kind registry, `emit`, event consumers, project configuration (enabled factories).

Scenarios: K1 step 7 (the walk raises an `approval` decision; the operator approves; apply writes the revision) and K4 step 3 in part (apply writes the revision; evidence pinned to the old one is stale by SPEC-08's freshness).

## 4. Requirements

REQ-0401: An item is identified by project and ID, has one kind, and has a current revision; a revision is immutable and holds the item's semantic fields, presentation fields, semantic hash, parent revision and provenance.
REQ-0402: `intent` writes revisions only inside ChangeSet apply; no other function creates or changes a revision or an item's current revision.
REQ-0403: Each revision's edges are derived from its typed reference fields when it is written, one edge per referenced ID with the edge type its field declares, and edges are never written any other way.
REQ-0404: A revision whose reference names an item that neither exists in the project nor is created in the same ChangeSet is refused with `reference_unresolved`.
REQ-0405: A kind with a lifecycle stores its state beside the item, never in the revision; one transition function per lifecycle is the only writer, refuses a transition its table does not list for that writer with `transition_illegal`, and records each transition with its writer and cause.
REQ-0406: An item created by apply enters its kind's `initial` lifecycle state.
REQ-0407: The kernel allocates IDs for kinds that declare an allocation format, never reusing a number in a project and skipping numbers already taken there, including imported ones, and refuses an imported or proposed ID that does not match its kind's pattern or is already taken by another kind.
REQ-0408: `render(revision)` produces Markdown with a header naming the item and the ledger as source of truth, the title, every semantic field and every reference as `[[ID]]`.
REQ-0409: An item bundle (YAML, schema version 1: a list of items with kind, ID, title and fields) parses into one ChangeDraft from the operator, or is refused with every item's errors.
REQ-0410: A ChangeDraft records its source (operator, task output, delegation result, intake, revert), its trust, its proposed revisions with the base hash each was drafted against, and the provenance every revision will carry; an operator draft carries the client key of the request that made it, unique per project, so a repeated import returns the original draft.
REQ-0411: The walk of a ChangeSet lists, for every semantically changed item, every current item outside the set that has a `review` edge to it; when that list is empty the walk is at its fixed point, and otherwise it is at its fixed point once each listed item has an `unaffected` verdict with a reason.
REQ-0412: A walked ChangeSet that passes the M1 rules raises one `approval` decision listing every proposed revision and every item the walk reached, flagged `untrusted` when its draft is untrusted.
REQ-0413: An approval answer applies the ChangeSet only if it gives an `unaffected` verdict with a non-empty reason for every reached item; otherwise the answer is refused with `verdict_missing`, and `reject` ends the ChangeSet with nothing applied.
REQ-0414: Apply is one transaction serialized per project: it checks every base hash against the current revision, then writes all revisions, edges, current pointers and initial lifecycle states, and emits `item.revised` for each item and `changeset.applied`, or writes nothing.
REQ-0415: When a base hash no longer matches at apply, nothing is applied: the ChangeSet's approval is superseded, its revisions' diffs are recomputed against the new base, the ChangeSet is walked again, and a new approval is raised whose context hash covers the new base, so no revision is ever applied over a change its approver did not see; the new bases are recorded on the new walk round, and from then on the rules, the approval's context hash and the apply check compare against the latest round's bases, so answering the new approval applies the ChangeSet unless the base moves again.
REQ-0420: Every lifecycle column of the kernel (kind lifecycles in `intent`, and the ChangeSet, decision, task, run and delivery lifecycles) and every table declared single-writer is written only by the function registered for it; FF-08 fails the build otherwise.
REQ-0421: `change` drafts and submits a ChangeSet for every `change.draft_requested` event, whose contract this specification owns and which any module may emit with the draft's source, trust, proposed revisions (as a blob), provenance and client key; so `work` (a task's proposals) and `delivery` (an outside merge) never import `change` (Components, "Module map"), and a request emitted twice drafts once.
REQ-0416: Every decision has a registered kind, a scope, a context hash, a recommended answer with its reason and source, and kernel-set flags; raising one without a recommendation is refused.
REQ-0417: An answer is refused if the decision is not open (`decision_superseded` when it was superseded), if the context hash the answerer saw differs from the decision's (`context_changed`), or if it fails the kind's answer schema; an accepted answer records who answered, through which channel and when; repeating an accepted answer with the same client key returns the original result.
REQ-0418: An accepted answer starts the decision's registered continuation exactly once, even if the process is killed after the answer commits.
REQ-0419: Only the module that raised a decision supersedes it, naming the replacement, and a superseded decision stays readable.

## 5. Design

**Contracts.**

`grindstone.contracts.intent`, schema version 1 each:

| Model | Fields |
| --- | --- |
| `ItemRevision` | `id` (UUIDv7), `project`, `item: ItemId`, `kind`, `title`, `semantic: JsonObject`, `presentation: JsonObject`, `hash: SemanticHash`, `parent: RevisionId \| None`, `provenance: Provenance`, `changeset: ChangeSetId` |
| `Edge` | `revision`, `source: ItemId`, `type`, `target: ItemId` |
| `ItemBundle` | `schema_version: 1`, `items: tuple[BundleItem, ...]` with `kind`, `id`, `title`, `fields` |
| `LifecycleTransition` | `item`, `kind`, `from_state`, `to_state`, `writer`, `cause` (a ChangeSet, task, evidence or delivery ID), `at` |

`grindstone.contracts.change`:
- `ChangeDraft`: `id`, `project`, `source`, `trust` (`trusted` or `untrusted`), `revisions: tuple[ProposedRevision, ...]` with `item`, `kind`, `base: SemanticHash | None`, `title`, `fields`, and `provenance`.
- `WalkResult`: `round`, `bases: tuple[ItemBase, ...]` with `item` and `base: SemanticHash | None` (the base each proposed revision is walked against in this round; round 1 copies the draft's), `changed: tuple[ItemId, ...]`, `reached: tuple[Reached, ...]` with `item`, `via_edge`, `to`.
- `Verdict`: `item`, `verdict: unaffected`, `reason`.

`grindstone.contracts.decisions`:
- `Decision`: `id`, `project`, `kind`, `flags`, `scope` (`task`, `changeset`, `delivery` or `run` IDs), `context_hash`, `title`, `payload`, `recommendation` (`answer`, `reason`, `source`: `fixed`, `agent` or `advisor`), `state`, `raised_by`, `raised_at`.
- `Answer`: `decision`, `answer`, `answered_by`, `channel` (`ui`, `api`, `vscode`, `plugin`), `context_hash_seen`, `client_key`, `at`.

**Kernel decision kinds** (registered with SPEC-03; their eligibility classes are seeds owned by SPEC-15):

| Kind | Payload | Answer | Class |
| --- | --- | --- | --- |
| `approval` | ChangeSet ID, revisions with diffs against their base, reached items | `approve` with `verdicts`, or `reject` with `notes` | `l2` |
| `question` | The asking task and run, question, refs, answer schema | `answer` valid against the question's schema | `never` |
| `permission` | The task, the action and its reason | `allow_once`, `allow_task`, `deny` | `never` |
| `delivery` | The delivery, its subject, the evidence summary, the delivery mode | `deliver`, `hold`, `cancel` | `l3` |
| `escalation` | The task or run, failure cause, evidence | `retry`, `cancel` in M1; SPEC-06 and SPEC-15 add others | `l2` |

Flags are the closed set of Concepts, "Decision". They are set only by kernel code that raises the decision, and never accepted from a payload.

Kernel error codes declared here (in `grindstone.contracts.errors`, SPEC-01):
- validation: `reference_unresolved`, `kind_not_enabled`, `id_invalid`, `id_taken`, `answer_invalid`, `recommendation_missing`;
- rule: `transition_illegal`, `verdict_missing`;
- authority: `decision_superseded`, `context_changed`, `decision_closed`.

Events: `change.draft_requested` (emitted by other modules, consumed here), `item.revised`, `item.transitioned`, `changeset.drafted`, `changeset.walked`, `changeset.applied`, `changeset.rejected`, `decision.raised`, `decision.answered`, `decision.superseded`.

**State and ownership.**

| Schema | Table | Write pattern |
| --- | --- | --- |
| `intent` | `items (project, id, kind, current_revision, lifecycle_state)` | Insert at apply; `current_revision` updated only by apply; `lifecycle_state` only by the transition function |
| `intent` | `item_revisions`, `edges`, `lifecycle_transitions` | Insert only |
| `intent` | `id_counters (project, prefix, next)` | Updated by allocation |
| `intent` | `lifecycle_states (kind, state)` | Rewritten from the registries at start-up; `items` references it, so the database refuses an undeclared state. A factory version that removes a state items still hold is refused at start-up (`manifest_invalid`, naming the state and the count of items), which pauses its projects (SPEC-03); mapping states across versions is an upgrade step (SPEC-13) |
| `change` | `change_drafts`, `changesets (id, project, draft, state, decision)`, `walk_rounds (changeset, round, bases, changed, reached)`, `verdicts` | Drafts, rounds and verdicts insert only; `state` by the ChangeSet transition function |
| `decisions` | `decisions (…, state)`, `answers`, `continuations (decision, name, payload)` | `state` by the decision transition function; answers and continuations insert only |

Kernel lifecycles, with PostgreSQL enums generated from their Python definitions by `make gen` (FF-08):

| Lifecycle | Transitions (writer) |
| --- | --- |
| ChangeSet | `drafted → walked` (walk) · `walked → awaiting_approval` (walk) · `awaiting_approval → applied` (apply) · `awaiting_approval → walked` (apply, base moved) · `awaiting_approval → rejected` (answer) |
| Decision | `open → answered` (answer) · `open → superseded` (owner) · `open → expired` (reserved for SPEC-15; no writer in M1) |

A kind's lifecycle is the factory's table (SPEC-03 `KindDecl.lifecycle`), whose writers are from the closed set `changeset`, `task`, `evidence` and `delivery`. In M1 only `changeset` writes, setting the initial state at apply.

**The `core` kinds, first form** (SPEC-11 extends them):

| Kind | ID | Fields (all semantic unless noted) |
| --- | --- | --- |
| `core.principle` | `P-n` | `statement` (text) |
| `core.learning` | `LRN-n` | `lesson` (text), `tags` (list of strings) |
| `core.finding` | `FND-n`, allocated | `type` (enum: `ambiguity`, `gap`, `conflict`, `discovery`, `failure`, `drift`, `delivery_bypass`), `severity` (`low`, `medium`, `high`), `trust` (`trusted`, `untrusted`), `description` (text), `about` (refs to any kind, edge `core.about`, impact `notify`) |
| `core.observation` | `OBS-n`, allocated | `source` (string), `content` (text), `inputs` (list of strings: the hashes it saw) |
| `core.interface` | `IF-n` | `shape` (string), `contract` (text holding JSON, which SPEC-11 validates against the shape's schema; OQ-0403), `provider` and `consumers` (refs) |

**Import (REQ-0409).** `intent.parse_bundle(bytes)` uses the safe YAML loader and the `ItemBundle` contract. Each item validates against its compiled kind contract, its ID pattern and the project's enabled factories, and its references resolve against the project or the bundle. An ID that exists gives a revision with the current hash as its base; a new ID gives a creation. Errors are collected per item and returned together. Example, with the `notes` fixture:

```yaml
schema_version: 1
items:
  - kind: notes.note
    id: N-3
    title: Opening paragraph
    fields: {body: "Grindstone proves work against intent."}
```

**Walk (REQ-0411).**
- `changed` are the items whose proposed semantic hash differs from their base in this round (`WalkResult.bases`); creations count as changed.
- A ChangeSet's **effective bases** are those of its latest walk round. The draft's bases, which are insert-only, are only round 1's (DEC-0407).
- For each, the walk queries current edges whose `target` is the item and whose edge type has impact `review`, and keeps sources that are not in the draft.
- Edges of impact `notify` and `render` are listed for information and need no verdict (ADR-09).

Each walk in M1 runs exactly one round; a re-walk after a moved base (REQ-0415) is a new walk with its own round number. Its verdicts can only be `unaffected`, so no verdict adds an amendment, and one round is a fixed point by definition. A reviewer who thinks an item is affected rejects the ChangeSet with notes and drafts a larger one (DEC-0402).

**Rules in M1**, checked at draft time and again before raising the approval:
- references resolve (REQ-0404);
- kinds belong to factories enabled in the project;
- IDs match their kind's pattern and are not taken by an item of another kind;
- each revision of an existing item has an effective base equal to the current hash.

A failure refuses the draft with every error listed per item.

**Approval and apply.**
1. The walked ChangeSet raises `approval` with a context hash: the semantic hash of the ChangeSet ID, the walk round, the draft's revisions with their effective bases, and the reached list. Its recommendation is `approve`, source `fixed`, reason "rules pass; every reached item needs your verdict", or "rules pass; nothing else is affected" when the reached list is empty. Its continuation is `change.apply`.
2. The answer's continuation runs the workflow `decision-<id>` with one datasource transaction step:
   - take `uow.lock(("apply", project))`;
   - re-check every effective base against the current hash;
   - insert revisions with provenance (`author_kind` from the source, the ChangeSet, the task or decision behind it, the reason);
   - derive and insert edges;
   - update current pointers;
   - allocate nothing (IDs were fixed at draft);
   - set initial lifecycle states through the transition function;
   - emit events;
   - move the ChangeSet to `applied`.
3. On a moved base the step applies nothing. In one unit of work it supersedes the approval, moves the ChangeSet back to `walked`, and re-walks as a new round whose `bases` are the items' current hashes, against which every revision's diff is recomputed; a new approval follows, whose context hash covers the new round and its bases (REQ-0415). The M1 rules then pass on the effective bases, and the apply check of the new approval's answer compares against them. The proposal still carries the fields drafted against the old base, so the card shows what applying it now would change, including any reversal of the change that moved the base. The foundation's "approval is asked again only if the review set changed" holds with the review set read as the proposed revisions' diffs plus the reached items: a moved base always changes the diffs. Merging fields over a moved base is SPEC-16's.

**Draft requests (REQ-0421).** `ChangeDraftRequested` (event `change.draft_requested`, in `grindstone.contracts.change`) carries `source`, `trust`, `revisions` (a `BlobRef` to the proposed revisions as JSON, so large proposals stay out of the event), `provenance` and `client_key`. Its consumer, registered at the composition root (SPEC-03), parses the blob, validates it like any draft and submits it; the client key is unique per project, so a request delivered or emitted twice drafts once. The contract lives here, below its emitters, so no specification cycle arises (DEC-0406). In M1 two modules emit it:
- `work` at collect (SPEC-06 part 2): source `task output`, trust `trusted`, the run's proposals, client key `run:<run>`;
- `delivery` on an outside merge or published change in unenforced mode (SPEC-08): source `intake`, trust `untrusted`, one `core.finding` of type `delivery_bypass`, severity `high`, `about` the delivery's targets, client key from the observation's external ID; its approval is flagged `untrusted` (I-07).

A draft that fails the M1 rules is refused as for any source, and the refusal is recorded on the request with its errors for the emitter's owner to show.

**Decisions.**
- `raise_decision(uow, kind, scope, payload, recommendation, flags, continuation)` validates the payload against the kind, refuses a missing recommendation, inserts the decision and its continuation, and emits `decision.raised`.
- `answer(...)` runs in one unit of work: lock the row, check state and context hash, validate, insert the answer, transition to `answered`, emit `decision.answered`.
- A registered consumer of `decision.answered` (SPEC-03's dispatcher) starts `decision-<id>`, which runs the named continuation with the answer. A crash after the answer commits therefore still starts it once (REQ-0418, DEC-0403).
- Continuations are registered by name at the composition root (`change.apply`, and in later specifications `work.resume_run`, `delivery.deliver`), so `decisions` imports no higher module (Components, "Module map").

**Interfaces.**
- `intent`: `read(project, id)`, `read_pinned(ref)`, `current_hash(project, id)`, `edges_to(project, id)`, `render(revision)`, `parse_bundle(bytes)`, `allocate(uow, project, kind)`, `transition(uow, item, to, writer, cause)`.
- `change`: `draft(uow, …)`, `submit(changeset)`.
- `decisions`: `raise_decision`, `answer`, `supersede(uow, decision, replacement)`, `open_decisions(project)`, `register_continuation(name, workflow)`.

REST and the card are SPEC-10's; the `propose` tool is SPEC-07's.

**Configuration.** None of its own. Enabled factories come from SPEC-03's project configuration.

**Security.**
- Agents reach this module only through `propose` (SPEC-07) and reports (SPEC-06), which create drafts with source `task output` and trust `trusted`. Agent output is always reviewed because every ChangeSet needs approval in M1.
- Intake drafts (SPEC-08's `delivery_bypass` finding) are `untrusted`, and so is their approval.
- Bundle files come from the operator, the trusted source. They are parsed with the safe loader and validated like any draft.
- Every answer records its channel and answerer from the authenticated session (SPEC-10).

**Make and prove.** No subjects are produced. ChangeSets are approved by a person, never by the agent that proposed them.

**Fitness functions.**
- FF-08 is added (REQ-0420). `scripts/ff/single_writer.py` reads a registry of guarded columns and tables, each with the one function allowed to write it, declared beside the transition functions with `@transition_function("<lifecycle>")` and `@single_writer("<table>")`. It parses each kernel module's code and fails when an SQL string that updates a guarded column, or inserts into a guarded table, sits outside its registered function. This specification registers the `intent`, `change` and `decisions` columns; SPEC-06 and SPEC-08 register theirs.
- FF-07 covers the three schemas.
- FF-09: no stored readiness, staleness or project pause here.
- `make gen` gains SQL enum generation, checked for drift by FF-02.

## 6. Decisions

DEC-0401: M1 imports items from a YAML bundle of kind, ID, title and fields · It is generic, validates against kind contracts with no factory code, and SPEC-11 adds Markdown import once rendering round-trips · Rejected: parsing the fixture's Markdown in M1 (needs SPEC-11's round-trip rules first); a factory-specific importer (kernel code would need a factory format).
DEC-0402: M1 accepts only `unaffected` verdicts, given by the operator on the approval card · One round is then a fixed point by definition, so I-13 holds without the multi-round machinery of SPEC-12 and SPEC-16 · Rejected: refusing every ChangeSet that reaches an existing item (M1-02 needs a criterion changed after its evidence passed); building amendments now (scope that M1 does not use).
DEC-0403: Continuations start from the `decision.answered` event through SPEC-03's dispatcher · The answer and its event commit together, so a crash between answer and start loses nothing, and the dispatcher's workflow ID makes the start exactly once · Rejected: starting the workflow from the REST handler after commit, with a recovery sweep (a second mechanism that does the same thing).
DEC-0404: Every item has a presentation field `title` · Titles may change without staling anything (Concepts, "Identity"), and every page and prompt needs one · Rejected: per-kind title fields (each factory would pick its own).
DEC-0405: Kind lifecycle states are constrained through a `lifecycle_states` table rewritten from the registries at start, and kernel lifecycles through generated PostgreSQL enums · Factory kinds are known only at load, so their states cannot be migration-time enums; the table gives the same database guarantee · Rejected: one text column without a constraint (FF-08 needs the database to refuse an undeclared state).
DEC-0406: Other modules request drafts through one event contract owned here · `work` and `delivery` may not import `change`, and consuming their own events would make this specification depend on later ones · Rejected: widening the module map (a module-map change needs a record and an architecture review); one event type per emitter consumed here (a specification cycle).
DEC-0407: The bases of a re-walked ChangeSet are recorded on its walk round, never on its draft · Drafts are insert-only and keep what was proposed against what, which provenance needs; the round is already the insert-only record of each walk, so the latest round's bases are what the approver saw · Rejected: a new draft superseding the old one (breaks the one-request, one-draft rule on client keys and the provenance link to the original request); updating the draft's bases in place (drafts would no longer record what was drafted).

## 7. Tickets and acceptance criteria

TKT-0401: Items, revisions, edges, lifecycles, ID allocation, rendering, `core` kinds · implements REQ-0401 to REQ-0408 · depends on TKT-0302, TKT-0201 · paths `packages/grindstone/src/grindstone/intent/`, `packages/grindstone/src/grindstone/contracts/intent.py`, `packages/grindstone/tests/intent/`.
TKT-0402: Decision records, kinds, answers, continuations · implements REQ-0416 to REQ-0419 · depends on TKT-0304 · paths `packages/grindstone/src/grindstone/decisions/`, `packages/grindstone/src/grindstone/contracts/decisions.py`, `packages/grindstone/tests/decisions/`.
TKT-0403: Bundle import, ChangeDrafts, walk, rules, approval, apply · implements REQ-0409 to REQ-0415 · depends on TKT-0401, TKT-0402 · paths `packages/grindstone/src/grindstone/change/`, `packages/grindstone/src/grindstone/contracts/change.py`, `packages/grindstone/tests/change/`.
TKT-0404: SQL enum generation for kernel lifecycles · implements REQ-0405 · depends on TKT-0401 · paths `scripts/gen_sql_enums.py`, `Makefile`, `tests/fitness/`.
TKT-0405: FF-08 single-writer check with fixtures · implements REQ-0420 · depends on TKT-0401 · paths `scripts/ff/single_writer.py`, `tests/fitness/`, `Makefile`.
TKT-0406: `change.draft_requested` contract and its consumer · implements REQ-0421 · depends on TKT-0403, TKT-0304 · `change` paths.

AC-0401-1: A revision cannot be updated or deleted (the database refuses it), and every revision has non-null provenance with author kind, author and reason · verifies REQ-0401 · integration · `test_revisions_are_immutable_with_provenance`.
AC-0402-1: No function outside apply in `intent` writes `item_revisions` or `items.current_revision` (FF-08 fixture), and a direct call to the revision writer outside an apply transaction is refused · verifies REQ-0402 · contract · `test_only_apply_writes_revisions`.
AC-0403-1: A revision of a fixture kind with two `ref` fields yields exactly one edge per referenced ID, typed by the field's edge, and changing a reference in a later revision changes only that revision's edges · verifies REQ-0403 · unit · `test_edges_derived_from_references`.
AC-0404-1: A draft referencing `N-9`, which neither exists nor is in the draft, is refused with `reference_unresolved` naming the field; one that creates `N-9` in the same draft is accepted · verifies REQ-0404 · unit · `test_unresolved_reference_refused`.
AC-0405-1: For a fixture lifecycle, a transition not in the table, or by a writer the table does not name, is refused with `transition_illegal`; each accepted one is recorded with writer and cause; the item's revision hash is unchanged by any transition · verifies REQ-0405 · property · `test_lifecycle_transitions_guarded`.
AC-0406-1: Items created by apply are in their kind's initial state · verifies REQ-0406 · unit · `test_initial_state_on_apply`.
AC-0407-1: Allocating `FND` IDs concurrently in one project yields distinct, increasing numbers; an imported ID that fails its pattern is refused with `id_invalid`, and one already used by another kind with `id_taken`; after importing `FND-7`, allocation never returns 7 · verifies REQ-0407 · integration · `test_id_allocation_and_validation`.
AC-0408-1: `render` of a fixture revision contains the ledger header, `# N-3 — <title>`, each semantic field, and each reference as `[[ID]]` · verifies REQ-0408 · unit · `test_render_item_markdown`.
AC-0409-1: A bundle of three valid fixture items becomes one ChangeDraft with source `operator`; importing it again with the same client key returns that draft; a bundle with two invalid items is refused listing both items' errors; a bundle with a YAML object tag is refused · verifies REQ-0409 · unit · `test_bundle_import`.
AC-0410-1: Drafts from each source record source, trust, bases and provenance, and a draft from intake has trust `untrusted` · verifies REQ-0410 · unit · `test_draft_records_source_and_trust`.
AC-0411-1: Over generated graphs (property test), the walk lists exactly the current items outside the set with a `review` edge to a changed item, never a `notify` source as needing a verdict, and is a fixed point when every listed item has `unaffected` · verifies REQ-0411 · property · `test_walk_lists_review_dependents`.
AC-0412-1: Importing a fixture bundle raises one open `approval` decision whose payload lists every revision and reached item; an intake draft's approval carries the `untrusted` flag · verifies REQ-0412 · integration · `test_import_raises_approval`.
AC-0413-1: An approve answer missing a verdict or a reason for a reached item is refused with `verdict_missing`; `reject` moves the ChangeSet to `rejected` and writes no revision · verifies REQ-0413 · unit · `test_approval_answers_need_verdicts`.
AC-0414-1: Approving the imported bundle writes every revision, edge and initial state and emits `item.revised` per item and `changeset.applied` in one transaction; a fault injected before commit leaves no trace · verifies REQ-0414 · integration · `test_apply_is_atomic`.
AC-0414-2: Two ChangeSets on the same item, approved concurrently, apply one after the other; the second, with a moved base, is re-walked · verifies REQ-0414 · integration · `test_apply_serialized_per_project`.
AC-0415-1: A ChangeSet whose base moved is never applied on its old approval: the approval is superseded, the new one shows diffs against the new base (including the reversal of the other ChangeSet's change), and answering it applies the ChangeSet over the new base; the M1 rules and the apply check read the latest round's bases, and a base that moves again asks again · verifies REQ-0415 · integration · `test_moved_base_asks_again`.
AC-0420-1: FF-08 passes on the kernel, and fixtures that update a guarded lifecycle column, or insert into a guarded table, outside the registered function fail it · verifies REQ-0420 · contract · `test_ff08_single_writer`.
AC-0421-1: A `change.draft_requested` event from a task's collect drafts one ChangeSet with source `task output`; one from a bypass drafts one `untrusted` ChangeSet with a high-severity `delivery_bypass` finding whose approval is flagged `untrusted`; each, emitted twice with its client key, drafts once · verifies REQ-0421 · integration · `test_change_consumes_draft_requests`.
AC-0416-1: Raising a decision without a recommendation, or with a flag in its payload instead of from the kernel, is refused · verifies REQ-0416 · unit · `test_decision_needs_recommendation`.
AC-0417-1: Answering a superseded decision fails `decision_superseded`; answering with a stale context hash fails `context_changed`; an accepted answer records answerer, channel and time; the same answer repeated with its client key returns the original result, and with another key fails `decision_closed` · verifies REQ-0417 · unit · `test_answer_guards`.
AC-0418-1: Killed after an answer commits and before its continuation starts, the process on restart runs the continuation once; answering twice runs it once · verifies REQ-0418 · crash-and-resume · `test_continuation_exactly_once`.
AC-0419-1: Superseding a decision from a module other than its raiser is refused; a superseded decision and its replacement are both readable · verifies REQ-0419 · unit · `test_only_raiser_supersedes`.

## 8. Test plan

- Unit, with fixture kinds in the `notes` style: AC-0403-1, AC-0404-1, AC-0406-1, AC-0408-1, AC-0409-1, AC-0410-1, AC-0413-1, AC-0416-1, AC-0417-1, AC-0419-1.
- Property: AC-0405-1, AC-0411-1.
- Integration, on real Postgres and DBOS: AC-0401-1, AC-0407-1, AC-0412-1, AC-0414-1, AC-0414-2, AC-0415-1, AC-0421-1.
- Crash-and-resume: AC-0418-1.
- Contract (FF-08 fixtures): AC-0402-1, AC-0420-1.

## 9. Open items and risks

OQ-0401: Should a bundle be able to retire an item in M1? · Default: no; retirement is a lifecycle transition through a ChangeSet that SPEC-16 adds with `invalidate` verdicts · Resolved by SPEC-16.
OQ-0403: Should `core.interface.contract` be structured content from the start? · Default: no; it is text holding JSON in M1, and SPEC-11 validates it against the shape's schema without changing its type, so no `core` field changes type later (I-18) · Resolved by SPEC-11.
OQ-0402: Is `l2` the right seed class for kernel `approval` and `escalation`? · Default: as the SDLC table in the Factories tab uses them; nothing answers by policy before SPEC-25 · Resolved by SPEC-15.

Risks mitigated: intent changing without review (only apply writes revisions; every ChangeSet approved in M1); a dependent left unexamined (one-round walk with mandatory verdicts); lost or double continuations (answer and event in one transaction, ID-keyed start).
Risk added: with only `unaffected` verdicts, the operator must reject and redraft when an item is affected. Mitigation: M1's changes are hand-written imports; SPEC-16 adds amendments at M3.

## 10. Rollout

The first migrations create schemas `intent`, `change` and `decisions`. `make gen` gains the SQL enum generator. The testbed's fixture intent is rewritten as an item bundle by SPEC-09. No stored data exists before M1.
