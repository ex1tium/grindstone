# Project Grindstone — Foundation v4.6

18 October 2026 · @Matti · Repository copy of the Foundation doc (https://claude.ai/code/artifact/5bf48b42-cfd0-4721-b97e-2cc88dd972c5), maintained here from v4.2 on. The diagrams are not reproduced; each is replaced by a caption stating what it shows, and nothing in the diagrams adds a commitment the text does not state.

Grindstone is a self-hosted orchestrator that makes agent work trustworthy enough to delegate: intent is typed and versioned, every result is proven by someone other than its maker against the exact intent it claims to satisfy, and a person decides only what a person should.

## How to read this set

This set is the foundation planning agents write specifications from. It fixes what is expensive to reverse — the product's scope, the system's structure, the kernel's concepts and their contracts, the boundary between kernel and factories, invariants, protocols, data ownership, the first factory's workflows and the decisions behind all of them — and leaves how each part keeps its promises to the specification that builds it. It is complete on its own: nothing outside it is needed to plan or build the MVP.

| Tab | Holds | Changes |
| --- | --- | --- |
| Product (this tab) | Goal, users, promise, the universal loop, factories in scope, quality bars, non-goals, MVP outcome, success measures, glossary | At milestone reviews |
| Architecture | Ranked quality goals with measurable scenarios, constraints, context, containers and deployment, architectural style, invariants, runtime views, threat model, failure model, operations, fitness functions | Only through a decision record |
| Concepts | The kernel's seven concepts and its substrate, field by field: Item, Capability, Station, Task, Check, ChangeSet, Decision, blobs, subjects, delivery, interfaces, cooperation | Only through a decision record |
| Components | Module map, a specification per module and per process, interfaces, data model, contracts and versioning, error model, configuration, testing strategy | Only through a decision record; details in specs |
| Factories | What a factory is, templates, make and prove, interface items, the complete software-development factory, sketches of later factories | SDLC factory per milestone; others when built |
| Decisions | One record per hard-to-reverse choice | Append-only once M0 starts |
| Roadmap | Milestones with exit criteria, spikes, open questions, spec map, ownership, releases, risks | Each milestone's detail is set when it starts |
| Planning playbook | How specifications are written, validated and kept consistent with this set | Rarely |

**Authority.** Product, Architecture, Concepts, Components and Factories state commitments; Decisions explains them; Roadmap orders the work; the playbook governs specifications. When a specification and this set disagree, this set wins until a decision record changes it. Names and values written as examples inside a commitment — field names, caps, defaults — are seeds the implementing specification owns; the meaning they carry binds.

**Identifiers.** Each is unique, typed and never reused.

| Prefix | Means | Defined in |
| --- | --- | --- |
| `I-nn` | Invariant | Architecture |
| `QG-n`, `QS-nn`, FF-nn | Quality goal, quality-attribute scenario, fitness function | Architecture |
| `K1`–`K4`, `S1`–`S6` | Kernel and SDLC scenarios | Architecture, Factories |
| `ADR-nn` | Decision record | Decisions |
| `Mn`, `Mn-nn` | Milestone, exit criterion | Roadmap |
| `SPK-n`, `Q-n` | Spike, open question | Roadmap |
| `SPEC-nn` | Specification | Roadmap |
| `Rn` | Release after the MVP | Roadmap |

Item kinds are namespaced: `core.*` belongs to the kernel, `sdlc.*` to the software-development factory, and each later factory gets its own namespace.

## Product goal

**Grindstone makes agent-driven work trustworthy enough to delegate.** A person states intent; agents do the work; Grindstone keeps the intent typed and versioned, proves every result independently against the exact intent it claims to satisfy, feeds what the work discovers back into the intent, and asks the person only what only a person should decide.

Its first and main use is software: an **agent-driven software development loop (ASDLC)** that takes a repository from an idea to merged pull requests, with the specification and the code moving together. Grindstone builds that loop on a small domain-neutral **kernel**, so the same guarantees — provenance, freshness, independent proof, reviewed change, typed decisions, durable and bounded execution — serve other kinds of agent work through **factories**: reverse engineering, testing and security, CAD and 3D, PCB and hardware, game development and in-house domains. Within one project, factories' specialists switch modes, consult each other and hand off work without talking to each other directly and without anyone tracking it by hand.

In one sentence: **any agent work, in any domain Grindstone has a factory for, ends in results a person can trust without having watched it happen.**

Three properties make that possible, and every part of the design serves one of them:

| Property | Means | Where it lives |
| --- | --- | --- |
| **Typed, versioned intent** | Everything agreed on is an item with a stable ID and a content hash; it changes only through a reviewed ChangeSet | Concepts: Item, ChangeSet |
| **Independent, fresh proof** | Work is done only when someone other than its maker has proven it against the exact inputs, subject and environment; proof goes stale on its own when any of those change | Concepts: Check; Factories: make and prove |
| **Bounded, recorded authority** | People answer typed decisions with a recommendation in front of them; policy answers only what they allowed, and every answer can be reverted | Concepts: Decision |

## Problem and users

**User.** One operator — a developer, tech lead or technical specialist — who runs Grindstone on their own infrastructure for their own repositories and targets, uses their own Claude subscription or API keys, and wants agents to do most of the work while they keep control of what gets built and what counts as done. Teams and multiple operators are out of scope for the MVP; nothing in the design prevents them later.

**What goes wrong with agent-driven work today, in any domain:**

- **Intent is lost.** Requirements, hypotheses and goals live in prompts and chat history. Nothing records which version of a requirement a result was built against, so intent and output drift apart.
- **Agents grade their own work.** "Done" or "found" means an agent said so. There is no independent, repeatable evidence tied to the exact intent and the exact subject — commit, binary, model or board.
- **Discoveries don't flow back.** When work reveals a gap or conflict, it is fixed locally and forgotten; the specification stays wrong and the next agent repeats the mistake.
- **Change is unsafe.** Changing a requirement or an interface gives no view of what else it affects, which evidence is now meaningless, or which running work builds on the old version.
- **Expertise is siloed or chaotic.** One agent tries to be expert at everything, or several agents chat with each other with no record, no budget and no clear end.
- **Supervision does not scale.** The person either babysits every session or reviews large outputs with no trace back to intent.
- **Agent-run code is trusted too much.** Agents run with the same credentials that ship results and set status; untrusted inputs — issues, binaries, documents — reach them unmarked.

**Jobs the operator hires Grindstone for:**

1. Turn an idea into a product definition and a specification I have actually agreed to.
2. Get approved work done by agents without watching them — code first, other domains as factories arrive.
3. Know at any moment which requirements or findings are proven, by which evidence, against which subject.
4. Change my mind — or let the work change it — and see and approve every consequence before it lands.
5. Let agents bring in the right specialist at the right moment, within limits I set, with everything they exchange on the record.
6. Delegate more decisions over time, with every delegated answer recorded and reversible.

## Promise and the universal loop

**Promise.** Give Grindstone an idea. It interviews you, drafts a product definition and a specification for you to approve, breaks it into tickets, has coding agents implement them — calling security, testing or other specialists when they need them — folds what they discover back into the specification, and lets a pull request merge only when independent evidence shows every acceptance criterion holds at that exact commit. The same promise, with other words for intent, subject and delivery, holds for every factory.

**The universal loop.** Every factory runs the same five beats; the kernel owns the beats and the factory names them.

| Beat | Kernel concept | Software development (MVP) | Reverse engineering (R1) |
| --- | --- | --- | --- |
| State intent | Item, ChangeSet, Decision | Product, features, specifications, requirements, criteria, tickets | Target, questions to answer, scope of analysis |
| Do the work | Task in work mode, with consult and delegate | Implementer in a worktree, consulting security or testing specialists | Static analyst driving Ghidra and rea, delegating a parser to SDLC |
| Prove it | Check, by someone other than the maker | CI suite, test reviewer, code and security reviewers | Reproduction on the pinned binary, a second tool, a reviewer |
| Learn and change | ChangeSet from findings and learnings | Findings amend the specification; learnings join future context | Findings revise the report and interface items |
| Deliver | Decision, then a delivery adapter | Pull request and merge | Report export; interface published to other factories |

The full ASDLC loop, with its diagram and commands, is in the Factories tab.

**Division of labour.** Every part of the system preserves it:

- **You decide intent.** Every specification, every finding that changes intent, every change of scope takes effect only through an approval you give, or one your autonomy policy may give and you can revert.
- **Agents propose.** They draft, make, report, ask and delegate — always through typed reports, proposals and decisions; never by writing intent, setting status or shipping.
- **The kernel applies.** Grindstone turns accepted proposals into recorded revisions, one atomic change at a time, after showing everything each change affects.
- **Only independent evidence closes work.** A task is done when someone other than its maker — a credential-less check station, a different specialist, or you — has proven its output against the exact intent revisions and subject.
- **Specialists cooperate through the ledger.** Switching mode, consulting and delegating are recorded, bounded tasks; results cross only as pinned items and files.

## Factories in scope

A factory packages one domain: its item kinds, specialists (capabilities), workflows (templates), proofs (check methods), subjects, delivery and interfaces. The kernel ships with no domain of its own.

| Factory | Status | What it gives the operator |
| --- | --- | --- |
| `sdlc` — software development | **MVP**, built from M1 | The full ASDLC loop: `/init`, `/discover`, `/plan`, `/implement`, `/patch`, `/repair`; implementer, spec author, auditor, planner, test, code, security and impact reviewers, advisor; GitHub pull requests |
| `notes` — fixture | **MVP**, test only | A code-free factory proving the kernel is domain-neutral (M2-05); never offered to users |
| `re` — reverse engineering, static | R1 | Analysis of trusted binaries with Ghidra headless, rea and in-house tools; reproducible findings; reports; code delegated to SDLC |
| `qa` — testing and security campaigns | Sketched | Test plans, threat models and campaigns that outlive tickets; hostile targets need T2 stations (R3) |
| `cad`, `pcb` — mechanical and electronic design | Sketched | Models, schematics and boards proven by geometry checks, ERC/DRC and reviews; bench work needs T3 stations (R4) |
| `game` — game development | Sketched | Mechanics, levels and asset specs; builds proven by play tests; GPU work needs T3 stations (R4) |

**Cooperation in the MVP.** Within SDLC, the implementer loads skills, consults the security or test specialist mid-task, and the security reviewer becomes a required prover by path policy (S5). Cross-factory delegation exists in the kernel from M3 and is exercised with the fixture factory; its first real use is RE delegating code to SDLC in R1 (S6).

**Computer use and hardware** are the long-term direction: T3 stations — a full VM with passed-through devices — where agents operate desktop tools and benches under approved runbooks. They arrive as new stations and capabilities, not as a new core.

## Quality bars and non-goals

The quality bars apply to Grindstone's own code and to everything Grindstone produces for a project, in every factory. The Architecture tab turns them into ranked quality goals with measurable scenarios, and into invariants.

| Bar | Means |
| --- | --- |
| Correctness | Each requirement is one testable statement with a stable ID; each acceptance criterion names the requirement it verifies and how it is verified |
| Traceability | Every relation is a typed reference; nothing references a missing item; nothing is left uncovered; every revision records who or what changed it and why |
| Freshness | Evidence counts only for the input hashes, subject version and environment it was produced against; staleness is computed, never stored |
| Durability | A workflow killed at any step resumes without duplicate side effects; every external action is idempotent |
| Type safety | One source of truth for types; everything else is generated and drift-checked in CI; breaking schema changes need a version bump and an upgrade path |
| Reversibility | Every applied change can be undone by another recorded change; actions that cannot be are marked and asked |
| Independence | Nothing proves its own work: makers and provers are always different |
| Simplicity | Fewest moving parts, least custom code: configuration beats code, off-the-shelf beats glue, glue beats in-house, and every new component states its reason. In factories, data beats code |

**Non-goals for the MVP.** Each is a deliberate exclusion; reopening one needs a decision record.

- More than one operator: no multi-user or multi-tenant operation, and no offering of Claude subscription login to anyone else.
- Any git host other than GitHub; any workflow engine other than DBOS.
- Kubernetes, message brokers, microservices, a separate vector or graph database, a factory marketplace.
- Merges or deliveries that bypass Grindstone's verification and delivery decision.
- Factories beyond SDLC and the test fixture; installing factories as separate packages (R1).
- Agents talking to each other directly, or model-based routing between specialists.
- Station tiers above T1: per-run microVMs (R3), full VMs, device passthrough and computer use (R4).
- Repository snapshot and restore, vector search, autonomy L3 and auto-merge, the pi agent, baseline generation from an existing codebase (all R2).
- Indexing source code for retrieval; agents search the repository themselves.
- Agent-quality metrics and capability evaluations; structured logs, traces and cost records are in scope.
- Spec Kit and Obsidian exports, web-research capabilities, merging and splitting items, item-kind inheritance, signed snapshots.

## MVP outcome and success measures

**The MVP is done when** an operator can take a new or an existing GitHub repository from an idea to merged pull requests through Grindstone — discovery, planning, breakdown, execution by Claude Code, with further agents added by configuration, with specialists consulted and proving as needed, verification and merge — where every merged change traces to approved requirement revisions with fresh, independent evidence, every change of intent was shown in full before it applied, and the operator's time goes to decisions rather than supervising sessions; **and** the kernel has been shown to carry a second, code-free factory with no change. Grindstone builds itself from the end of M1, so its own repository is the first and hardest test project.

**Success measures.** Grindstone computes each from its own records. Targets are initial hypotheses, confirmed or reset at the M3 review from measured baselines (Q-8).

| Measure | Definition | Initial target at MVP |
| --- | --- | --- |
| Delegation rate | Share of merged ticket PRs with no commit authored by a person on the branch | ≥ 60% on Grindstone's own repository |
| Evidence integrity | Share of merges whose every criterion had fresh, independent, passing evidence at the merge commit | 100%; zero bypassing merges where the remote enforces the gate, and every bypass detected and counted where it does not (ADR-40) |
| Regression catch | Share of broken proven criteria found by re-checks or the regression sweep before a person reports them | ≥ 90% |
| Decision load | Decisions a person answers per merged ticket, and median wait for an answer | Baseline at M3; falling month over month once L2 is available (M5), with no tripwire trips caused by policy answers |
| Lead time | Median time from specification approval to all its tickets merged | Baseline at M3; trend tracked |
| Governed share | Share of merged PRs on the default branch that are Grindstone ticket PRs | ≥ 90% on Grindstone's own repository |
| Cooperation value | Share of consults and delegations whose output the caller used (cited in its report or pinned), and their share of total spend | Baseline at M3; used share ≥ 70% |
| Kernel stability | Kernel changes required by factory work after M2 | Zero breaking SDK changes; every additive change recorded |

The measures judge Grindstone, not agents: agent-quality metrics stay a non-goal.

## Glossary

Every term the set uses with a specific meaning. Specifications use these words exactly as defined here.

| Term | Meaning |
| --- | --- |
| ACP | Agent Client Protocol: how the agent host talks to each agent runtime (Claude Code in the MVP; others by configuration) |
| Agent host | The process on an agent station that runs agent sessions; built on `@ahpd/sdk` |
| AHP | Agent Host Protocol: how the UI and VS Code attach to live agent sessions |
| Artifact | A container kind with one header item and member items, such as a specification |
| ASDLC | Agent-driven software development loop: the SDLC factory's workflow |
| Autonomy level | L0–L3: how much the project's policy may answer on the operator's behalf |
| Blob | An immutable file in the content-addressed store, identified by SHA-256 |
| Capability | A specialist defined as data: prompt, agent, skills, toolbox, workspace mode, permissions, offers |
| ChangeSet | The only way intent changes: drafted, walked for impact to a fixed point, approved, applied atomically |
| Check | One recorded attempt to prove a target item holds for a subject, by someone other than its maker |
| Check station | A station that runs mechanical checks with no credentials; the `runner` container in the MVP |
| Consult | A read-only child task answering a question; its answer is a suggestion and is cached |
| Context pack | What a task run sees: pinned items, principles, learnings, interfaces and skills, recorded by hash |
| Control plane | The `grindstone` process: kernel, factories, workflows, APIs, delivery |
| Decision | A typed question only a person or approved policy may answer, with a recommendation |
| Delegate | A child task in work mode, in any enabled factory, with its own checks, within the depth and live-children caps |
| Delivery adapter | A factory component that ships verified subjects outside Grindstone after a decision |
| Evidence | The immutable record a check produces |
| Factory | A package that gives the kernel one domain: kinds, capabilities, templates, methods, subjects, adapters, interfaces |
| Finding | A `core.finding` item: something noticed that may change intent |
| Freshness | Whether evidence still holds: computed by comparing its input hashes, subject version and environment with current values |
| Interface item | A `core.interface` item: a contract between two parts of a project, with a provider and consumers |
| Item | A typed, hashed, versioned unit of intent or knowledge |
| Kernel | The domain-neutral core: concepts, invariants, services and the SDK |
| Lane | A queue on an agent station: writing (one at a time) or read-only (small concurrency) |
| Limits | Structural guards against runaway work that do not depend on a task's size: delegation depth and live children, a liveness timeout, a consult ceiling, and an optional project cap. Cost is recorded, never gating (ADR-37) |
| Make and prove | The rule that whoever makes a subject never produces the evidence that gates it |
| Need | A namespaced label for what a task or agent asks for; capabilities offer needs |
| Operator | The one person who runs Grindstone and answers its decisions |
| Project | One ledger: items, tasks, evidence, decisions and enabled factories for one body of work |
| Report | The typed result that ends each turn: done, blocked, failed, or waiting (set by a suspending tool) |
| Revision | An immutable version of an item, with provenance |
| Skill | A Markdown instruction pack, optionally with tools, that a capability may load mid-session |
| Station | Where work or checks run, with an isolation tier T0–T3 |
| Subject | The versioned thing a check proves and delivery ships: a commit, a blob, a blob set, an item revision |
| Task | One unit of work with pinned inputs, an output contract, a check plan and limits |
| Task run | One attempt at a task, in a fresh workspace |
| Template | A factory workflow: a bounded graph of six step types, exposed as a command |
| Tier | Station isolation level: T0 read-only, T1 container, T2 microVM, T3 full VM or hardware |
| Tripwire | Conditions that drop a project's autonomy to L1 until the operator restores it |
| Workspace | A task run's private working directory on its station |


# Architecture

The system-level design: what Grindstone must be good at, the parts it runs as, the rules no part may break, and how it behaves when things go wrong.

## Quality goals

Seven goals, ranked. When two conflict, the higher one wins. Each is made concrete by quality-attribute scenarios with a measurable response; specifications turn scenarios into acceptance criteria and the Roadmap's exit criteria prove them.

| # | Goal | What it protects |
| --- | --- | --- |
| QG-1 | **Evidence integrity** | "Done" means the same thing in every factory and cannot be forged by the work it judges |
| QG-2 | **Durability** | Crashes cost time, never correctness |
| QG-3 | **Containment** | Work content is untrusted and cannot reach Grindstone's authority |
| QG-4 | **Traceability and safe change** | Every change shows its full consequences before it lands |
| QG-5 | **Bounded cost** | Agent work, including cooperation, cannot loop, stall or fan out without limit, and every cost is visible |
| QG-6 | **Operability and simplicity** | One operator can install, run, explain and recover the whole system |
| QG-7 | **Generality without kernel change** | New domains arrive as factories, not as kernel edits |

Generality ranks last on purpose: when making the kernel more general would make the MVP harder to run, explain or trust, the MVP wins and the generality waits for a second real factory.

**Quality-attribute scenarios.** Source and stimulus, the environment it happens in, the required response, and how the response is measured.

| ID | Goal | Stimulus | Environment | Response | Measure |
| --- | --- | --- | --- | --- | --- |
| QS-01 | QG-1 | An implementer writes a test that always passes and reports done | Normal operation | The task stays in verifying; the test reviewer fails the weakened test | 0 tasks reach done on maker-produced evidence (M1-07) |
| QS-02 | QG-1 | A criterion's text changes after its evidence passed | Task done, PR open | Evidence is stale on the next read; the verification status returns to pending | Staleness visible within one read; no stored flag (M2-02) |
| QS-03 | QG-1 | Agent-written code tries to set the GitHub status or push | Inside an agent or check station | The attempt fails: no credential is reachable from the station | 0 credentials readable from stations (M1-05) |
| QS-04 | QG-2 | The control plane is killed between an external action and its record | Any workflow step | On restart the step finds the effect by its idempotency key and records it | 0 duplicate sessions, pushes, PRs, statuses, blobs or children (M1-04) |
| QS-05 | QG-2 | The host restarts mid-turn | Agent session running | The run continues in a new session from its workspace, or fails with `host_lost` and retries | No lost reports; at most one retry per host loss |
| QS-06 | QG-3 | A repository contains a malicious hook or settings file | Copy-back and delivery | Hooks never run in the control plane; settings never reach a session | Fixture attack fails in CI (M1-05) |
| QS-07 | QG-3 | Imported content (issue, review comment, binary) contains instructions | Intake | Marked `untrusted`; derived ChangeSets wait for a person at every autonomy level | 0 untrusted ChangeSets applied by policy (M3-04) |
| QS-08 | QG-4 | The operator edits a requirement that three specifications and five tickets depend on | Work in progress | Every affected item is listed with a verdict before apply; only dependent checks re-run | Walk reaches a fixed point; re-runs equal the dependency set (M2-03, M3-01) |
| QS-09 | QG-4 | An applied change turns out wrong | Next day | A revert ChangeSet restores the previous revisions, walked like any change | Revert applies or raises `revert_conflict`; nothing deleted (M3-03) |
| QS-10 | QG-5 | An agent delegates in a loop | Mid-task | The third level of delegation or the fifth live child returns a structured tool error; the agent continues or reports `blocked` | 0 trees exceed depth 2 or the live-children cap (M3-05) |
| QS-11 | QG-5 | The same consult is asked twice with unchanged inputs | Same project | The second answer comes from the cache | Second ask costs no agent run |
| QS-12 | QG-6 | A new operator installs Grindstone | Fresh host | `docker compose up` plus documented secrets runs the walking skeleton | Install to first verified PR in ≤ 1 hour following the runbook (M3-07) |
| QS-13 | QG-6 | The operator asks why a task is blocked | Any time | The UI shows the blocking decision, limit or check with its reason | Answer reachable in ≤ 2 clicks from the task |
| QS-14 | QG-7 | A new factory with kinds, a capability and a template is installed | Kernel at M2 or later | It runs end to end without kernel edits | 0 kernel files changed (M2-05) |
| QS-15 | QG-5 | An agent session stops making progress, or a consult runs far longer than expected | Agent session running | A run with no activity for the liveness timeout fails `stalled`; an open kernel tool call never counts as inactivity; a consult past its ceiling suspends the caller's turn and raises an escalation | Stall or ceiling acted on within one minute of the limit; 0 waiting callers failed as stalled (M3-05) |

## Constraints, assumptions and capacity

**Constraints** are fixed for the MVP; each has a decision record.

| Constraint | Record |
| --- | --- |
| One operator, self-hosted on one machine with Docker Compose | ADR-01, ADR-36 |
| Python for the control plane, kernel and factories; TypeScript only for the agent host and the UI | ADR-01, ADR-06, ADR-15 |
| PostgreSQL holds every record; one content-addressed volume holds files; DBOS Transact runs every workflow | ADR-02, ADR-03, ADR-04 |
| Agents run behind an AHP host over ACP and reach Grindstone only through MCP; Claude Code is the only real agent until the operator adds another | ADR-15, ADR-16, ADR-18, ADR-41 |
| The UI is a static SvelteKit app; VS Code and the operator plugin use the same API | ADR-06 |
| GitHub is the only git host and the SDLC factory's only delivery target | ADR-27 |
| Every dependency is the latest stable release compatible with the other pins, pinned exactly, with each exception's constraint recorded; images by digest; upgrades are deliberate commits that pass CI; versions are resolved at M0 from primary sources | ADR-01, ADR-46 |

**Assumptions.** Each is checked at a named point; if one fails, the named fallback applies.

| Assumption | Checked by | If false |
| --- | --- | --- |
| An AHP host built on `@ahpd/sdk` can run Claude Code sessions with a per-session MCP server | SPK-1 | A minimal host behind the same control API; live sessions in the browser move to M4 |
| DBOS survives kills during steps, waits and child workflows without duplicate effects | SPK-2 | Fix in DBOS usage before M1 specs; no alternative engine in the MVP |
| Agents tolerate an MCP tool call held open for several minutes | SPK-5 | Consults park the task and resume it with the answer |
| One machine with 8 cores, 32 GB memory and 500 GB disk is enough for the MVP envelope below | M3 review | Raise the documented minimum; no architectural change |

**Capacity envelope.** The MVP is designed and tested for these figures; the operations view shows each, and exceeding one is a warning, not a failure.

| Dimension | MVP envelope |
| --- | --- |
| Projects per instance | 10 active |
| Items per project | 20,000 live, 200,000 revisions |
| Concurrent agent sessions | 1 writing + 4 read-only per agent station |
| Concurrent check jobs | 1 per check station |
| Task runs per day | 500 |
| Blob store | 200 GB, single blob ≤ 2 GB |
| Impact walk | ≤ 2 s for a change touching 500 items |
| Freshness read for one task | ≤ 100 ms |
| UI event latency (state change to browser) | ≤ 1 s |

## System context

Grindstone runs on one host the operator controls. Everything it trusts is inside that host; everything it talks to outside is named here, with what crosses the boundary.

*Diagram (not reproduced): system context — one operator and three external services (GitHub, model providers, package registries) around the one host; the table below states everything it shows.*

| External party | What crosses | Direction | Credential | Trust |
| --- | --- | --- | --- | --- |
| Operator | Commands, decision answers, edits to intent, steering prompts; views of every record and live session | Both | Operator login (password + session); per-client tokens for VS Code and the plugin | Trusted |
| GitHub | Pushes, pull requests, verification status, comments — out. Repository state, PR state, review comments, issues, check results — in | Both | GitHub App installation token, held only by the control plane | Content coming in is untrusted |
| Model providers | Prompts and tool results out; model output in | Both | Claude subscription token or API key (keys for further providers when added) — held by the agent station, readable by agents | Output is untrusted work content |
| Package registries | Dependency downloads for builds and tests | In | None | Untrusted; reached only from stations |

Nothing else is contacted. Later factories add their own external parties (a tracker, a fab house) only through delivery adapters and station toolboxes, each declared in the factory manifest and granted per project.

## Containers and deployment

The control plane is one Python process holding the kernel and every installed factory. Work runs on **stations**: in the MVP one agent station and one check station. Both are thin glue around off-the-shelf parts (ADR-01, ADR-17). Authority — the database, delivery credentials, signing keys — lives only in the control plane.

*Diagram (not reproduced): containers — one control plane, two stations and one database, with the four volumes; the tables below state everything it shows.*

| Container | Responsibility | Holds secrets | Can reach |
| --- | --- | --- | --- |
| `grindstone` | Kernel, factories, workflows, REST API and static UI, event stream, kernel MCP server, delivery adapters, private clones, blob store, search | GitHub App key, database password, host control and event-signing keys, MCP token signing key, operator session key | `postgres`, the agent station's control API, GitHub |
| `agent-host` | AHP host for every agent session; ACP agents run as child processes under their own Unix user; two lanes | Model credentials (readable by agents); host tokens (readable only by the host process) | The control plane's MCP and event endpoints; model providers; package registries |
| `runner` | Runs mechanical checks on a materialized subject, one job at a time, in the project's declared image | None | Package registries only; talks to the control plane only through job files |
| `postgres` | All records, DBOS system tables, blob metadata, full-text index | Its data | Nothing |

| Volume | Mounted in | Holds |
| --- | --- | --- |
| `blobs` | `grindstone` only | Content-addressed files: inputs, outputs, evidence attachments (ADR-04) |
| `repos` | `grindstone` only | Bare mirrors and private clones used by the SDLC factory; the only place Grindstone commits and pushes from |
| `workspaces` | `grindstone`, `agent-host` | One directory per task run: a writable worktree, materialized inputs, or a read-only checkout |
| `runs` | `grindstone`, `runner` | One directory per check job: the materialized subject, the procedure, the results |

**Protocols.** AHP is the client-facing session layer: the UI and VS Code attach to the same live sessions. ACP connects the host to each agent runtime. MCP is how agents read pinned inputs, report, ask and cooperate. The control plane drives the agent station through a small typed control API with signed, at-least-once events, and the check station through job files. Stations of higher tiers speak the same two protocols over an authenticated channel, so the kernel does not change when they arrive.

**Deployment.** One `compose.yaml`, every image pinned by digest, secrets from files mounted read-only into the one container that needs each. A fresh install is `docker compose up` plus the documented secrets; upgrades replace images and run migrations before workflows resume. Backups are a Postgres dump plus a copy of the `blobs` volume; `repos` can be rebuilt from GitHub, `workspaces` and `runs` are disposable.

## Architectural style

Grindstone is a **modular monolith with a kernel and plug-in factories**, run as **durable workflows** over **one transactional store**, with untrusted work pushed out to **isolated stations** (ADR-01, ADR-03, ADR-07, ADR-21). The kernel is a grammar: seven concepts describe any agentic workflow Grindstone will run; a factory supplies the vocabulary of one domain.

*Diagram (not reproduced): architectural style — factories on top of the kernel's seven concepts, on top of the substrate (blobs, subjects, delivery port, interface items).*

| Concept | Kind | One line |
| --- | --- | --- |
| **Item** | noun | A typed, hashed, versioned unit of intent or knowledge |
| **Capability** | noun | A specialist: prompt, agent, skills, toolbox, what it produces and offers |
| **Station** | noun | Where work or proof runs, with an isolation tier |
| **Task** | verb | One unit of work with pinned inputs, an output contract, a check plan and limits |
| **Check** | verb | Evidence produced by someone other than the maker, bound to exact inputs, subject and environment |
| **ChangeSet** | verb | The only way intent changes: impact reviewed to a fixed point, then applied atomically |
| **Decision** | verb | Authority: a person or the recorded policy answers a typed question |

**Three rules make the grammar safe.**

1. **Make and prove are separate.** A check is performed by a different capability, in a different task run, on a workspace the maker never wrote; mechanical checks run on a check station (I-15).
2. **Agents never talk to each other.** They cooperate only by loading a skill, consulting a specialist or delegating to one — all through the kernel, all recorded (I-16).
3. **Results travel as pinned references.** Items and blobs cross task and factory boundaries by revision and hash, never as copied conversation; when the source changes, everything built on it goes stale (I-19).

**Why this style.** Each choice is the simplest one that meets a ranked quality goal:

| Choice | Serves | Instead of |
| --- | --- | --- |
| Modular monolith, import-enforced boundaries | QG-6 | Services and a broker: operational cost with no benefit for one operator |
| Durable workflows with idempotency keys | QG-2 | Hand-written retry and recovery code in every module |
| One transactional store | QG-4, QG-2 | Separate graph and vector stores: no atomic apply across them |
| Stations outside the control plane | QG-3, QG-1 | Running agents beside the database and the keys |
| Kernel plus factories, data-first | QG-7 | One SDLC-shaped core bent for each new domain |
| Typed concepts, generated contracts | QG-1, QG-4 | Prompt conventions and free-form documents |

## Invariants

Invariants are the rules every specification cites and every factory inherits. No factory or specification may weaken one. Each is enforced by mechanism, not by convention, and proven by a named kind of test; the conformance kit runs every factory against them.

| ID | Invariant | Enforced by | Proven by |
| --- | --- | --- | --- |
| I-01 | Items hold intent; everything work produces is evidence, a subject or a blob, never intent | `intent` accepts revisions only from ChangeSet apply | Store tests; conformance kit |
| I-02 | Every revision is immutable and records who or what made it, from which task or decision, and why | Append-only tables; non-null provenance columns | Schema constraints; golden round-trip |
| I-03 | Agents propose; only the kernel applies, transitions and delivers | The MCP surface exposes propose and report, never apply | In-memory tool tests |
| I-04 | A task is done only when every required check has fresh, passing evidence | One task transition function with a guard | Property tests over task and evidence states |
| I-05 | Evidence is valid only for its input hashes, subject version and environment; freshness is computed, never stored | No freshness column; one freshness function | Property tests for freshness |
| I-06 | Every run records the item revisions, capability hash, factory version, provider, model, subject version, context pack and prompts it used | The run record is written before the session opens | Crash-and-resume tests |
| I-07 | Scope expansion and content from outside the project need a person | `scope_expansion` and `untrusted` flags are class `never` | Decision service tests |
| I-08 | Agents never deliver; delivery adapters deliver only verified subjects after a decision; where the remote cannot enforce the gate, the adapter says so and reports every merge made outside it | Delivery credentials exist only in the control plane; the port checks evidence; the adapter observes the delivery mode (ADR-40) | Integration test with a fake remote in both modes |
| I-09 | Credentials are split by container and purpose; the control plane never executes work content; nothing mounts the Docker socket | Compose file, images, secret scoping | Deployment lint in CI |
| I-10 | Search results, mentions, consult answers and advisor output are suggestions only | They enter as context or `suggestion` decisions, never as revisions | Tool and decision tests |
| I-11 | Every point that needs a person is a typed decision with a recommendation | The decision service is the only way to wait on a person | Contract tests |
| I-12 | Policy answers only by written rules, records the rule it matched, and can be reverted | Policy engine; tripwire | Policy tests; revert test |
| I-13 | Every intent change is a ChangeSet walked to a fixed point before apply | Apply requires an approved ChangeSet with a complete walk | Property tests for impact analysis |
| I-14 | Agents never change the configuration that governs them: capabilities, templates, policy, manifests, limits | Configuration lives outside every workspace and is not a proposable kind | Tool tests; workspace mount lint |
| I-15 | Whoever makes a subject never produces the evidence that gates it | The check plan rejects a prover equal to the maker; self-checks are working notes | Conformance kit |
| I-16 | Agents never talk to each other directly; cooperation goes through `ask` and `delegate` as kernel tasks | No agent-to-agent channel exists; MCP is per task | Architecture test (import and network rules) |
| I-17 | Delegation is bounded: depth at most two and a live-children cap per task; overflow returns a structured tool error, never a silent child | Dispatch checks both caps before creating a child | Property tests on delegation trees |
| I-18 | Factories add names only in their own namespace and never redefine kernel meaning; the kernel never imports a factory | Loader validation; import linter | Conformance kit; CI import check |
| I-19 | Results cross task and factory boundaries only as pinned item revisions and blobs | Child output is a ChangeDraft and blobs; parents read by pin | Scenario K3 |
| I-20 | Stations that touch untrusted targets or hardware hold no control-plane credentials; irreversible actions are asked unless an approved runbook covers them | Tier rules; `irreversible` flag | Station tests (R3, R4) |

## Runtime views

Four scenarios show the kernel working without any domain logic. Each is an end-to-end test in the kernel suite, run against the fixture `notes` factory so it cannot lean on SDLC code; crash-and-resume variants kill the control plane, the agent host and the runner at every step. The SDLC factory's scenarios (S1–S6, Factories tab) exercise the same paths with real work.

### K1 — A task, end to end

| # | Step | Module | External effect and its idempotency key |
| --- | --- | --- | --- |
| 1 | A template step creates task T: need `notes.write`, inputs pinned to item N-3 at hash `a1…`, one required `review` check by need `notes.review` | `work` | — |
| 2 | Readiness passes; matching resolves `notes.write` to `notes.writer@1`; the run record is written (I-06) | `work` | — |
| 3 | The run is dispatched to a T1 agent station in the writing lane | `stations` | Session create, keyed by run ID |
| 4 | The agent reads N-3 through MCP, writes `draft.md`, and submits a report: outcome `done`, one proposed revision, one declared file | `surface` | Report, keyed by run ID and turn |
| 5 | The report is validated; `draft.md` is copied into the blob store; a ChangeDraft is created; T moves to verifying | `work`, `store`, `change` | Blob write, keyed by content hash |
| 6 | A check task runs `notes.reviewer@1` read-only against the blob; it passes; evidence is recorded against `(N-3@a1, blob hash, env)` | `evidence` | Check run, keyed by check ID and subject |
| 7 | The ChangeDraft is walked and raises an `approval` decision; the operator approves; apply writes the revision | `change`, `decisions` | — (one transaction) |
| 8 | T has fresh passing evidence and no delivery target, so it moves to done | `work` | — |

Killed at any step, the workflow resumes from DBOS state with no second session, blob, check or decision.

### K2 — A consult in the middle of a task

1. While running T, the agent calls `ask(need="notes.style", question, refs=[N-3], answer_schema)`.
2. The kernel matches `notes.stylist@1` and looks up the consult cache by `(capability hash, question hash, input hashes)`. On a miss it joins an identical consult already in flight, or creates child task C in `consult` mode on the read-only lane.
3. C answers in a structured report. The kernel caches the answer and returns it as the tool result; the agent's tool call stays open while C runs, kept alive by progress notifications, however long C takes. If T's session drops, the re-asked question joins C or reads its cached answer; if C passes the consult ceiling, T's turn suspends with outcome waiting and an escalation is raised (ADR-38).
4. The answer is a suggestion (I-10): it enters T's transcript as a `core.observation` and nothing else. An identical ask from any task in the project hits the cache until N-3 changes.

### K3 — Delegation across factories, and staleness

1. Task R in factory `alpha` needs an artefact only factory `beta` makes. It calls `delegate(need="beta.build", goal, refs=[IF-1], output={kind: "beta.thing"}, checks=[…])`, where IF-1 is a `core.interface` item naming `alpha` as consumer and `beta` as provider.
2. The kernel creates child D in `beta` with its own required checks, pins IF-1 at its current revision, and counts D against R's live-children cap. R's turn ends with outcome waiting: its session closes and its writing lane is freed, so D can run on it.
3. D completes; its output is a blob and a ChangeDraft for a `beta.thing` item. Once approved, R continues in a new session on its own workspace with both pinned (I-19).
4. Later the operator revises IF-1. The impact walk reaches the `beta.thing` item and R's output; the regression sweep marks both evidence records stale; re-check tasks run in each factory. Neither factory sent the other a message.

### K4 — A change of intent mid-flight

1. Tasks T1 and T2 are running against item X-4.
2. The operator edits X-4 semantically. The walk reaches T1's target (verdict `amend`) and T2's target (verdict `unaffected`).
3. On approval, apply writes the revision. T1 receives the new revision at its next turn; it would be cancelled only if its pinned item had been removed. T2 keeps running. Evidence pinned to the old X-4 is stale, and every affected done task gets a re-check.
4. The operator reverts the ChangeSet the next day. The revert is walked the same way and restores the previous state; no revision is deleted.

## Threat model and trust boundaries

The adversary is the work itself: agent output, code agents write and run, and content that arrives from outside. The operator and the host are trusted. Security holds when nothing on the untrusted side of a boundary can reach an asset on the trusted side.

**Assets**, from most to least sensitive: the evidence and revision history (they define what is true); delivery credentials (they ship to the world); the decision queue and policy (they carry authority); configuration that governs agents; the database; model credentials (they cost money); project source code.

**Trust boundaries.**

| # | Boundary | Trusted side | Untrusted side | What may cross |
| --- | --- | --- | --- | --- |
| B1 | Control plane ↔ agent station | Control plane | Agent sessions and everything they write | MCP calls with a per-task token; signed host events; workspace files, read only by declared copy-out |
| B2 | Control plane ↔ check station | Control plane | Check jobs running project code | Job files in; result files out, parsed against a schema |
| B3 | Control plane ↔ GitHub | Control plane | Repository content, comments, issues | Pushes and API calls out; fetched content in, marked `untrusted` |
| B4 | Operator clients ↔ control plane | Both, after login | Browser and plugin traffic before authentication | Authenticated REST, event stream and AHP attach |
| B5 | Kernel ↔ factory | Kernel | Factory data and adapter code (trusted as installed, but bounded) | SDK calls only; manifests validated at load |

**Threats and mitigations.**

| Threat | Example | Mitigation | Invariant | Proven by |
| --- | --- | --- | --- | --- |
| Forged evidence | Agent edits a test to always pass, or writes a fake result file | Evidence only from a check station or a different capability; test reviewer as a required prover; results parsed from job files the agent never touched | I-04, I-15 | M1-07, QS-01 |
| Credential theft | Code under test reads environment variables or the host's token files | No control-plane credential on any station; host tokens readable only by the host user; agents run as their own Unix user | I-09 | M1-05 |
| Repository-borne execution | A git hook or tool configuration in the repo runs during commit or checkout | The control plane commits with hooks disabled and never runs repository tooling; settings files never reach sessions | I-09 | QS-06 |
| Prompt injection from outside | An issue or review comment tells the agent to delete tests | Intake by fixed code with no agent reading first; content marked `untrusted`; derived ChangeSets always need a person | I-07 | QS-07, M5-03 |
| Self-modification | An agent edits capability files, templates or policy | Configuration lives outside every workspace; no tool proposes it | I-14 | Mount lint |
| Privilege escalation through tools | An agent asks for network access or a protected path | Default deny; a `permission` decision for anything outside the capability's grants | I-11 | M1-05 |
| Runaway spend | Delegation loop, oversized context, stuck session | Depth and live-children caps; liveness timeout; provider quota signals park runs; optional project cap; cost visible per tree | I-17 | QS-10, QS-15 |
| Event spoofing | A process forges a host event to end a run | HMAC-signed events with IDs and turn numbers; unknown or duplicate IDs ignored | — | M1-04 |
| Merge outside Grindstone | Someone merges a Grindstone pull request in GitHub, or pushes to the default branch, where the ruleset is not enforced | Enforced mode: the remote refuses it. Unenforced mode: Grindstone merges itself with the head SHA it verified; `observe` reports any other merge as an `untrusted` `delivery_bypass` finding (ADR-40) | I-08 | M1-02 |
| Container escape to the host | A malicious build escapes the runner container | Accepted residual risk at T1 for trusted repositories; T2 microVMs for untrusted code (R3); nothing mounts the Docker socket | I-09, I-20 | Deployment lint |

**Accepted residual risks for the MVP.** Agents can read the model credential of their own station and use it with network egress; mitigated by per-provider spend limits, a rotation runbook, and per-run isolation at T2. A kernel-level container escape on T1 is out of scope; repositories with untrusted code wait for T2.

## Failure model

Every external action is a DBOS workflow step with an idempotency key derived from the record that caused it (run ID, turn, ChangeSet ID, delivery key, content hash). A resumed step looks the effect up by its key and records it instead of repeating it. Waits on people never hold a workflow open: the decision stores a typed continuation, and its answer starts that continuation exactly once.

| Failure | Detected by | Recovery | Visible as |
| --- | --- | --- | --- |
| Control plane crash or upgrade | DBOS on restart | Every workflow resumes at its last completed step; external steps are looked up by key | A gap in the event stream; no duplicates |
| Agent host restart mid-turn | Missing heartbeat; host event stream resets | The run continues in a new session on the same workspace, or fails `host_lost` and retries once | Run timeline shows a new session |
| Agent never reports | Turn timeout | One corrective prompt; then the run fails `missing_report` | Escalation decision |
| Provider error or rate limit | Typed host event | Waits park the run; retry within the run with backoff; persistent errors fail `provider_error` | Run state `parked` with reason |
| Context exhausted | Agent or host signal | Run fails `context_exhausted`; retry with a smaller context pack or another capability | Escalation decision |
| Run stalls | No agent activity for the liveness timeout; an open kernel tool call is not inactivity | Run fails `stalled` | Escalation decision |
| Project cap reached (when enabled) | Cap check before each new run | No new run starts in the project; running turns finish | Escalation flagged `cap_reached` |
| Consult passes its ceiling | Ceiling timer on the open `ask` | The caller's turn suspends with outcome waiting; the consult keeps running | Escalation: wait longer, retry, cancel |
| Check station job crashes | Job timeout or missing result file | Check result `error`; the check is retried once, then escalated | Evidence with `error` |
| Postgres unavailable | Connection failures | The control plane stops dispatching and serves read-only status; workflows resume when it returns | Health check red |
| Blob store full | Write failure | Run fails `storage_limit`; GC runs; operator warned | Operations view warning |
| GitHub unavailable or rejects a push | API error | Delivery step retries with backoff; after the limit, a `delivery` escalation | Delivery state `failed` with cause |
| Two ChangeSets race on one item | Base-revision check at apply | The later one is re-walked against the new base | Approval asked again if the review set changed |
| Decision answered against stale context | Context hash check | The answer is refused; the decision is superseded and raised again | Superseded decision in history |
| Factory fails to load | Manifest validation at start | Factory stays unloaded; projects using it are paused; the kernel still runs | Startup report |

**Degraded modes.** Without the agent station, planning and implementation pause but decisions, intent edits and checks continue. Without the check station, tasks wait in verifying. Without GitHub, deliveries queue. In every mode, nothing that was true becomes false: evidence, revisions and decisions are never lost or rewritten.

## Observability, cost and operations

**Events.** Every kernel record has a stable ID, and every state change emits one typed event with a monotonic sequence number per project. The event stream is the single feed for the UI, VS Code and the operator plugin; clients resume from the last sequence they saw, so a reconnect never misses or double-counts a change.

**Logs and traces.** Structured JSON logs carry the project, task, run, workflow and request IDs as correlation fields. OpenTelemetry traces span the control plane, the agent host and the runner for each task run; spans are exported to a local collector the operator may point anywhere. Transcripts, tool calls and timings of every run are stored and linked from the task.

**Cost.** Every run records wall time always, and tokens and spend where the provider reports them; spend is computed from a price table the operator maintains. Costs roll up the delegation tree and the template run, and the UI shows spend per command, factory, capability and need. Cost is recorded, never gating: limits stop runaway work structurally, and the optional project cap is the only spend ceiling (ADR-37); consult caching, read-only lanes and the depth limit keep cooperation cheaper than one agent reading everything.

**Health and service levels.** For one operator on one host the targets are practical, not contractual:

| Signal | Target |
| --- | --- |
| Control plane readiness after restart | ≤ 60 s, with all workflows resumed |
| Decision visible in the UI after it is raised | ≤ 1 s |
| Dispatch of a ready task when its lane is free | ≤ 5 s |
| Lost or duplicated external effects | 0 |
| Evidence or revisions lost on crash | 0 |

**Operations view.** One page shows lanes and queues, running and parked tasks, waiting decisions with their age, stale evidence, spend against the project cap, blob store use and the capacity envelope, with a warning for anything outside it.

**Routine operations.** Each has a runbook and a test:

| Operation | How | Tested by |
| --- | --- | --- |
| Install | `docker compose up` with documented secrets | M3-07 |
| Upgrade | New image digests; migrations run before workflows resume; parked workflows resume once | M5-06 |
| Backup | Postgres dump plus a copy of `blobs`, consistent by taking the dump first and copying only blobs it references | M5-06 |
| Restore | Load the dump and blobs on a fresh host; rebuild mirrors from GitHub; a regression sweep re-checks proven criteria | M5-06 |
| Rotate a credential | Replace the secret file; restart the one container that holds it | Runbook check at M5 |
| Pause | One switch stops dispatch and policy answers; running sessions finish their turn | M5-04 |
| Blob garbage collection | Deletes blobs with no root, older than a grace period; roots are written by their owners in the same transaction as the reference | M5-06 |

## Architecture fitness functions

The structure in this set is enforced by automated checks in CI, not by review alone. Each fitness function fails the build when the architecture drifts. They exist from M0 and grow with the milestones; a specification that adds a module or a boundary adds its fitness function.

| # | Fitness function | Fails when | Guards | From |
| --- | --- | --- | --- | --- |
| FF-01 | Import boundaries (import-linter contracts) | A module imports another's internals, a lower layer imports a higher one, or anything in `grindstone` imports `factories/` | Module map; I-18 | M0 |
| FF-02 | Generated-contract drift | JSON Schema or TypeScript types differ from the Pydantic source | ADR-05 | M0 |
| FF-03 | Schema compatibility | A contract, kind or MCP tool changes incompatibly without a version bump and an upgrade step | ADR-05 | M1 |
| FF-04 | Pins | Any dependency or image is unpinned or uses a floating tag | ADR-01 | M0 |
| FF-05 | Deployment lint | A secret is mounted in a container that must not hold it, a station mounts `blobs` or `repos`, or anything mounts the Docker socket | I-09 | M1 |
| FF-06 | Workspace mount lint | Configuration paths are reachable from any workspace | I-14 | M1 |
| FF-07 | Table ownership | A module's SQL touches another module's tables | Data ownership | M1 |
| FF-08 | Single writer | A lifecycle state column is written outside its transition function | Lifecycles | M1 |
| FF-09 | No stored derivations | A column stores freshness, readiness or another value defined as computed | I-05 | M1 |
| FF-10 | Idempotency coverage | A workflow step with an external effect has no idempotency key or crash-and-resume test | QG-2 | M1 |
| FF-11 | Conformance kit | Any installed factory violates namespace, make/prove, lifecycle or adapter rules | I-15, I-18 | M2 |
| FF-12 | Kernel neutrality | A kernel module or kernel spec names a factory kind, capability, template, method or adapter | QG-7 | M2 |
| FF-13 | Traceability | An exit criterion has no specification, an acceptance criterion has no test, or a document cites an ID that does not exist | Planning playbook | M0 |
| FF-14 | Performance budgets | Impact walk or freshness read exceeds the capacity envelope on the benchmark fixture | Capacity envelope | M2 |


# Concepts

The kernel's vocabulary, defined once. Three nouns — Item, Capability, Station — and four verbs — Task, Check, ChangeSet, Decision — on a small substrate. Every factory and every spec uses these words with exactly these meanings.

## Item

An item is the unit of intent and knowledge: a requirement, a design decision, a reverse-engineering claim, a board interface, a principle, a finding. Everything a workflow agrees on, depends on or reasons about is an item (ADR-08).

| Aspect | Rule |
| --- | --- |
| **Kind** | A namespaced name, `namespace.name` (`core.principle`, `sdlc.requirement`, `re.claim`). Each kind is a flat Pydantic model registered by the kernel or by one factory, declaring its fields, its references with cardinality, its ID pattern and the edge types it takes part in. No inheritance between kinds |
| **Identity** | A stable ID matching the pattern its kind declares, most often `PREFIX-n` (`PRD` and `M1` are other forms), unique within a project and typed per kind (`ReqId`, `ClaimId`). IDs never change and are never reused; titles may change |
| **Fields** | Semantic fields are hashed and drive freshness; presentation fields (display order, editorial notes) are not. A change to a presentation field never makes anything stale |
| **Hash** | SHA-256 over the RFC 8785 canonical JSON of the semantic fields, with text normalised to NFC and LF line endings, so every implementation and every round trip agrees; a field at its declared default is left out, and the hash is written `sha256:<hex>` (ADR-44) |
| **References** | Three sources, all derived from content and never edited separately: typed reference fields (a criterion *verifies* a requirement), mentions `[[ID]]` and embeds `![[ID]]`. A revision with an unresolved reference is refused. References may point at any kind whose factory is enabled in the project |
| **Edge types** | Registry entries declaring endpoints, an inverse name, whether the edge belongs to a check's dependency set, and an impact rule: **review** (a change marks the source for a verdict), **notify** (the source is told; no verdict), **render** (embedded text re-renders). Typed dependency edges use review; mentions notify; embeds render (ADR-09) |
| **Blobs** | An item may reference blobs by hash, media type and size; the blob hash is part of the item's semantic fields |
| **Revisions** | Immutable sets of (item, hash) pairs, created only by applying a ChangeSet, each recording its parent, the author kind (person, agent, policy, system), the ChangeSet, and the task, finding or decision behind it (I-02) |
| **Artifacts** | A container kind with one header item for its own fields and a set of member kinds: an `sdlc.spec` holds requirements, criteria, design decisions, scenarios, non-goals and open questions. Artifacts are optional: standalone items such as tickets, ADRs and principles need no container and render on their own or in a generated list |
| **Lifecycles** | Any kind — an artifact header or a single item — may declare a lifecycle: a transition table with one writer per transition. Lifecycle state is not a semantic field: it is stored beside the item and never hashed, so a transition such as approved → verified never makes evidence stale; the kernel enforces one transition function per lifecycle as the only writer, an enum or an equivalent constraint in the database, and illegal transitions as typed errors. States that can be derived are computed in views, never stored |
| **Rendering** | Every artifact renders to Markdown from its items and embeds; the rendered file carries a header naming the ledger as the source of truth. Markdown round-trips: parsing the render yields the same semantic hashes |

**Kernel kinds.** The kernel owns the kinds every factory needs:

| Kind | ID prefix | Purpose |
| --- | --- | --- |
| `core.principle` | `P` | A rule a person sets for the project, carried into every context pack |
| `core.learning` | `LRN` | A lesson an agent proposes and the policy or a person accepts |
| `core.finding` | `FND` | Something noticed that may change intent: ambiguity, gap, conflict, discovery, failure, drift. Carries severity, trust and a type a factory may extend |
| `core.observation` | `OBS` | A consult answer or a recorded tool result, with its source and the inputs it saw. Advisory only (I-10) |
| `core.interface` | `IF` | A contract one part of the project publishes for others to build against, owned by one factory (ADR-25) |

Factories add their own kinds in their namespace and may extend kernel kinds only by adding fields through registered extensions, never by changing the meaning of existing ones (I-18).

## Capability

A capability is a specialist: everything the kernel needs to start an agent that does one kind of work well, and to know what that agent can be asked for (ADR-23).

| Field | Meaning |
| --- | --- |
| `id` | Namespaced name: `sdlc.implementer`, `sdlc.security_reviewer`, `re.analyst` |
| `version` | Bumped on any change; the capability's hash is recorded on every task run (I-06) |
| `prompt` | The specialist's instructions, as a file in the factory |
| `agent` | Agent runtime and model: preset (`claude`, `scripted`; others when added, ADR-41), model, effort |
| `skills` | The **library** of skills this specialist may load, and the subset loaded at start. Loading anything outside the library is refused |
| `toolbox` | The station image it needs, and allow-listed tool servers it may use — local stdio processes on its station, holding no secrets |
| `workspace` | `write` (a writable workspace for making) or `read_only` (a checkout at a subject version, for reviewing and consulting) |
| `permissions` | Commands allowed without asking; what happens to anything else: `deny` or a `permission` decision |
| `produces` | The report schemas it can submit and the item kinds it may propose |
| `offers` | Typed contracts others match against: a **need**, the input kinds it accepts, the output kind it yields, whether it serves `consult`, `delegate` or both, and tags |
| `may_check` | The check methods it may perform as a prover, and on which kinds of subject |
| `tier` | The minimum station tier it requires |
| `limits` | Overrides of the instance's liveness timeout and consult ceiling, for specialists that think for long stretches |

**Where capabilities come from.** Each factory ships its capabilities as versioned files. A project may override a bounded set per capability — model and effort, limits, extra skills from the same factory's library, extra prompt text — but never `offers`, `produces`, `may_check`, `tier` or the namespace. `grindstone check` validates every capability and override before use.

**One specialist, three uses.** The same capability can do a task, answer a consult or perform a check. What changes is the task's mode, workspace and limits, not the specialist's definition. Make and prove still applies per subject: a capability that made a subject cannot prove it, even in a different mode.

**Skills.** A skill is a Markdown instruction pack, optionally declaring extra tools, versioned with its factory. The skills a capability loads at start are materialized, read-only, into the session's private configuration directory outside the workspace, where agents that discover skills natively find them; they are part of the context pack. Loading one mid-session (`load_skill`) returns its instructions inline as the tool result, which works with every agent, and is recorded on the run; its tools are listed from session start and refused until it is loaded (ADR-39, ADR-43). It never changes the capability's permissions, workspace mode or tier.

## Station

A station is a place where agents work or checks run. Stations isolate untrusted work from the control plane and from each other; the kernel chooses one for every task run and check job by kind, tier and free lane (ADR-17).

| Field | Meaning |
| --- | --- |
| `id`, `kind` | `agent` (runs agent sessions) or `check` (runs mechanical checks) |
| `tier` | Isolation level, below |
| `image` | Pinned by digest; for check stations, chosen per project from an instance allow-list |
| `resources` | CPU and memory; later GPU, passed-through devices, licensed tools, a desktop |
| `network` | `none`, `registries` (package registries only) or an explicit allow-list per capability |
| `lanes` | Agent stations run two lanes: **writing** (one session at a time by default) and **read-only** (a small configurable concurrency for planning, reviewing and consulting) |
| `credentials` | Never a control-plane credential. Agent stations hold model credentials for their agents and host tokens readable only by the host process |

| Tier | Isolation | Allowed work | Available |
| --- | --- | --- | --- |
| T0 | Read-only view of materialized inputs | Reading, reviewing, consulting | MVP, as a read-only workspace on a T1 station |
| T1 | Container; agents under their own Unix user | Coding, tests, builds, static analysis of trusted files | MVP |
| T2 | Disposable microVM per run; no network by default | Running untrusted code and binaries, headless computer use | R3 |
| T3 | Full VM with a desktop or passed-through devices | GUI computer use, hardware benches, licensed desktop tools | R4 |

**Workspaces.** Every task run gets its own workspace on its station, never shared: a writable worktree or materialized inputs for making, or a read-only checkout at a subject version for reviewing and consulting. A prover's workspace is materialized fresh from the subject; it is never the maker's (I-15). Workspaces are disposable: only declared outputs survive, copied out by the kernel.

**Protocols.** Agent stations are driven through the typed host control API and report signed, at-least-once events. Check stations receive job directories and return results as files. A station of any tier speaks one of these two protocols, so adding T2 and T3 adds adapters, not kernel concepts.

**Physical safety.** A station that holds hardware or runs untrusted targets never holds control-plane credentials, and an irreversible physical or external action is always asked unless a runbook item a person approved covers it exactly (I-20).

## Task

A task is the one unit of work in Grindstone. Implementing a ticket, drafting a specification, auditing a draft, answering a consult, analysing a binary, reviewing a pull request for security — each is a task with a different capability and mode (ADR-14).

| Field | Meaning |
| --- | --- |
| `origin` | The template step, parent task or operator command that created it |
| `need`, `capability` | The need requested and the capability matched to it (ADR-24) |
| `mode` | `work` (make something), `consult` (read-only advice), `check` (prove someone else's output) |
| `goal` | What to achieve, as text with item references |
| `inputs` | Item revisions and blob hashes pinned at start, plus the subject version it starts from; the agent reads only these |
| `output_contract` | The report schema it must submit, the item kinds it may propose, the files it must produce, the delivery target if any |
| `checks` | The check plan: each check's method, the need or capability that performs it, required or advisory |
| `limits` | Its depth in the delegation tree and live-children cap, the liveness timeout and consult ceiling that apply to its runs, and the project cap it counts toward if one is enabled (ADR-37) |
| `tier`, `lane` | Minimum station tier; writing or read-only lane |
| `parent`, `children` | The delegation tree, depth at most two below a top-level task |
| `deadline` | Optional; passing it raises an escalation, never a silent answer |

**Lifecycle.** A task has eight stored states, written only by the task transition function in `work` (FF-08). The diagram that stated them was not reproduced; this table is reconstructed from the text of this set, and SPEC-06 owns the exact transition table and its guards.

| State | Means | Leaves to |
| --- | --- | --- |
| `queued` | Created; waiting until it is ready (readiness is computed, below) | `running`, `cancelled` |
| `running` | A run is in progress on a station | `waiting`, `verifying`, `blocked`, `cancelled` |
| `waiting` | The last turn ended with outcome waiting: a delegated child, an operator answer, or a consult past its ceiling; no lane is held | `running`, `blocked`, `cancelled` |
| `verifying` | The maker reported `done`; required checks are running on the collected subject | `delivering`, `done`, `blocked`, `running` (a rework round) |
| `delivering` | Every required check is fresh and passing; a `delivery` decision and the adapter are in progress | `done`, `blocked` |
| `blocked` | Stopped on a typed failure cause, a denied permission or a failed delivery; an escalation is open | `queued`, `cancelled` |
| `done` | Every required check had fresh passing evidence and any delivery completed, that is, reached `delivered` in the delivery port (I-04) | `queued` (only a failing re-check reopens it) |
| `cancelled` | Stopped for good, by the operator or because a pinned item was removed | — |

A run parked on a provider limit stays `running`; parking is a run state, not a task state.

**Readiness** is computed, never stored: a queued task is ready when its inputs exist at approved revisions, its prerequisite tasks are done, no decision blocks its scope, the project cap (if enabled) is not reached, and a station of its tier has a free lane.

**Runs, sessions and turns.** Each attempt is a **task run** with a fresh workspace. A run is a series of agent sessions — a new session after a host restart, a parked wait or a provider limit continues from the workspace. Grindstone numbers its own turns. The operator may steer a running session from the UI or VS Code; steering turns are recorded but carry no Grindstone number and cannot end the run. Every run records the item revisions, capability hash, factory version, provider, model, subject version, context pack and prompts it was given (I-06).

**Reports.** One accepted report ends each turn, with outcome `done`, `blocked` or `failed`. The kernel validates it against the output contract and returns structured errors the agent fixes in the same turn; a turn without a report gets one corrective prompt, then the run fails `missing_report`. Proposed items become a ChangeDraft; declared output files are copied out of the workspace into the blob store; nothing an agent writes reaches intent or delivery any other way (I-03). Three tools end a turn by themselves: delegate, ask addressed to the operator, and a request for permission, which raises a `permission` decision. Each records its request, counts as the turn's report with outcome waiting, closes the session and frees the lane; when the child finishes or the decision is answered, the run continues in a new session on the same workspace with the result in context. A consult that passes its ceiling (ADR-38) suspends the same way. No task ever holds a lane while it waits.

**Failure causes.** A run fails with one typed cause, each with its rule:

| Cause | Retry rule |
| --- | --- |
| `rate_limited`, `provider_error` | Park and retry within the run with backoff |
| `host_lost` | Continue in a new session; retry the run once |
| `stalled`, `missing_report`, `context_exhausted` | Block the task; escalation |
| `cap_reached`, `storage_limit` | Block; escalation (flagged `cap_reached` for the project cap) |
| `checks_failed` | Block with the failing evidence attached; a template with rework rounds retries at once with that evidence in context, up to its round limit, then escalates |
| `cancelled` | None |

An escalation offers retry, reassign to another capability, raise the project cap where it applies, or cancel.

**Context pack.** The kernel assembles what a run sees: the pinned items rendered as Markdown, the project's principles, relevant learnings, the interface items in scope and the capability's loaded skills. The pack is recorded by hash, so advice and drafts built on it go stale when it changes.

## Check and evidence

A check is how Grindstone proves something. An acceptance criterion names *what* must hold; a check is one recorded attempt to show that it holds for a given subject. Checks produce **evidence**, and evidence is the only thing that moves a task to done (I-04, ADR-12).

| Field | Meaning |
| --- | --- |
| `target` | The item it verifies: an acceptance criterion, a finding, an interface item, a principle |
| `method` | One of the six kernel methods below, or a factory method registered under its namespace |
| `by` | The need or capability that performs it; never the capability that made the subject (I-15) |
| `subject` | A typed subject reference: `git_commit`, `blob`, `blob_set`, `item_revision`, or a factory subject kind |
| `inputs` | Hashes of the items it verifies against, including the target's semantic hash |
| `env` | Environment fingerprint: station image digest, toolchain versions, tier, declared tool versions |
| `required` | Required checks gate done; advisory checks only inform and may raise suggestions |
| `result` | `pass`, `fail`, `error` (could not run) or `inconclusive` (ran, could not decide), with structured details and output blobs |

**Methods.** The kernel defines six methods and how each runs. Factories add methods only in their namespace and must map each to one of these execution shapes.

| Method | Who runs it | Evidence | Typical use |
| --- | --- | --- | --- |
| `command` | Check station, declared command | Exit code, logs, output blobs | Lint, build, type check, static scan |
| `test` | Check station, named tests | Per-test results tied to criteria | Unit, integration, property tests |
| `reproduce` | Check station, recorded steps | Steps re-run on the subject; observed outputs | RE finding confirmed, bug reproduced |
| `cross_tool` | Check station, a second independent tool | Agreement or difference of two tools' outputs | Two disassemblers agree on a function boundary |
| `review` | Agent station, a reviewing capability in read-only mode | Structured verdict per criterion with item references | Specification audit, code review, security review |
| `manual` | A person, through a `manual_check` decision | Verdict, notes, attachments | UX sign-off, bench measurement |

**Freshness.** Evidence is valid only for the exact `(input hashes, subject version, env fingerprint)` it was produced against (I-05, ADR-11). Freshness is computed on read by comparing those three with current values; it is never stored, so it cannot drift. Semantic changes to a criterion or anything in its dependency set make evidence stale; presentation edits do not. A changed environment stales evidence only for methods that declare the environment relevant (`command`, `test`, `reproduce`, `cross_tool`). A stale result always names what changed.

**Required and advisory.** A template step lists its required checks; the agent cannot remove them, and the kernel adds any check the target criteria demand, plus any the factory's workspace provider adds when it collects the subject — for example a security review because files under a security-relevant path changed. Checks can be added at collect time, never removed. Advisory checks never block done, but a failing advisory check raises a `suggestion` decision with the evidence attached.

**Regression sweep.** When a subject changes — a commit lands on the base branch, a blob is replaced, an interface item is revised — the kernel recomputes freshness for every check that pinned the old version and queues re-check tasks through the same check plan. Only a *failing* re-check reopens a done task. The sweep also runs on a schedule over every proven criterion.

**Evidence records.** Each stores the check definition hash, method, performer (capability hash or person), station and tier, subject reference, input hashes, environment fingerprint, result, output blob hashes and timings. Records are immutable; re-running a check creates a new record, and the latest fresh record per check decides.

**Working notes.** A maker may run tests and tools in its own workspace while it works; those runs are recorded on the run as working notes and never count as evidence.

## ChangeSet

A ChangeSet is the only way intent changes (I-13, ADR-10). The same pipeline governs an SDLC requirement, an RE finding and a PCB interface. Code, logs and output files are not intent and never pass through a ChangeSet; they are subjects and blobs.

**Sources.** A ChangeSet starts as a **ChangeDraft** from one of five sources:

| Source | Example | Trust |
| --- | --- | --- |
| Operator edit | The operator rewrites a requirement in the UI or VS Code | Trusted |
| Task output | A planner proposes tickets; an analyst proposes findings; an implementer proposes a learning | Agent — always reviewed |
| Delegation result | A child task in another factory proposes an interface item revision | Agent — always reviewed |
| Intake | An imported document, a review comment, a tracker issue | `untrusted` — needs a person (I-07) |
| Revert | Undoing an applied ChangeSet | Trusted, but walked like any other |

**Impact walk.** Before apply, the kernel walks the item graph from every semantically changed item, one hop per round, following edges by their impact rule:

| Edge | Rule | Effect on the source of the edge |
| --- | --- | --- |
| Typed dependency (`implements`, `verifies`, `derives_from`, `constrains`, factory relations) | `review` | Needs a verdict before apply |
| Mention `[[ID]]` | `notify` | Listed; no verdict |
| Embed `![[ID]]` | `render` | Re-renders; nothing else |

A presentation-only edit applies at once with a recorded revision and no walk.

**Verdicts.** Each item reached by a `review` edge gets one verdict with a reason: `unaffected`, `amend` (with a proposed revision, which joins the same ChangeSet and extends the walk), `invalidate` (the item must be retired or replaced) or `escalate` (cannot decide). Items in one artifact may share one **group verdict** when one reason covers all. Until the impact-reviewer capability exists (M3) the operator gives verdicts; afterwards it proposes them and the operator approves the set. The walk repeats until a round adds no amendments — a fixed point — or the round limit raises a decision flagged `rounds_exhausted`.

**Rules.** Before approval the final set is validated against every manifest rule in force: references resolve; kinds belong to enabled factories; transitions are legal for their writer; every criterion names a method; coverage holds (each requirement verified, each interface with a provider and a consumer); principles are not contradicted. A rule failure blocks approval and is shown per item (ADR-13).

**Approval and apply.** Approval is a decision of kind `approval`, flagged `scope_expansion` when the set adds work beyond approved scope and `principle` when it touches a principle. Apply is one database transaction, serialized per project, with a base-revision check: every revision is written with provenance; running tasks pinned to a changed item receive it at their next turn, and those whose pinned item was removed are cancelled; decisions whose context changed are superseded and raised again; freshness is recomputed for touched evidence. A moved base sends the set back for a re-walk; approval is asked again only if the review set changed. Agents cannot apply (I-03).

**Revert.** Every applied ChangeSet can be reverted by a new ChangeSet restoring the previous revisions. The revert is walked like any other; if an item changed since, the decision is flagged `revert_conflict` and the operator chooses per item. Nothing is ever deleted: revisions, ChangeSets and their decisions stay readable.

## Decision

A decision is anything only a person, or a policy the person approved, may settle (I-11, ADR-28). Every place where Grindstone could otherwise guess becomes a typed decision with a recommendation, so the operator answers a short queue instead of reading transcripts. A decision blocks exactly the scope it names and nothing else.

| Kind | Raised when | Answer |
| --- | --- | --- |
| `approval` | A ChangeSet reached its fixed point and passed rules | approve, reject, send back with notes |
| `question` | An agent asks something its inputs cannot answer (`ask` with need `operator`) | Free text or a typed answer matching the given schema |
| `permission` | A task needs an action outside its capability's permissions (a host, a secret, a tier, a protected path) | allow once, allow for this task, deny; times out to deny |
| `manual_check` | A check with method `manual` is due | pass, fail, notes, attachments |
| `delivery` | Verified output is ready for its delivery adapter | deliver, hold, cancel |
| `suggestion` | Advisory evidence failed, an advisor or consult proposed something, a learning or link was offered | accept (becomes a ChangeDraft), dismiss |
| `escalation` | A run failed or stalled, a deadline passed, a consult passed its ceiling, the project cap was reached, matching was ambiguous | retry, reassign, wait longer, raise cap, cancel |
| `scope` | Work would add or remove approved scope, or a factory is enabled | approve, reject, split into a new goal |
| `<ns>.*` | Factory kinds, each with an eligibility class and an answer schema | As declared |

**Flags** modify how a decision may be answered and are set by the kernel, never by an agent: `scope_expansion`, `principle`, `untrusted`, `rounds_exhausted`, `revert_conflict`, `cap_reached`, `irreversible` (the action cannot be undone by a ChangeSet — a published release, a flashed device, a sent message). A flagged decision always needs a person, at every autonomy level.

**Lifecycle.** `open → answered | superseded | expired`. An answer is refused if the decision was superseded or its context hash changed; a decision superseded three times becomes an escalation. Related decisions are batched on one card. Only `permission` decisions expire, to deny. A waiting workflow holds no resources: the decision stores a typed continuation that the answer starts exactly once.

**Recommendation.** Every decision carries one recommended answer and its reason, from one source recorded on the decision: a **fixed default** declared by the template or manifest; the **asking agent**, which must recommend when it asks; or the **advisor** capability (M4), which drafts recommendations with options, change class and impact (ADR-29). Recommendations are suggestions (I-10).

**Policy and autonomy.** Each decision kind belongs to an eligibility class: `never` (always a person), `l2` (policy may answer at L2 and above), `l3` (only at L3). Factories map their own kinds to a class and cannot place a kernel kind in a lower class (ADR-30).

| Level | What policy may answer | Typical use |
| --- | --- | --- |
| L0 | Nothing; every decision waits | First days on a project |
| L1 | Nothing, but recommendations are pre-selected and decisions batched | Default |
| L2 | Unflagged `l2` decisions whose recommendation matches a written policy rule | Steady work: retry once, accept a passing review |
| L3 | Also `l3` kinds, such as `delivery` to a protected target | R2, behind the tripwire |

**Tripwire.** Any of these drops the project to L1 until the operator restores it: a reverted policy answer, two consecutive failed deliveries, a high-severity security finding, the project cap reached, a principle-flagged decision. Every policy answer records the rule that matched and can be reverted like a ChangeSet (I-12). A pause switch stops dispatch and policy answers at once.

**Channels.** Decisions are answered in the web UI, in VS Code and — from M5 — through the operator plugin in Claude Code, all through one service; the answer records who answered, where and when.

## Substrate: blobs, subjects, delivery and interfaces

Four small services sit under the concepts. They let one kernel serve git repositories, binaries, CAD files and boards without knowing what any of them are.

### Blob store

Every file a task produces or consumes that is not a git commit lives in the blob store (ADR-04): content-addressed by SHA-256, immutable, on the `blobs` volume, written only by the control plane. When a run ends, the kernel copies the files its output contract declares out of the workspace, hashes and records them; undeclared files are discarded with the workspace. Stations receive input blobs read-only. Every blob has at least one root from the moment it is written: putting a blob creates a lease root owned by the run or job that produced it, and the module that later references it — an item revision, an evidence record, a decision — adds its own root through the store's interface in the same transaction; a lease is released when its run is archived. Garbage collection deletes only blobs with no root that are older than a grace period, so the store never reads another module's tables and a live blob is never collected. Size limits per blob and per project are configured; exceeding one fails the run `storage_limit` (ADR-37).

### Subjects

A subject is the versioned thing a check proves and a delivery adapter ships. Its reference is typed and pinned:

| Kind | Version | Owner |
| --- | --- | --- |
| `git_commit` | Repository plus commit SHA | Kernel (read), SDLC factory (workspaces, branches) |
| `blob` | SHA-256 | Kernel |
| `blob_set` | Hash of the sorted member hashes | Kernel |
| `item_revision` | Item ID plus semantic hash | Kernel |
| `<ns>.*` | Declared by a factory; must reduce to one of the above | Factory |

A factory subject kind — `re.binary`, `pcb.board` — always resolves to a blob, blob set or commit, so freshness and the regression sweep work without factory code.

### Delivery port

Delivery is the only way verified output leaves Grindstone (I-08, ADR-26, ADR-45). The port's operations are `observe_mode` (whether the remote enforces the gate, ADR-40), `prepare` (build the outgoing change from verified subjects, idempotent by delivery key), `deliver` (perform it after a `delivery` decision), `observe` (report external state back: accepted, closed, rejected, commented), and two optional ones with no-op defaults for remotes without a gate or an acceptance step: `publish_gate_state` (show the remote the current verification state) and `accept` (complete the delivery on the remote, used only in unenforced mode after the gate is re-checked). The kernel calls them in order, re-checks the gate and holds every idempotency key. The kernel owns the port, the decision and the idempotency ledger; factories ship adapters. The MVP has one adapter, `sdlc.github_pr` (ADR-27). Agents never hold delivery credentials.

### Interface items

`core.interface` lets factories cooperate without talking (ADR-25). One item names a boundary, its **provider** and its **consumers** (each an artifact or item in some factory), the contract (a schema, a signature list, a pinout, a protocol) and the checks that prove each side honours it. Work on either side pins the interface revision; when the provider revises it, the impact walk reaches every consumer and the regression sweep stales their evidence — no messages, subscriptions or cross-factory tracking. Interface items and `core.*` kinds are the only items a factory may reference outside its namespace (I-19). The Factories tab gives the full shape.

## Cooperation

An agent that needs expertise it does not have has exactly three options, each a kernel tool on its per-task MCP server (ADR-24). They differ in who does the thinking, what it costs and what comes back.

|  | Switch mode | Consult | Delegate |
| --- | --- | --- | --- |
| Tool | `load_skill(skill)` | `ask(need, question, refs, answer_schema)` | `delegate(need, goal, refs, output, checks)` |
| Who thinks | The same agent, with extra instructions and tools | A specialist in a read-only child task | A specialist in a child task with its own workspace |
| Returns | Nothing; the agent continues with the skill loaded | A structured answer, as the tool result | Approved, pinned items and blobs after the child is verified |
| Caller waits | No | Yes, in the open call until the answer arrives, up to the consult ceiling (ADR-38); then the turn suspends | No: the turn ends, the session closes and the lane is freed; the run resumes when the child is done |
| Evidence | None; cannot satisfy a check | None; the answer is a suggestion (I-10) | The child's own required checks |
| Cost | Context tokens only | One read-only run, cached and shared by identical asks | A full task tree, bounded by the depth and live-children caps |
| Example | Implementer loads `sdlc.security-basics` before touching auth code | RE analyst asks `sdlc.code` whether a decompiled routine is a known CRC variant | RE analyst delegates a working decoder for a format it documented |

**Switch mode** never changes permissions, workspace mode or tier, and never lets an agent act as its own reviewer: a security skill loaded by the implementer makes it write safer code, while the security *review* still runs as a check by another capability (I-15).

**Consult** creates a child task in `consult` mode on the read-only lane. The specialist sees only the question, the referenced revisions and blobs, and its own skills, and answers in the caller's schema. Answers are cached per project by `(capability hash, question hash, input hashes)` until an input changes. A consult cannot propose items or start children; if real work is needed it says so, and the caller may delegate.

**Delegate** creates a child task in `work` mode, in the matched capability's factory, with its own template step, workspace and checks, counted against the parent's live-children cap. The child's proposals go through a ChangeSet like any other, so the parent receives approved, pinned results (I-19). A delegated child may consult, and may delegate once more (depth two, I-17).

**Asking a person** uses the same tool: `ask(need="operator", …)` raises a `question` decision instead of a consult, with the agent's recommended answer; the turn suspends until the answer arrives.

**Why agents never talk directly.** A chat between agents has no auditable record, no bounds, no freshness and no clear end. Every cooperation is a task with pinned inputs, a typed result and a cost, so the ledger stays a tree of verifiable work and no factory tracks another's conversations (I-16).

### Matching

Templates and agents ask for a **need** — a namespaced, capability-neutral label such as `sdlc.implement`, `sdlc.review.security`, `re.analyse.static` — never for a capability. The kernel declares a few needs in `core` (`core.review.impact`, `core.advise`); factories offer them without adding names. For each request the kernel filters candidates in fixed order and stops at the first step that leaves exactly one:

1. Offers of the requested need, from factories enabled in the project, serving the requested mode.
2. Accepting every referenced input kind.
3. Producing the requested output kind, if named.
4. Within the tiers and permissions the project granted.
5. The project's pinned choice for that need, if any.
6. The capability in the caller's own factory.

No candidate, or more than one after step 6, raises an `escalation`; the operator's answer becomes the project's pin. Matching uses no embeddings, scores or models: the same request in the same project always matches the same capability.

### Limits

Tasks vary too much in size for a fixed allowance of turns, time or tokens to be right, so Grindstone sets no per-task or per-tree budget (ADR-37). It bounds **runaway shapes** instead — loops, stalls and fan-out — which look the same whatever the task's size, and it records every cost without letting cost gate work. Provider quota and rate-limit signals already park runs (`rate_limited`).

| Limit | Seed default | When reached |
| --- | --- | --- |
| Depth | 2 below the root | `delegate` returns `depth_exceeded`; the agent works without it |
| Live children | 4 per task | `delegate` returns `fanout_exceeded` until a child finishes |
| Liveness timeout | 20 min with no agent activity (no output, tool call or event); an open kernel tool call pauses it | Run fails `stalled` |
| Consult ceiling | 2 h per open `ask` | The caller's turn suspends with outcome waiting; escalation: wait longer, retry, cancel |
| Project cap | Off. When the operator enables it: spend where reported, otherwise turns, per calendar month | No new run starts in the project; running turns finish; escalation flagged `cap_reached` |
| Storage | Per blob and per project, from instance configuration | Run fails `storage_limit` |

The agent always learns a limit from the tool's structured error, so it can carry on or report `blocked` instead of failing silently. Seed values are owned by SPEC-17; capabilities may override the liveness timeout and consult ceiling within instance bounds.


# Components

How the system is cut into modules and processes, what each owns and offers, and the contracts between them.

## Module map

The control plane is one Python package, `grindstone`, built as a modular monolith of twelve modules in five layers. Factories are separate packages under `factories/<namespace>/` that use only `grindstone.sdk`. Each module owns its tables and its lifecycles, exposes a typed service interface and emits events; no module reads another's tables.

*Diagram (not reproduced): module map — twelve kernel modules in five layers (foundation, platform, domain, orchestration, edge), factories on top; the table below states the dependency rules exactly.*

**Dependency rules.** A module may call the public interface of modules in lower layers and of the modules listed for it below; nothing else. Where a lower module must trigger work in a higher one — a decision answer resuming a task, an applied ChangeSet re-queuing work — it does so through a registered continuation or an event the higher module subscribes to, never an import (dependency inversion).

| Module | Layer | May depend on | Notified through continuations or events |
| --- | --- | --- | --- |
| `contracts` | Foundation | — | — |
| `store` | Platform | `contracts` | — |
| `platform` | Platform | `contracts`, `store` | — |
| `intent` | Domain | `platform`, `store` | — |
| `evidence` | Domain | `intent`, `stations`, `platform`, `store` | — |
| `decisions` | Domain | `platform`, `store` | Answers start continuations registered by `change`, `work`, `delivery` |
| `memory` | Domain | `intent`, `platform`, `store` | — |
| `stations` | Domain | `platform`, `store` | Session and job events consumed by `work`, `evidence` |
| `change` | Orchestration | `intent`, `evidence`, `decisions` | Apply events consumed by `work` |
| `work` | Orchestration | `intent`, `evidence`, `decisions`, `stations`, `memory` | — |
| `delivery` | Orchestration | `evidence`, `decisions` | Delivery events consumed by `work` |
| `surface` | Edge | Every module's public interface | — |

The rules are enforced by import contracts in CI (FF-01) and by table-ownership checks (FF-07). The SDK exposes a curated subset of `contracts` and `platform` registries; factories never see `store`, `work` or `change` internals.

## Component specifications

Each module has one responsibility, owns specific state, offers a typed service interface and emits events. Specifications refine these entries; they may add, never move, ownership. Introduced-by specs are in the Roadmap's spec map.

| Module | Responsibility | Owns | Provides | Emits |
| --- | --- | --- | --- | --- |
| `contracts` | The single source of types | Pydantic models for every kernel record, typed IDs, hashing, canonical JSON | Models, `semantic_hash()`, JSON Schema export, generated TypeScript | — |
| `store` | Durable storage and execution substrate | Database schema and migrations, DBOS setup, lanes as queues, blob store and GC | Unit of work (transaction), blob put (with a lease root) and get by hash; add and release roots, queue handles | `blob.stored`, `blob.collected` |
| `platform` | Extension registry and configuration | Registries (kinds, edges, methods, capabilities, templates, subjects, adapters, decision kinds, rules), manifest loader, project configuration, versions | Registry lookups, `grindstone check`, the kernel SDK | `factory.loaded`, `config.changed` |
| `intent` | Items and their history | Items, revisions, artifacts, references and edges, lifecycles, rendering | Read by pin, graph queries, render to Markdown, transition functions | `item.revised`, `artifact.transitioned` |
| `evidence` | Proof | Check definitions, evidence records, the freshness function, regression sweep schedule | Plan checks, record evidence, `freshness()`, sweep | `evidence.recorded`, `evidence.stale` |
| `decisions` | Authority | Decisions, kinds and flags, continuations, policy rules, autonomy state, tripwire | Raise, answer, supersede, batch; register a continuation; policy evaluation | `decision.raised`, `decision.answered` |
| `memory` | What the project learned | Principle and learning indexes, full-text index; later vector index | Retrieval for context packs, search (suggestions only) | `learning.accepted` |
| `stations` | Where work runs | Station registry, tiers, lanes, workspace lifecycle, host and runner adapters | Dispatch session or job, cancel, workspace prepare/collect/discard hooks | `session.*`, `job.*` |
| `change` | Changing intent safely | ChangeDrafts, ChangeSets, impact walks, verdicts, apply and revert | Draft, walk, validate rules, apply, revert | `changeset.applied`, `changeset.reverted` |
| `work` | Running work | Tasks, runs, turns, reports, readiness, matching, limits, cooperation, template runs, context packs | Create task, dispatch, report intake, `ask`, `delegate`, `load_skill`, start template | `task.*`, `run.*` |
| `delivery` | Shipping verified output | Delivery records, idempotency ledger, adapter invocation, `observe` polling | Prepare, deliver, observe | `delivery.*` |
| `surface` | Every way in | REST API, event stream, kernel MCP server, operator authentication, AHP attach proxy | HTTP endpoints, MCP tools, streamed events | — |

**Failure modes and tests per module.**

| Module | Main failure modes | Required tests |
| --- | --- | --- |
| `contracts` | Hash drift between implementations; incompatible change | Golden hash vectors; generated-type drift (FF-02); schema compatibility (FF-03) |
| `store` | Lost write; migration on a parked workflow; blob orphaned or collected too early | Crash-and-resume; migration with parked workflows; GC property tests: no rooted blob is ever collected |
| `platform` | Invalid or hostile manifest; name collision | Loader rejection tests; conformance kit (FF-11) |
| `intent` | Illegal transition; unresolved reference; round-trip mismatch | Single-writer test (FF-08); golden Markdown round-trip |
| `evidence` | Stale evidence counted as fresh; maker-produced evidence counted | Freshness property tests; make/prove tests |
| `decisions` | Answer applied twice; stale answer accepted; policy outside its class | Exactly-once continuation tests; context-hash tests; policy class property tests |
| `memory` | Search result treated as fact | Tool tests that search never writes |
| `stations` | Duplicate session; lost event; workspace leak between runs | Idempotent create; signed-event replay; isolation tests |
| `change` | Walk misses a dependent; race between two applies | Impact property tests; concurrent-apply tests |
| `work` | Duplicate run; runaway delegation tree; stall not detected or a waiting caller failed as stalled; ambiguous match accepted silently | Crash-and-resume; delegation-tree property tests; liveness tests; matching determinism tests |
| `delivery` | Duplicate PR or push; delivery of unverified subject | Idempotency against a fake remote; evidence gate test |
| `surface` | Unauthorized call; token reuse across tasks | Auth tests; per-task token scope tests; in-memory MCP tool tests |

## Out-of-process components

Five components run outside the `grindstone` process. None holds kernel state; each can be restarted at any time without loss.

| Component | Language and base | Responsibility | Talks to | Holds |
| --- | --- | --- | --- | --- |
| Agent host (`agent-host`) | TypeScript on `@ahpd/sdk`, unmodified, with a backend wrapper and a vendored launcher in front of each ACP agent (ADR-15, ADR-42) | Starts, prompts, cancels and disposes agent sessions; runs each agent as a child process under its own Unix user; sets the workspace and the per-task MCP server; forwards permission requests; serves AHP to the UI and VS Code | The control plane's host control API (in) and event endpoint (out); model providers | Model credentials; host tokens readable only by the host process |
| Runner (`runner`) | A small Python job executor inside the project's declared image | Picks up one job directory at a time, runs the declared command, tests or reproduction steps, writes results and logs as files | The `runs` volume only | Nothing |
| Web UI (`web`) | SvelteKit (static build) with Svelte 5, served by the control plane | Decision cards, item pages and graph, ChangeSet diffs, task and template runs, delegation trees with costs, live sessions, operations view | REST and the event stream; AHP for live sessions | A session cookie |
| VS Code extension | TypeScript | Item navigation and editing, decisions, attach to live sessions | REST, events, AHP | A per-client token |
| Operator plugin | A Claude Code plugin with skills and an MCP client | Lists and answers decisions, starts commands, shows status from the operator's own Claude Code | REST through an operator MCP endpoint | A per-client token |

**Agent host control API.** Idempotent on client keys; every call names the run:

| Call | Effect |
| --- | --- |
| `create_session(run, workspace, agent, mcp_url, token, lane)` | Starts a session; returns the session ID, or the existing one for the same key |
| `prompt(session, turn, text)` | Sends a Grindstone turn |
| `answer_permission(session, request, decision)` | Answers a permission request from its decision |
| `cancel(session)`, `dispose(session)` | Stops a turn; ends and cleans up |
| `list()` | Reconciliation after restarts |

Events (session started, turn started and ended, tool call, permission requested, steering received, error, ended) are HMAC-signed, carry event IDs and turn numbers, and are delivered at least once; the control plane ignores duplicates by ID.

**Runner job format.** A job directory holds `job.json` (job ID, check IDs, method, command or test selectors, timeouts, env declaration), the materialized subject, and an empty `out/`. The runner writes `result.json` per check and log files; the control plane parses results against their schema and never trusts anything else in the directory.

## Interfaces

Four interfaces cross a process or package boundary. Each is versioned, typed from `contracts` and covered by contract tests.

### Kernel MCP surface (agents)

One MCP server inside `grindstone` (FastMCP), mounted per task run and authenticated by a per-task bearer token that names the task, the run and the capability (ADR-16). Every tool is scoped to that task's pins and grants.

| Tool | Does | Available to |
| --- | --- | --- |
| `read_item(id)`, `read_items(query)` | Returns pinned revisions, rendered to Markdown with typed fields | All modes |
| `read_blob(hash)` | Streams an input blob | All modes |
| `search(text)` | Full-text search over the project; results are suggestions | All modes |
| `report(outcome, summary, data)` | Submits the turn's report against the output contract; returns structured errors | All modes |
| `propose(items)` | Adds proposed revisions to the run's ChangeDraft | `work` mode, kinds in `produces` |
| `ask(need, question, refs, answer_schema)` | Consult a specialist, or the operator with `need="operator"` | `work` mode; consults may not ask specialists |
| `delegate(need, goal, refs, output, checks)` | Creates a child task | `work` mode, depth below two |
| `load_skill(name)` | Loads a skill from the capability's library | All modes |
| `request_permission(action, reason)` | Raises a `permission` decision | All modes |

**Suspending tools.** `delegate`, `ask(need="operator")` and `request_permission` end the turn, because no task holds a lane while it waits on a person or a child: the tool result confirms the request, the kernel records it as the turn's report with outcome `waiting`, disposes the session and frees the lane. When the child finishes or the decision is answered, the run continues in a new session on the same workspace, with the result at the top of the next prompt. A specialist consult keeps the call open until it answers, with progress notifications as keepalives, up to the consult ceiling, and then suspends the same way (ADR-38). A parent never waits on a lane its child needs: delegation frees the lane, and consults run on the read-only lane. A caller in an open consult does hold its own lane; the operations view shows it.

There are no tools to apply, transition, deliver, change configuration or reach another task (I-03, I-14, I-16). Factory domain tools (Ghidra, rea, CAD kernels) are separate tool servers in a capability's toolbox, local to the station, holding no secrets.

### Kernel SDK (factories)

`grindstone.sdk` is the only package a factory imports. It is versioned with the kernel by semantic versioning; a factory declares the range it supports.

| Area | Contents |
| --- | --- |
| Types | Base classes for item kinds, report contracts, subject kinds, decision kinds; typed IDs; hashing helpers |
| Registration | Decorators and manifest schema for kinds, edges, rules, methods, capabilities, templates, subjects, workspace providers, adapters, interface shapes |
| Adapter ports | `WorkspaceProvider` (`prepare`, `collect`, `discard`), `SubjectResolver`, `CheckMethod` (maps to an execution shape), `DeliveryAdapter` (`observe_mode`, `prepare`, `deliver`, `observe`, and the optional `publish_gate_state` and `accept`, ADR-45) |
| Read services | Read items by pin, graph queries within the factory's kinds and interfaces, blob access |
| Testing | An in-memory kernel and the conformance kit (pytest plugin) |

**Collect outcome.** `WorkspaceProvider.collect(run)` returns a `CollectOutcome`, not just a subject: the `subject` reference; `extra_checks`, which the kernel adds to the task's check plan before it enters verifying (for example a security review because a security-relevant path changed); and `permission_requests` for anything the factory's policy says needs a person (for example a protected path), each raised as a `permission` decision while the run waits, with `deny` failing the run `checks_failed`. A factory can add checks this way but never remove one, and the maker cannot influence the outcome: it is computed from the factory's policy and the actual changes.

### REST API and event stream (clients)

Resource-oriented JSON over HTTPS under `/api/v1`, generated from `contracts`, with an OpenAPI document. Commands are idempotent on a client key. The event stream is Server-Sent Events, one stream per project, each event carrying a per-project sequence number; clients resume with `Last-Event-ID`. The UI, VS Code and the operator plugin use exactly the same API; there are no private endpoints.

### Host control API and runner jobs (stations)

Described with the out-of-process components above. Higher-tier stations implement the same two protocols over an authenticated channel.

## Data model and storage layout

One PostgreSQL database (ADR-02). Each module owns one Postgres schema named after it; only that module's code reads or writes it (FF-07). Every row carries its project ID; records are append-only wherever history matters, and current state is a view over history.

| Schema | Main tables | Write pattern |
| --- | --- | --- |
| `platform` | `factories`, `project_config`, `events` (transactional outbox) | Config by load; events appended in the same transaction as the change they describe |
| `store` | `blobs` (hash, size, media type, first seen), `blob_roots` | Insert-only; GC deletes unreachable rows after grace |
| `intent` | `items`, `item_revisions` (semantic fields as JSONB, hash, provenance), `edges` (derived per revision), `artifacts` | Revisions insert-only; current pointer updated only by apply |
| `change` | `change_drafts`, `changesets`, `walk_rounds`, `verdicts` | Insert-only per round; state by transition function |
| `evidence` | `checks`, `evidence` | Evidence insert-only; freshness is a function, never a column |
| `decisions` | `decisions`, `continuations`, `policy_rules`, `policy_answers`, `autonomy_state` | Decisions by transition function; answers insert-only |
| `work` | `tasks`, `task_runs`, `turns`, `reports`, `template_runs`, `consult_cache`, `spend` | Tasks and runs by transition functions; turns, reports and spend insert-only |
| `stations` | `stations`, `sessions`, `jobs`, `workspaces` | Reconciled from host and runner events |
| `delivery` | `deliveries`, `delivery_keys` | Idempotency keys unique; state by transition function |
| `memory` | `search_documents` (full-text), later embeddings | Rebuilt from items; derived, disposable |
| `surface` | `operators`, `client_tokens` | Small, admin-only |
| DBOS | DBOS system tables | Managed by DBOS |

**Rules that hold across schemas.**

- Identifiers are typed in code and stored as text with a prefix (`REQ-0412`), or as UUIDv7 for records people never type.
- Every lifecycle column has a database enum or an equivalent constraint and is written by exactly one function (FF-08).
- Nothing derivable is stored: readiness, freshness, coverage and staleness are views or functions (FF-09).
- Cross-module references are by ID only, never by foreign key into another schema, so each module can migrate alone.
- Events are written to the outbox in the same transaction as the state change, then published to the stream; consumers are idempotent by event ID.

**Files.** `blobs` holds content by hash in a two-level directory fan-out. `repos` holds one bare mirror per repository plus private clones for delivery. `workspaces` and `runs` hold one directory per run or job, deleted when the run or job is archived. Nothing on disk is the only copy of a record.

## Contracts, versioning and code generation

**One source of truth.** Pydantic models in `contracts` define every record, report, event, API payload and manifest (ADR-05). Everything else is generated from them and checked for drift in CI (FF-02):

| Generated | From | Used by |
| --- | --- | --- |
| JSON Schema per contract | Pydantic models | Report validation, manifest validation, MCP tool schemas |
| TypeScript types | JSON Schema | Agent host, web UI, VS Code extension |
| OpenAPI document | REST routes and models | Clients, contract tests |
| SQL enums for lifecycle states | Lifecycle definitions | Database constraints |

**What is versioned.**

| Surface | Version scheme | Breaking change requires |
| --- | --- | --- |
| Kernel record contracts | Schema version per model | A migration and an upgrade path for stored data and in-flight workflows |
| Kernel MCP surface | Tool-set version advertised to the agent | A new tool set; capabilities declare which they support |
| REST API | `/api/v1` path version | A new path version; the old one kept until clients move |
| Kernel SDK | Semantic version | A major bump; factories declare a supported range |
| Factory manifests and kinds | The factory's semantic version | A major bump and an upgrade step turned into a ChangeSet |
| Agent host control API and runner jobs | Protocol version in every call | Both sides support old and new during the upgrade |

**Compatible changes** are additive: new optional or defaulted fields, new kinds, new states that old readers can ignore, new tools. The schema diff in CI (FF-03) classifies every change and fails an incompatible one without a version bump and an upgrade step.

**Hashing contract.** Semantic hashes are SHA-256 over RFC 8785 canonical JSON of semantic fields with NFC-normalised text and LF line endings; a semantic field equal to its declared default is omitted, changing a semantic default is a breaking change, and hashes are written `sha256:<hex>` (ADR-44). Golden test vectors live in `contracts` and are run by every implementation that hashes — Python and TypeScript.

## Error model and configuration

**Errors are typed values, not strings.** Every service interface returns either a result or one error from a closed, documented set, defined in `contracts`. Errors carry a stable code, a message for people, a structured detail for machines, and whether a retry can help.

| Class | Example codes | Who sees it | Handling |
| --- | --- | --- | --- |
| Validation | `report_invalid`, `reference_unresolved`, `manifest_invalid` | The caller (agent, client, loader) | Fix and resubmit; never retried automatically |
| Rule | `transition_illegal`, `coverage_missing`, `principle_conflict` | The ChangeSet or task that triggered it | Blocks approval; shown per item |
| Authority | `permission_required`, `decision_superseded`, `context_changed` | Agent or operator | Raises or refreshes a decision |
| Limit | `depth_exceeded`, `fanout_exceeded`, `storage_limit`, `cap_reached`, `consult_ceiling` | The agent, as a tool result | Agent continues or reports `blocked`; `cap_reached` and `consult_ceiling` also raise an escalation |
| Transient | `provider_unavailable`, `station_unavailable`, `remote_rejected` | The workflow step | Retried with backoff by the step's policy |
| Internal | `invariant_violated` | Logs and the operations view | The workflow stops; an escalation is raised; never swallowed |

Agents always receive errors as structured tool results they can act on; the REST API maps classes to HTTP status codes; workflows map transient errors to retries and everything else to recorded outcomes.

**Configuration is data.** It lives in versioned files, is validated before use, is hashed, and its hash is recorded on every run that used it (I-06). No agent can change it (I-14).

| Level | Where | Holds | Changed by |
| --- | --- | --- | --- |
| Instance | `grindstone.toml` and secret files | Stations, allowed images, providers, limits, price table | Operator, restart of the affected container |
| Factory | The factory package | Kinds, capabilities, templates, skills, rules, policy defaults | Installing a factory version |
| Project | `.grindstone/` files, held by the control plane and exported read-only to the repository for review; agent edits to that folder are refused at copy-back | Enabled factories and versions, grants, pins, overrides, policy rules, limits, path policies, autonomy ceiling | Operator edit, validated by `grindstone check`, applied as a recorded configuration change |

`grindstone check` validates all three levels together and refuses to start a project whose configuration is invalid; the error names the file, the field and the rule.

## Testing strategy

Every acceptance criterion is tied to the test that proves it, and each kind of risk has its own kind of test. Tests that need no model run on every commit; live runs are recorded at milestone closes.

| Test kind | Proves | Scope | Runs |
| --- | --- | --- | --- |
| Unit | Module logic in isolation | Every module | Every commit |
| Property | Impact walk reaches exactly the dependents; freshness is stale exactly when an input, subject or relevant environment field changes; delegation trees never exceed the depth or live-children caps; matching is deterministic; GC never collects a reachable blob | `change`, `evidence`, `work`, `store` | Every commit |
| Golden round-trip | Markdown render and parse yield the same hashes; hash vectors agree across Python and TypeScript; published formats are byte-stable | `contracts`, `intent`, SDLC rendering | Every commit |
| Crash-and-resume | Killing any process at any workflow step resumes with no duplicate and nothing lost | Every workflow with an external effect (FF-10) | Every commit (fast set), nightly (full matrix) |
| In-memory tool | Every MCP tool's scoping, errors and refusals | `surface` | Every commit |
| Contract | REST, MCP, host control API and runner jobs match their schemas on both sides | All interfaces | Every commit |
| Conformance kit | A factory honours namespaces, make/prove, lifecycles, adapter idempotency | Every factory (FF-11) | Every commit of the factory |
| Scripted agent | Mechanisms end to end with a deterministic fake agent that follows a script of tool calls | Kernel scenarios K1–K4, SDLC scenarios | Every commit |
| Integration | Real Postgres, real DBOS, fake GitHub and fake providers | Delivery, stations | Every commit |
| Security | Credential reachability from stations, hook execution, protected-path copy-back, injection fixtures | Deployment, SDLC workspaces | Every commit |
| Performance | Capacity envelope on a benchmark fixture | Impact walk, freshness, event latency (FF-14) | Nightly |
| Live run | The real agent does the real job | Exit criteria that name an agent | Milestone close, recorded with logs |

**The scripted agent** is an ACP-compatible fake that replays a script of tool calls and reports. It makes every mechanism testable without a model, so CI is fast, free and deterministic (ADR-19).

**Test data.** A fixture project with tagged tests, a GitHub test repository with its ruleset, the `notes` fixture factory and a benchmark project of 20,000 items are maintained alongside the code from M0.


# Factories

A factory packages one domain for the kernel. Software development is the first and the reason Grindstone exists; the others prove the kernel is general.

## What a factory is

A factory is a domain packaged for the kernel: the vocabulary, specialists, workflows and proofs of one kind of work (ADR-21). The kernel knows how to store items, run tasks, prove results and ask people; a factory tells it *what* items exist in its domain, *who* can do the work, *in what order*, and *how to prove* it.

A factory is one installable package with a **manifest** of seven parts. Every part registers names in the factory's namespace (I-18).

| Part | Declares | SDLC example | RE example (R1) |
| --- | --- | --- | --- |
| Item kinds | Kinds, fields (semantic or presentation), relations and their impact rule, lifecycle transition tables, artifacts that contain them | `sdlc.requirement`, `sdlc.criterion`, `sdlc.ticket`, `sdlc.spec` | `re.target`, `re.function`, `re.claim`, `re.report` |
| Task templates | Bounded graphs of steps: which need, mode, inputs, outputs, checks and decisions each step has | `/discover`, `/plan`, `/implement`, `/patch` | `/triage`, `/analyse`, `/confirm` |
| Capabilities | Specialists: prompt, agent, skills, toolbox, workspace mode, permissions, offers, limits, tier | Implementer, spec author, auditor, test, code and security reviewers | Static analyst, decompiler driver, finding writer |
| Check methods | Factory methods mapped onto a kernel execution shape | `sdlc.ci_suite` (shape `command`) | `re.cross_disasm` (shape `cross_tool`) |
| Subjects and workspaces | Subject kinds and how they resolve to commits or blobs; workspace providers | `git_commit` worktrees and copy-back | `re.binary` (resolves to `blob`) |
| Delivery adapters | Ports that ship verified subjects | `sdlc.github_pr` | `re.report_export` |
| Interface shapes | Which `core.interface` shapes it can provide or consume | Provides `api_contract`; consumes `format_spec` | Provides `format_spec`, `protocol_spec` |

**What a factory cannot do.** Define a new verb; bypass a ChangeSet; mark its own output verified; give an agent delivery credentials; place a kernel decision kind in a lower autonomy class; read another factory's private items; change the meaning of a `core.*` kind. Anything the grammar cannot express is a kernel change request, handled by decision record and specification — none of the factories sketched below should need one (QG-7).

**Code in a factory.** Most of a factory is data: YAML manifests, Markdown prompts and skills, JSON Schemas for report contracts. Code is allowed only for adapters (delivery, workspace providers, subject resolvers) and factory check methods, each of which must pass the conformance kit. A factory with no code at all — the `notes` fixture — is a valid factory.

## Installing, enabling and trusting factories

**Install.** A factory is a Python distribution exposing one entry point in the group `grindstone.factories`. In the MVP the SDLC factory and the `notes` fixture ship in the Grindstone repository and are installed with it; separately installable factory packages arrive in R1. At start the loader discovers entry points, validates each manifest against the manifest schema and the kernel SDK range, and registers its names. A factory that fails validation stays unloaded and is reported; the kernel still starts.

**Enable per project.** A project lists its enabled factories and pinned versions in its configuration. Only enabled factories' kinds can be created, their templates run and their capabilities matched in that project. Enabling a factory is a `scope` decision because it adds vocabulary and specialists; disabling one is refused while items of its kinds are live, and becomes an `approval` decision to retire them.

**Versioning.** Factories follow semantic versioning. A minor version may add kinds, fields, capabilities and templates; a major version may change or remove them and must ship an **upgrade step**: a declared mapping from old to new kinds and fields that the kernel turns into a ChangeSet, walked and approved like any other. Every run records the factory version and capability hash it used, so evidence from an older version stays interpretable. A project upgrades a factory only by decision, never automatically.

**Validation.** The **conformance kit** is a pytest plugin every factory runs in its own CI (FF-11). It checks that:

- the manifest loads and every name is namespaced;
- every relation has an impact rule and every lifecycle has one writer per transition;
- no capability can prove a subject it can make, and every check plan names a different prover;
- every template step names an existing need and a valid mode, and every loop is bounded;
- every factory check method maps to a kernel execution shape;
- every report contract is valid JSON Schema;
- every adapter is idempotent under replay;
- the factory's own scenarios pass against the in-memory kernel.

**Trust.** A factory's prompts and skills shape agents with tool access, and its adapters run in the control plane. Factories are therefore code the operator trusts, like a dependency: installed by the operator, pinned by version and hash, never fetched at run time, never proposable by an agent (I-14). A manifest may ask for station tiers, egress hosts and secrets; the project grants them by decision when the factory is enabled, and capabilities get no more than the project granted.

## Task templates

A task template is a factory's workflow written as data: a small directed graph of steps the kernel runs as DBOS workflows (ADR-22). The SDLC commands are templates; the same engine runs RE triage or a PCB review. Templates are what operator commands start.

**Step types.** Every step is one of six types. There is no general scripting.

| Type | What it does | Creates |
| --- | --- | --- |
| `task` | Runs one task with a need, mode, inputs, output contract, checks and limits | A task and its check tasks |
| `fan_out` | Runs one `task` step per item in a selection (each ready ticket, each function in a target), up to a concurrency limit | Many tasks, joined before the next step |
| `check` | Runs checks on a subject without a making task (audit an imported spec, re-verify after a sweep) | Check tasks |
| `change` | Turns the outputs of earlier steps into one ChangeSet and runs the impact walk | A ChangeSet and its `approval` decision |
| `decide` | Asks a person or policy a typed question, with the recommendation from the previous step | A decision |
| `deliver` | Hands verified subjects to a delivery adapter | A `delivery` decision and a delivery |

**Edges and loops.** Edges carry a condition on the previous step's outcome (`done`, `blocked`, `failed`, a decision answer). A loop is allowed only as a bounded edge — `max_rounds` is required — and exhausting it raises a decision flagged `rounds_exhausted`. The audit-and-revise loop of `/plan` is exactly such an edge: author, auditor, author, at most three rounds.

**Bindings.** Steps refer to earlier outputs by name (`steps.author.items`, `steps.analyse.blobs`), to the command's arguments, and to selections over the item graph (`items(kind="sdlc.ticket", state="ready", scope=$goal)`). Bindings resolve to pinned revisions when the step starts, so a template run is reproducible from its records.

**Commands.** Each template is exposed as an operator command in the UI, VS Code and the operator plugin. A command shows its plan — steps, needs, matched capabilities, limits — before it starts; the operator runs it at once or at the next free lane.

**What templates do not do.** They do not decide who is competent (matching), what counts as proof (check plans and criteria) or what needs a person (decision kinds and policy). Keeping those out keeps templates short: the SDLC `/implement` template fits on one screen.

## Make and prove

The one rule every factory shares is that nothing grades itself (I-15, ADR-12). It is what lets autonomy rise without trust falling.

| Role | Who | Workspace | Output | Counts as evidence |
| --- | --- | --- | --- | --- |
| Maker | The capability running the `work` task | Writable, its own | Subjects (commits, blobs) and proposed items | No |
| Maker's own checks | The same capability, inside its workspace | Same | Working notes on the run | No |
| Prover — mechanical | Check station running `command`, `test`, `reproduce`, `cross_tool` | Fresh, read-only copy of the subject | Evidence records | Yes |
| Prover — judgement | A different capability, `review` method, read-only | Read-only copy and pinned items | Structured verdicts as evidence | Yes |
| Prover — person | Operator, through `manual_check` | — | Verdict and attachments | Yes |

**What "different" means.** The prover is a different capability (by ID, not just version) from the maker of the subject and from any capability that delegated to the maker for that subject. A factory may require more: the SDLC factory runs its auditor and code reviewer on a different model from the author and implementer, in a fresh read-only session, and on a different model family once a second agent is configured (ADR-41).

**Tests written by the maker.** In SDLC the implementer writes tests, and tests are the main evidence. The rule handles this in two steps: the **test reviewer** (a prover) checks that each added or changed test verifies its criterion and was not weakened — a weakened or deleted test fails that check — and the tests then run on the check station against the copied-back commit. Implementation and its proof stay separate even though one agent typed both.

**The same rule elsewhere.** An RE analyst's finding is proven by `reproduce` (steps re-run on the binary by the check station) or `cross_tool` (a second tool agrees), never by the analyst's confidence. A CAD model is proven by a geometry check and a manufacturability review by another capability; a board by ERC/DRC on the check station and a design review; a game build by automated play tests and a manual check.

**Cost.** Proving is usually cheaper than making: check-station runs need no model, and review runs are read-only, cached by input hashes and run on the concurrent lane.

## Interface items and cross-factory work

Several factories can work in one project. They share one ledger — one item graph, one decision queue, one evidence store — but never share private items or talk. What connects them is a small number of `core.interface` items (ADR-25).

| Field | Semantic | Meaning |
| --- | --- | --- |
| `title`, `summary` | No | What the boundary is, for people |
| `shape` | Yes | A shape a factory registered: `api_contract`, `protocol_spec`, `format_spec`, `pinout`, `mechanical_envelope`, `asset_spec`, … |
| `contract` | Yes | The content, validated against the shape's JSON Schema: an OpenAPI fragment, a message layout, a pin table, a bounding box |
| `provider` | Yes | The artifact or item that must satisfy it, in one factory |
| `consumers` | Yes | Artifacts or items that rely on it, in any factories |
| `checks` | Yes | The checks that prove the provider conforms and, optionally, each consumer's use |

**How work crosses.** A factory reads interface items and the blobs they reference, never another factory's private items. When an RE analysis documents a file format, it proposes a `format_spec` interface with the RE report as provider. When SDLC later builds a parser, the parser's requirement references the interface and the parser's checks include the interface's conformance check. Both sides pin the same revision.

**How change crosses.** A semantic revision of the interface goes through a ChangeSet; the impact walk follows `review` edges into both factories, each side's affected items get verdicts, and the regression sweep stales each side's evidence. Each factory re-checks with its own provers. Neither side subscribes, polls or messages the other.

**Ownership.** The provider's factory owns the interface's lifecycle; consumers may propose revisions, which always need an `approval` decision. An interface without a provider or a consumer fails the coverage rule.

**Why this works.** Engineering disciplines that work across teams — electronics and firmware, airframe and avionics — use interface control documents for the same reason: each side changes its insides freely as long as the boundary holds, and the boundary is the one thing both sides prove. Interface items give Grindstone that property with no machinery beyond items, ChangeSets and checks.

**Within one project.** All cooperation happens inside a project. Two projects never share items; sharing across projects is done by delivering (a release, a document) and importing the result as `untrusted` intake in the other.

## The SDLC factory

The SDLC factory (`sdlc`) is the first factory and the reason Grindstone exists. It runs the agent-driven software development loop: goal, discovery, specification with independent audit, breakdown into tickets, implementation in isolated worktrees, proof against exact requirement revisions, delivery as a pull request, and findings feeding back into the specification.

*Diagram (not reproduced): the ASDLC loop — eight stages (the rows of the table below) and five decision points: scope, specification, breakdown, findings that change intent, and delivery.*

**One ledger, two moving parts.** The factory keeps specification and code moving together. Every ticket implements requirements by typed reference; every acceptance criterion names the requirement it verifies and its method; every commit is proven against the exact revisions it was built from. When implementation finds something the specification did not foresee, the implementer proposes a finding and the change flows back through a ChangeSet — the loop closes in the specification, not in a chat.

**The loop at a glance.**

| Stage | Command | Makes | Proven by | Decided by a person |
| --- | --- | --- | --- | --- |
| Initialise | `/init` | Principles, conventions skill, project configuration | Repository scan check; operator review | Principles, enabled factories, grants |
| Discover | `/discover` | Product, features, milestones | Auditor | Scope and every feature |
| Specify | `/plan` | Specifications: requirements, criteria, design decisions | Auditor, bounded rounds; manifest rules | Each specification |
| Break down | `/plan` | Tickets with dependencies and declared paths | Coverage rules | The breakdown |
| Implement | `/implement` | Commits in a worktree; findings; learnings | CI suite on the check station; test, code and security reviewers | Findings that change intent |
| Deliver | part of `/implement` | Pull request with an evidence table | Delivery port checks freshness | Merge (`delivery`) |
| Patch | `/patch` | A small specification change plus tickets | Auditor; rules | The change |
| Repair | `/repair` | Fixes for stale or failing evidence | Same as Implement | Delivery; any scope change |

**Beyond the core loop.** Security, performance and accessibility reviewers are capabilities any step can name as provers; the implementer can consult them mid-task; and SDLC provides code to other factories through delegation and interface items (S6).

## SDLC kinds, capabilities and templates

### Item kinds and artifacts

| Kind | ID form | Key semantic fields | Relations (impact rule) | Rendered in |
| --- | --- | --- | --- | --- |
| `sdlc.product` | `PRD` | Goal, users, scope, non-goals, success measures | — | Product definition |
| `sdlc.feature` | `FEAT-n` | Outcome, users, priority, milestone | `derives_from` product (review) | Product definition |
| `sdlc.milestone`, `sdlc.exit_criterion` | `M<n>`, `M<n>-kk` | Outcome; observable condition | `of` milestone (review) | Roadmap |
| `sdlc.spec` (artifact header) | `SPEC-nn` | Milestone, status, cited principles and decisions, exit criteria delivered | `delivers` exit criterion (review) | Specification |
| `sdlc.requirement` | `REQ-nnxx` | One testable statement, priority, rationale | `derives_from` feature, `constrained_by` principle, `uses` interface (review) | Specification |
| `sdlc.criterion` | `AC-nnxx-k` | Given/when/then or measurable condition, method, required | `verifies` requirement (review) | Specification |
| `sdlc.design_decision` | `DEC-nnxx` | Decision, reason, rejected options | `decides_for` requirement (review) | Specification |
| `sdlc.ticket` | `TKT-nnnn` | Goal, declared paths, estimate | `implements` requirements, `after` tickets (review) | Plan |
| `sdlc.adr` | `ADR-nn` | Context, decision, rejected options, consequences, status | `supersedes` ADR (review) | Decision log |

The kernel kinds `core.principle`, `core.finding`, `core.learning`, `core.observation` and `core.interface` are used as they are. Only the specification is an artifact with a header of its own; the other documents in the last column are generated lists, and tickets, ADRs and milestones are standalone items with their own lifecycles.

**Lifecycles.** A requirement goes `draft → approved → implemented → verified` and may go `→ retired` by ChangeSet; a ticket goes `proposed → ready → in_progress → in_review → done`, with `blocked` and `cancelled` reachable. `implemented` and `verified` are written by the kernel from task and evidence state, never by an agent. Lifecycle state is not hashed, so moving a requirement to verified never stales the evidence that verified it.

**Artifacts** render to Markdown under `docs/` in the repository on delivery, so the specification travels with the code and diffs in review; the ledger remains the source of truth.

**Coverage rules.** Every approved requirement has at least one criterion; every criterion names a method; every ticket implements at least one requirement; every requirement in a milestone is covered by tickets before its `/implement` runs; every milestone exit criterion is delivered by at least one specification.

### Capabilities

| Capability | Offers (need · modes) | Workspace | May prove | Default agent | From |
| --- | --- | --- | --- | --- | --- |
| `sdlc.implementer` | `sdlc.implement` · delegate | write, git worktree | No | Claude Code | M1 |
| `sdlc.test_reviewer` | `sdlc.review.tests` · check | read-only | Yes | Claude Code | M1 |
| `sdlc.spec_author` | `sdlc.specify` · delegate | write, items only | No | Claude Code | M2 |
| `sdlc.auditor` | `sdlc.audit.spec` · check, consult | read-only | Yes | Claude Code, on a different model from the spec author | M2 |
| `sdlc.impact_reviewer` | `core.review.impact` · check | read-only | Yes | Claude Code | M3 |
| `sdlc.code_reviewer` | `sdlc.review.code` · check, consult | read-only | Yes | Claude Code, on a different model from the implementer | M3 |
| `sdlc.security_reviewer` | `sdlc.review.security` · check, consult | read-only | Yes | Claude Code | M3 |
| `sdlc.discoverer` | `sdlc.discover` · delegate | write, items only | No | Claude Code | M4 |
| `sdlc.planner` | `sdlc.breakdown` · delegate | write, items only | No | Claude Code | M4 |
| `sdlc.advisor` | `core.advise` · consult | read-only | No | Claude Code | M4 |
| `sdlc.repairer` | `sdlc.repair` · delegate | write, git worktree | No | Claude Code | M5 |

**Independence.** The auditor and the code reviewer run on a different model from the author and the implementer, in a fresh read-only session that shares none of their context; once a second agent is configured they default to a different model family (ADR-41). This is SDLC policy above make/prove; a project may relax it only by a `principle`-flagged decision.

**Skills.** `sdlc.repo-conventions` (generated by `/init`), `sdlc.security-basics`, `sdlc.testing-patterns`, `sdlc.migration-safety`, `sdlc.api-design`.

**Toolboxes.** The implementer gets the kernel MCP tools plus the agent's file and shell tools inside its worktree, with egress only to the package registries the project granted. Reviewers get the kernel read tools, `report` and a read-only shell inside a copy of the subject. No SDLC capability holds GitHub credentials (I-08).

### Templates and commands

| Command | Steps | People decide | From |
| --- | --- | --- | --- |
| `/init` | `check` repository scan → `task` draft principles, conventions skill and configuration → `change` → `decide` | Principles, enabled factories, grants | M4 |
| `/discover` | `task` discoverer interviews through `ask(operator)` and drafts product, features, milestones → `check` auditor → `change` → `decide` | Scope and every feature | M4 |
| `/plan <milestone>` | `task` spec author ↔ `check` auditor (max 3 rounds) → `change` → `decide` → `task` planner → `check` coverage → `change` → `decide` | Specifications, then tickets | Specify M2, break down M4 |
| `/implement [tickets]` | `fan_out` over ready tickets: `task` implementer → `check` CI suite, test reviewer, code reviewer, security reviewer by path policy → `change` findings and learnings → `deliver` | Delivery; findings that change intent | Thin M1, reviewers M3 |
| `/patch <request>` | `task` spec author drafts the smallest change → `check` auditor → `change` → `decide` → `/implement` on its tickets | The change, then delivery | M4 |
| `/repair` | `check` regression sweep → `fan_out` `task` repairer per failure → `check` → `deliver` | Delivery; scope if new intent is needed | M5 |

**Existing repositories.** `/init` followed by `/discover` in import mode drafts items from existing documents and code as `untrusted` drafts the operator approves. Generating a full baseline specification from an existing codebase is R2.

## SDLC workspaces, checks, delivery and decisions

**Workspace provider.** The SDLC factory owns git workspaces (ADR-27). For each implementing run it creates a worktree from the bare mirror on `repos`, at the pinned base commit, on branch `gs/<ticket>/<run>`, under `workspaces/<run>`. The agent station mounts only that worktree. The kernel sees the workspace only through the provider's hooks `prepare(run)`, `collect(run) → subject` and `discard(run)`.

**Copy-back.** `collect` commits whatever the agent left, with hooks disabled, then applies path tiers:

| Tier | Paths | Rule |
| --- | --- | --- |
| Free | Within the ticket's declared paths | Copied back as committed |
| Reviewed | Tests, fixtures and docs outside the declared paths | Copied back; the test reviewer or code reviewer must pass them explicitly |
| Protected | CI configuration, `.grindstone/`, lockfiles changed without their manifest, files the project marks protected | Refused: the run fails `checks_failed` with the list, unless a `permission` decision allowed it for this task |

The result is a `git_commit` subject on the mirror; the worktree is discarded. Checks and delivery use only that commit.

**Path policy at collect time.** `collect` returns a `CollectOutcome` (Components tab): the subject, the extra checks the path policy requires for the files actually changed — `sdlc.review.security` for authentication, crypto, input parsing, dependency manifests and infrastructure files; an explicit pass by the test or code reviewer for reviewed-tier files — and a permission request for each protected path. The kernel adds the checks to the task's plan and raises the permission decisions before verifying starts. Projects extend the path policy in their configuration.

**Check method.** `sdlc.ci_suite` (shape `command`) runs the project's declared lint, type check, build and test commands on a check station from a fresh checkout of the subject, and maps results to criteria by test annotations (`@verifies AC-0412-3`). A required criterion with method `test` and no annotated test fails the suite.

**Environment fingerprint.** The runner image digest plus the toolchain versions the project declares (runtime, package manager, lockfile hash). Changing the lockfile therefore stales test evidence.

**Delivery.** `sdlc.github_pr` prepares a pull request from the subject commit to the target branch, with a body generated from the ledger: tickets, requirements and criteria covered, evidence with freshness, findings raised, decisions taken. It posts one verification status. Delivery is idempotent by `(project, ticket, subject commit)`. `observe` reports merge, close, review comments and failing external checks back; review comments arrive as `untrusted` findings. Merging is a `delivery` decision at L0–L2; the GitHub App key lives only in the control plane.

**Delivery modes** (ADR-40). The adapter observes, at project setup and before every delivery, whether the target branch's rules actually require the verification status from the Grindstone App. **Enforced:** GitHub itself refuses an unverified merge. **Unenforced** (for example, rulesets on a private repository on GitHub's free plans): Grindstone performs the merge itself after the `delivery` decision, re-checking freshness and passing the head SHA it verified so a concurrent push fails the merge, and `observe` reports any merge of a Grindstone pull request it did not perform, and any change to a published file on the default branch that did not come through a delivery, as a high-severity `untrusted` `delivery_bypass` finding. The mode is shown on the project and on every delivery card; a switch from enforced to unenforced raises an escalation before the next delivery.

**Decisions and autonomy.** SDLC maps its decisions to eligibility classes and ships default L2 policy rules a project starts from:

| Decision | Class | Recommendation from | Shipped L2 rule |
| --- | --- | --- | --- |
| `approval` of a specification or ticket ChangeSet | `l2` | Auditor's final verdict | Approve if the auditor passed, rules pass and no flag is set |
| `approval` of a findings or learnings ChangeSet | `l2` | Impact reviewer | Approve learnings only; findings that amend requirements wait |
| `delivery` of a pull request | `l3` | Fixed: deliver when all required evidence is fresh and passing | None before L3 |
| `escalation` after a failed run | `l2` | Fixed: retry once with the same capability | Retry once for `stalled`, `rate_limited`, `provider_error`, `host_lost` |
| `suggestion` from an advisory reviewer | `l2` | The reviewer | Dismiss style-only suggestions; queue others |
| `permission` for a protected path | `never` | The implementer's stated reason | — |
| `sdlc.merge_conflict` | `l2` | Fixed: rebase and re-run checks | Rebase if conflicts are only in lockfiles or generated files |
| `sdlc.flaky_test` | `l2` | Fixed: re-run once, then quarantine as a finding | Re-run once |

New projects start at L1. The operator moves a project to L2 once its first milestone has delivered through Grindstone and the tripwire has stayed quiet for a set number of deliveries (default 10). At every level, principles, scope, protected paths, anything `untrusted`, any security finding of medium severity or higher and every irreversible action stay with a person.

## SDLC scenarios

Six scenarios define what the SDLC factory must do; each becomes an end-to-end test with the scripted agent, and a live run where a real agent is the point. S1–S4 are the core loop; S5 and S6 show cooperation.

### S1 — One ticket, end to end (M1)

The operator writes TKT-0001 by hand, implementing REQ-0101 with AC-0101-1 (method `test`). `/implement TKT-0001` creates a task with need `sdlc.implement`; the implementer works in `gs/TKT-0001/r1`, writes code and a test annotated `@verifies AC-0101-1`, and reports `done`. `collect` commits and copies back; the CI suite passes on the check station; the test reviewer confirms the test verifies the criterion. A `delivery` decision appears with the recommendation "deliver"; the operator approves; the pull request opens with its evidence table and the verification status succeeds. After merge, `observe` reports it and REQ-0101 moves to `verified`.

### S2 — Specify a milestone with independent audit (M2)

`/plan M1` runs the spec author against the milestone's features and exit criteria. The auditor fails round one with two structured findings — an untestable requirement and an uncovered exit criterion; the author revises; round two passes. The ChangeSet is walked, rules pass, and an `approval` decision lists the new specification. The operator approves; requirements and criteria become `approved` with provenance pointing at both runs.

### S3 — Implementation finds a gap in the specification (M3)

While implementing TKT-0042 the implementer finds that REQ-0412 cannot hold under concurrent writes. It proposes FND-0007 with a suggested amendment and reports `blocked`. The walk reaches REQ-0412, its criteria, TKT-0042 and TKT-0043; the impact reviewer proposes verdicts (`amend` REQ-0412, `unaffected` TKT-0043). On approval the requirement is revised; TKT-0042 resumes against the new revision; evidence pinned to the old REQ-0412 is stale and re-checked.

### S4 — A change of intent from the operator (M3)

The operator edits a feature to drop a platform. The walk reaches two specifications, five requirements and three tickets, one in progress. Verdicts invalidate two requirements and cancel one ticket; its running implementation is cancelled cleanly and its worktree discarded; the remaining work continues. The next day the operator reverts; the revert restores the requirements and re-queues the ticket.

### S5 — The implementer consults a security specialist (M3)

Implementing a password-reset ticket, the implementer loads `sdlc.security-basics`, then calls `ask(need="sdlc.review.security", question="Is a 6-digit code with 15-minute expiry acceptable here?", refs=[REQ-0520])`. The security reviewer answers read-only: no — recommend a signed single-use link and rate limiting, citing the project's account-recovery principle. The implementer follows the advice. Because the path policy marks `auth/` as security-relevant, the security reviewer also runs as a *required check* on the resulting commit — a separate task proving someone else's subject — and passes it.

### S6 — Another factory delegates code to SDLC (R1)

In a project with SDLC and RE enabled, an RE analyst has documented a proprietary file format and proposed IF-0003 (shape `format_spec`, provider: the RE report). It calls `delegate(need="sdlc.implement", goal="A Python parser for this format", refs=[IF-0003], output={kind: "sdlc.ticket"}, checks=[IF-0003 conformance])`. The kernel creates an SDLC ticket and implementation task; the implementer builds the parser; the CI suite and the conformance check (parsing the RE team's sample blobs) pass; a pull request is delivered. The RE task resumes with the delivered commit pinned. When the analyst later corrects a field width in IF-0003, the parser's evidence goes stale and `/repair` picks it up.

## Later factories, sketched

These sketches test the kernel; they are not commitments. Each must fit the seven manifest parts with no kernel change; where one needs a station tier the MVP lacks, the release that brings it is named. Only the RE static factory is planned (R1).

|  | Reverse engineering | Testing and security | CAD and 3D | PCB and hardware | Game development |
| --- | --- | --- | --- | --- | --- |
| Namespace | `re` | `qa` | `cad` | `pcb` | `game` |
| Key item kinds | Target, function, structure, claim, report | Test plan, test case, threat, vulnerability | Part, assembly, constraint, drawing | Requirement, schematic block, net class, board | Design pillar, mechanic, level, asset spec |
| Subjects | `re.binary` (blob), annotated database (blob) | `git_commit`, deployed snapshot (blob) | Model files (blob set) | KiCad project (commit) | Build (blob set), repository (commit) |
| Makers | Static analyst (Ghidra headless, rea), finding writer | Test author, fuzz harness author | Modeller (CadQuery, OpenSCAD) | Schematic author, layout assistant | Designer, gameplay implementer |
| Provers | `reproduce`, `cross_tool`, reviewer | Test run, DAST scan, reviewer | Geometry and interference checks, manufacturability review | ERC/DRC on the check station, design review, manual bench check | Automated play tests, performance capture, manual playtest |
| Delivery | Report export, tracker issue | Issue or PR comment | STEP/STL export, PR to a model repository | Fabrication package, PR | Build artifact, PR |
| Interfaces | Provides `format_spec`, `protocol_spec` | Consumes `api_contract` | Provides `mechanical_envelope` | Provides `pinout`; consumes `mechanical_envelope` | Consumes `asset_spec` |
| Tier needed | T1 for trusted samples; T2 for untrusted or dynamic (R3) | T1; T2 for hostile targets (R3) | T1 | T1; T3 for bench and flashing (R4) | T1; T3 with GPU for play tests (R4) |

**Reverse engineering (R1).** RE comes first after SDLC because it exercises what SDLC does not: blob subjects instead of commits, `reproduce` and `cross_tool` checks, findings as the main output, untrusted inputs by default, and cooperation in the other direction (S6). Its capabilities drive Ghidra headless and rea through tool servers in their toolboxes, on T1 stations with no network. Findings are proven by reproduction: the check station re-runs the analyst's recorded script on the pinned binary and compares outputs. In-house tools join as tool servers in a capability's toolbox.

**Testing and security as a factory.** In the MVP, security and test reviewers are SDLC capabilities (S5). A separate `qa` factory becomes worthwhile when testing has long-lived intent of its own — test plans, threat models, campaigns — that outlives any ticket; SDLC then consults or delegates to it, and threat models become interface items both factories pin.

**Hardware and computer use (R3, R4).** T2 and T3 stations are additions to the station registry, not kernel changes: a capability asks for a tier, the project grants it, and I-20 keeps credentials away and asks a person before anything irreversible unless an approved runbook item covers that exact action. Computer-use agents run on T3 stations as ordinary capabilities with a screen-and-input toolbox; their evidence is screenshots and recordings as blobs, proven by `manual` checks or by a second agent replaying the steps (`reproduce`).


# Decisions

One record per choice that is expensive to reverse.

## How decision records work

Forty-six records cover every choice that is expensive to reverse. Each states the decision, why it was made, what it commits the specifications to, and the options rejected with their reasons. Every record is **Accepted**, on 17 October 2026 except ADR-45 and ADR-46 (18 October 2026); ADR-20 is superseded by ADR-37. Records 37 to 39 come from the operator's answers to the open questions at the M0 kickoff; ADR-40 from the decision to stay on GitHub's free plan, where rulesets on private repositories are not enforced; ADR-41 from the decision to work with Claude only for now. ADR-42 and ADR-43 come from the M0 spike results (SPK-1, SPK-5) and ADR-44 from SPEC-01; the operator accepted all three on 17 October 2026. ADR-45 and ADR-46 come from the first review of the M1 specifications; the operator accepted both on 18 October 2026.

**Append-only.** From the start of M0 (foundation v4.2) records are never edited: a change is a new record that supersedes an old one, and the superseded record keeps a pointer to its successor.

**When to write a record.** A specification author who needs a choice that crosses a module or factory boundary, changes a contract others rely on, adds a component or dependency, adds a kernel kind, check shape, step type, decision class or station tier, or contradicts a record here proposes a new record instead of deciding inside the specification. Choices inside one module or one factory belong to its specification.

**What binds.** The decision binds. Specific values inside it — caps, budgets, counts, key names, default lists — are seed defaults owned by the implementing specification, which may change them with a stated reason. Versions are resolved at M0 from primary sources.

**Index.**

| ADR | Title | Area |
| --- | --- | --- |
| 01 | A Python modular monolith with three supporting containers (amended by 46) | Platform |
| 02 | PostgreSQL is the only store of records | Platform |
| 03 | DBOS runs every workflow; waits on people park | Platform |
| 04 | A content-addressed blob store owned by the control plane | Platform |
| 05 | Pydantic is the single source of types | Platform |
| 06 | A static SvelteKit UI; one API for every client | Platform |
| 07 | A domain-neutral kernel with a grammar of three nouns and four verbs | Kernel |
| 08 | Items are namespaced, typed and hashed; the kernel defines five kinds | Kernel |
| 09 | One typed relation graph, derived from content, with three impact rules | Kernel |
| 10 | Every intent change is a ChangeSet walked to a fixed point | Kernel |
| 11 | Freshness is computed from inputs, subject and environment | Kernel |
| 12 | Checks prove subjects; makers never prove their own work | Kernel |
| 13 | Rules are registered Python functions over SQL | Kernel |
| 14 | One task model for all work | Execution |
| 15 | Grindstone runs its own thin AHP host; agents connect over ACP | Execution |
| 16 | Agents act only through a per-task kernel MCP surface | Execution |
| 17 | Stations have tiers T0 to T3 | Execution |
| 18 | Agents in order: Claude Code, then Codex (amended by 41) | Execution |
| 19 | A scripted agent proves mechanisms in CI | Execution |
| 20 | Every task tree has a budget (superseded by 37) | Execution |
| 21 | Factories are the unit of extension | Factories |
| 22 | Templates are bounded graphs of six step types | Factories |
| 23 | Capabilities define specialists as data; skills load on demand | Factories |
| 24 | Cooperation through three verbs and deterministic matching | Factories |
| 25 | Factories integrate through interface items | Factories |
| 26 | Delivery is a kernel port with factory adapters (amended by 45) | Factories |
| 27 | The SDLC factory owns git workspaces, copy-back and GitHub delivery | Factories |
| 28 | Every question to a person is one typed decision | People |
| 29 | An advisor recommends; change classes have computed floors | People |
| 30 | Autonomy is decided by fixed rules, with a tripwire | People |
| 31 | Project memory is principles and learnings; search only suggests | People |
| 32 | The outer loop maps external signals by fixed code | People |
| 33 | Discovery comes before planning; small changes take a fast path | People |
| 34 | Walking skeleton first; Grindstone builds itself | Scope |
| 35 | The foundation holds commitments; specifications hold designs | Scope |
| 36 | The MVP is SDLC on the kernel, with cooperation | Scope |
| 37 | Limits bound runaway work; cost is recorded, never gating | Execution |
| 38 | A consult holds the call open until it answers, under a ceiling | Execution |
| 39 | Skills are materialized per session outside the workspace and returned inline | Execution |
| 40 | Delivery states whether the remote enforces the gate | Factories |
| 41 | Claude Code is the only agent until the operator adds another | Execution |
| 42 | The agent host uses its packages unmodified, behind a launcher and a backend wrapper | Execution |
| 43 | A skill's tools are listed from session start and refused until the skill is loaded | Execution |
| 44 | Semantic hashes omit fields at their default | Kernel |
| 45 | The delivery port reports the gate and completes deliveries through optional operations | Factories |
| 46 | Dependencies are the latest stable release compatible with the other pins | Platform |

## Platform and runtime

#### ADR-01 — A Python modular monolith with three supporting containers

**Status.** Amended by ADR-46 (latest compatible release, exceptions recorded).

**Decision.** Everything Grindstone owns is one Python process (`grindstone`) in one repository, deployed with Docker Compose next to three supporting containers: a thin TypeScript agent host (`agent-host`), a credential-less `runner` on the project's own toolchain image, and `postgres`. Four volumes: `blobs` and `repos` (control plane only), `workspaces` (control plane and agent host), `runs` (control plane and runner). Every dependency is the latest stable release, pinned exactly; images are pinned by digest; upgrades are deliberate commits that pass CI.

**Why.** One operator on one machine needs few moving parts; the only separations are the ones security and the agent ecosystem require. **Consequences.** Module boundaries are enforced by import contracts, not networks (FF-01); the deployment is one file. **Rejected:** microservices and a message broker (operational cost with no user benefit); Kubernetes (one machine).

#### ADR-02 — PostgreSQL is the only store of records

**Decision.** Grindstone tables, DBOS system tables, the relation graph, blob metadata, the full-text index and, later, vector embeddings all live in one PostgreSQL. Each module owns one schema. File content lives in the blob store (ADR-04), described by rows here.

**Why.** One backup, one transaction boundary, one thing to operate; recursive SQL covers graph walks and full-text and pgvector cover search at this scale. **Consequences.** A ChangeSet applies intent, decisions and task effects in one transaction. **Rejected:** a graph database or a separate vector database (a second store and no cross-store transactions).

#### ADR-03 — DBOS runs every workflow; waits on people park

**Decision.** DBOS Transact, in the same process, runs all workflows, queues, schedules and bounded waits; workflow and step IDs are idempotency keys. A wait on a person never holds a workflow open: the decision stores a typed continuation and its answer starts the continuation exactly once. Only agent turns and check jobs wait inside a workflow, each capped; provider rate-limit waits park. Agent sessions run as child workflows on the station lanes: writing (one at a time by default) and read-only (small configurable concurrency).

**Why.** Durable execution in Postgres with no extra service; parking keeps long human waits out of workflow history and survives upgrades. **Rejected:** agent orchestration frameworks (they orchestrate prompts, not durable side effects); Temporal (an extra cluster).

#### ADR-04 — A content-addressed blob store owned by the control plane

**Decision.** Files that are not git commits — binaries under analysis, reports, models, logs, build outputs, evidence attachments — are stored by SHA-256 on the `blobs` volume, written only by the control plane, with metadata in Postgres. Declared outputs are copied out of workspaces when a run ends; every blob is rooted from the moment it is written — a lease owned by its producing run, joined by the referencing module's root in the same transaction — and garbage collection removes only unrooted blobs older than a grace period.

**Why.** Non-code domains produce and consume files that have no repository; content addressing makes freshness and deduplication free. **Rejected:** files in Postgres (size, backups); S3-compatible storage in the MVP (another service; the same interface can be backed by it later); leaving files in workspaces (neither durable nor addressable).

#### ADR-05 — Pydantic is the single source of types

**Decision.** Pydantic models are the only hand-written types. JSON Schemas, TypeScript types, MCP tool schemas, the OpenAPI document, manifest schemas and SQL enums are generated and drift-checked in CI. IDs are typed per kind; relations are typed fields with cardinality; lifecycle states are enums with transition tables; every JSON column is read through its model; events form a discriminated union. Every stored payload has a schema version; CI fails a breaking change without a version bump and an upgrade path.

**Why.** Type safety across Python, TypeScript, agents and stored data from one source. **Rejected:** schema-first IDL with generated Python (two toolchains, weaker validation); hand-maintained TypeScript types (drift).

#### ADR-06 — A static SvelteKit UI; one API for every client

**Decision.** The UI is SvelteKit (static adapter) with Svelte 5, served by the control plane behind operator login, using the generated REST client and Server-Sent Events. Graphs use `@xyflow/svelte` behind one graph component. Live agent sessions are watched and steered in the browser through AHP, with the connection token served only after login; VS Code attaches to the same host. The UI, VS Code and the operator plugin use one public API; there are no private endpoints.

**Why.** No Node server in production; one live-session protocol for every client; no client can do what another cannot audit. **Consequences.** UI pages hold no domain logic. **Rejected:** a server-rendered Node frontend (another runtime); proxying sessions through the control plane (re-implements AHP).

## Kernel model

#### ADR-07 — A domain-neutral kernel with a grammar of three nouns and four verbs

**Decision.** The core is a kernel that knows three nouns — Item, Capability, Station — and four verbs — Task, Check, ChangeSet, Decision — on a substrate of blobs, subjects, a delivery port and interface items. Everything domain-specific, including all of software development, is a factory on top. The kernel never imports a factory.

**Why.** Durability, provenance, freshness, independent proof, reviewed change, decisions and cost control are the same problem in every domain; solving them once lets software development, reverse engineering, hardware and other work share them. **Consequences.** Kernel specifications are written without factory names (FF-12); the SDLC factory is built alongside the kernel from M1 so no seam goes untested; a code-free fixture factory proves neutrality at M2. **Rejected:** an SDLC-shaped core with plug-ins for other domains (every new domain bends SDLC types); a general workflow engine with agents as steps (no typed intent, no freshness, no proof); a multi-agent framework (orchestrates prompts, not durable, auditable work).

#### ADR-08 — Items are namespaced, typed and hashed; the kernel defines five kinds

**Status.** Amended by ADR-44 (defaults omitted from the hash).

**Decision.** An item is a typed record with a stable ID, a kind in a namespace (`core.*`, `sdlc.*`, `re.*`), fields marked semantic or presentation, typed references, mentions `[[ID]]` and embeds `![[ID]]`. Its semantic hash is SHA-256 over RFC 8785 canonical JSON of the semantic fields after NFC and LF normalisation. Revisions are immutable and carry provenance. Artifacts are containers with a header item; any kind may declare a lifecycle — a transition table with one writer per transition — whose state is stored beside the item and never hashed. The kernel defines `core.principle`, `core.learning`, `core.finding`, `core.observation` and `core.interface`.

**Why.** A shared item model is what makes impact analysis, freshness and review work across domains; namespaces let factories add vocabulary without collisions. **Rejected:** free-form documents with embedded metadata (no reliable impact walk); one universal schema for every domain (forces every factory into one shape); kind inheritance (couples factories to each other's kinds).

#### ADR-09 — One typed relation graph, derived from content, with three impact rules

**Decision.** Relations are derived from item content — typed reference fields, mentions and embeds — and stored as edges per revision; they are never edited separately. Edge types are registry entries with endpoints, an inverse name, membership in check dependency sets and an impact rule: `review` for typed dependencies, `notify` for mentions, `render` for embeds. An unlinked item ID in text becomes a link suggestion.

**Why.** One graph, always consistent with the text, and impact proportional to the kind of link: only real dependencies demand verdicts. **Rejected:** a separately maintained link table (drifts from the text); every link demanding a verdict (noise drives people around the system).

#### ADR-10 — Every intent change is a ChangeSet walked to a fixed point

**Decision.** Every change to intent — from an operator edit, task output, a delegation result, intake or a revert — is a ChangeSet: draft, impact rounds one hop at a time with a recorded verdict for every item reached by a `review` edge, rules, approval, one atomic apply with a base-revision check, serialized per project. Amendments join the set and extend the walk; a round limit raises a decision. A moved base sends the set back for a re-walk. Running tasks receive applied changes at their next turn, or are cancelled if a pinned item was removed; decisions with changed context are superseded. A revert applies the inverse as a new ChangeSet.

**Why.** Safe change is the product's core promise; a fixed point means nothing affected is left unexamined. **Rejected:** applying edits directly and checking later (consequences land unseen); locking items during work (blocks the operator).

#### ADR-11 — Freshness is computed from inputs, subject and environment

**Decision.** Every evidence record stores the semantic hashes of its inputs, the subject version and an environment fingerprint. Freshness is a function that compares them with current values on read and names any mismatch; it is never stored. Presentation changes never stale evidence; environment changes stale only methods that declare the environment relevant.

**Why.** A stored "stale" flag drifts from the truth the moment someone forgets to set it; a computed one cannot. **Rejected:** stored freshness flags updated by triggers (drift, ordering bugs); time-based expiry (stale for the wrong reasons).

#### ADR-12 — Checks prove subjects; makers never prove their own work

**Decision.** A check verifies a target item against a typed subject by one of six methods — `command`, `test`, `reproduce`, `cross_tool`, `review`, `manual` — or a factory method mapped onto one. Evidence that gates done comes only from a credential-less check station, a different capability in read-only mode, or a person. A maker's own runs are working notes.

**Why.** Agents grading their own work is the central failure of agent-driven development; one rule applied everywhere fixes it for code, findings, models and boards alike. **Consequences.** The SDLC test reviewer is a required prover; checks run on a fresh copy of the subject. **Rejected:** trusting maker-reported results; one check method per domain (unbounded kernel growth).

#### ADR-13 — Rules are registered Python functions over SQL

**Decision.** Structural rules — every requirement covered, every interface with a provider and a consumer, no dependency cycle, no unresolved reference at approval — are Python functions registered by the kernel or a factory, built on a few SQL helpers. Each declares the approvals it gates, the finding type it raises and its severity; a nightly sweep runs them all.

**Why.** A modest number of rules does not justify a rule language. **Rejected:** a declarative rule language compiled to SQL (a compiler to build and maintain for little gain).

## Execution, stations and agents

#### ADR-14 — One task model for all work

**Decision.** Every unit of agent or check work is a task with a mode (`work`, `consult`, `check`), pinned inputs, an output contract, a check plan, a budget, a tier and a parent. Attempts are task runs in fresh workspaces; runs are sessions and Grindstone-numbered turns; each turn ends with exactly one validated report. Failures have typed causes with retry rules. Delegating and asking the operator end the turn with outcome waiting, close the session and free the lane; the run continues in a new session on the same workspace when the result arrives, so no waiting task holds a lane.

**Why.** One model gives one place for retries, budgets, provenance and cancellation, and makes consults and delegations ordinary tasks. **Rejected:** separate models per kind of work (duplicated recovery logic); unstructured sessions with no report contract (no reliable end state).

#### ADR-15 — Grindstone runs its own thin AHP host; agents connect over ACP

**Status.** Amended by ADR-42 (no patch; a launcher and a backend wrapper).

**Decision.** All agent work runs as AHP sessions on a host built on `@ahpd/sdk`, with a vendored, patched ACP agent plugin; agents connect over ACP and run as child processes under their own Unix user. The control plane drives sessions through a small typed control API that is idempotent on client keys, and receives HMAC-signed, at-least-once events with event IDs and turn numbers. Permission requests are answered only through the control API, from their decision. Steering prompts from the UI or VS Code are recorded but never end a run. Correctness never depends on a session surviving a restart.

**Why.** Grindstone needs per-session MCP servers, working directory, credentials and metadata that stock hosts do not offer; a thin owned host keeps the browser and VS Code as plain clients. **Rejected:** a stock host daemon (static plugin configuration); VS Code's agent host (cannot host ACP agents with per-session MCP); a Python AHP client (no mature client; a narrow typed API is easier to make idempotent).

#### ADR-16 — Agents act only through a per-task kernel MCP surface

**Decision.** Each run gets an MCP server scoped to its task, authenticated by a per-task token naming the task, run and capability, with tools to read pinned items and blobs, search, report, propose, `ask`, `delegate`, `load_skill` and request permission. There are no tools to apply, transition, deliver, change configuration or reach another task. The server is FastMCP inside the control plane. Factory domain tools run as separate, secret-less tool servers on the station.

**Why.** One narrow, typed surface makes "agents propose, the kernel decides" enforceable and testable in memory. **Rejected:** letting agents call the REST API (too broad); per-factory servers for kernel actions (duplicated enforcement).

#### ADR-17 — Stations have tiers T0 to T3

**Decision.** Stations are agent stations or check stations at a tier: T0 read-only, T1 container (MVP), T2 microVM per run (R3), T3 full VM with a desktop or passed-through devices (R4). Capabilities state a minimum tier; projects grant tiers. No station holds a control-plane credential; stations that touch untrusted targets or hardware ask a person before any irreversible action unless an approved runbook covers it.

**Why.** Untrusted binaries, computer use and hardware need stronger isolation than trusted code; naming the ladder now keeps the kernel unchanged when it is climbed. **Rejected:** microVM isolation in the MVP (cost with no MVP user); per-factory isolation schemes (inconsistent guarantees).

#### ADR-18 — Agents in order: Claude Code, then Codex

**Status.** Amended by ADR-41 (Codex deferred).

**Decision.** Agents are added in a fixed order, all through ACP behind the same host: Claude Code (M1), Codex (M3); pi and other model APIs after the MVP (R2). Claude runs on the operator's own subscription for the operator's own work only, guarded at start-up against every credential source that would outrank it and checked by a self-test; an API key is a configuration-only fallback. Repository files that could configure a session (hooks, settings, MCP servers) are kept out of it. Grindstone never offers Claude login to anyone else. A capability's agent is configuration: switching provider changes no code.

**Why.** The operator's primary tool first; the second agent proves the abstraction and gives independent reviewers a different model family. **Rejected:** building on one vendor's SDK directly (locks out others); several agents at once (multiplies early integration risk).

#### ADR-19 — A scripted agent proves mechanisms in CI

**Decision.** The agent host carries a scripted ACP agent preset that replays fixture scripts of tool calls and reports. Exit criteria about mechanisms run in CI against it; criteria about real agents are recorded live runs kept with their logs.

**Why.** Deterministic, cheap tests of durability, reporting, cooperation and change handling without model variance. **Rejected:** live models in CI (cost, flakiness); mocking the host (misses the real protocol path).

#### ADR-20 — Every task tree has a budget

**Status.** Superseded by ADR-37.

**Decision.** Each run has its own limits. Each tree — a command, template run or top-level task with everything it delegates — has a tree budget set at its root, with one counter per unit (tasks, turns, wall time, tokens and spend where reported), never converted between units. Consults draw a capped allowance from their caller; delegated children run on their capability's own limits and are charged to the tree budget. Depth is at most two below the root and live children are capped. Any overflow returns a structured tool error and raises a `budget_overflow` decision. Costs roll up the tree and are shown per command, factory, capability and need.

**Why.** Cooperation without bounds is the main cost risk of multi-agent work. **Rejected:** global rate limits only (no per-tree control); unlimited delegation with monitoring (finds problems after spending); a fixed fraction of the parent's budget for children (delegated work is often larger than its parent, and subscription and API runs report different units).

## Factories and cooperation

#### ADR-21 — Factories are the unit of extension

**Decision.** A factory is a package with a manifest of seven parts — item kinds, task templates, capabilities, check methods, subjects and workspace providers, delivery adapters, interface shapes — registering names only in its namespace, importing only the kernel SDK. Projects enable factories by version. Factories are data first; code only for adapters and check methods. Every factory passes the conformance kit. The MVP ships SDLC and the `notes` fixture in the main repository; separately installable packages arrive in R1.

**Why.** Registries, entry points, templates and versioned contracts are the right extension seams; a factory groups them for one domain so a domain arrives or leaves as one unit. **Rejected:** a marketplace and run-time plug-in loading (trust and versioning problems before there is demand); factories extending kernel verbs (ends domain neutrality).

#### ADR-22 — Templates are bounded graphs of six step types

**Decision.** Factory workflows are templates of `task`, `fan_out`, `check`, `change`, `decide` and `deliver` steps with conditional edges; loops require `max_rounds`, and exhausting them raises a decision. Templates are exposed as commands and run as DBOS workflows; bindings resolve to pinned revisions at step start.

**Why.** Enough structure for every planned domain without becoming a programming language; reproducible from records. **Rejected:** arbitrary Python workflows per factory (unreviewable, hard to resume); BPMN or a general workflow language (too large).

#### ADR-23 — Capabilities define specialists as data; skills load on demand

**Decision.** A capability is a versioned, hashed file declaring id, prompt, agent, skills library, toolbox, workspace mode, permissions, produced kinds, offers, what it may prove, minimum tier and default budget. Skills are Markdown instruction packs with optional tools, loaded at start or mid-session through `load_skill`, only from the capability's library. Projects may override a bounded set of fields. Capabilities and skills are never proposable by agents.

**Why.** Specialists as reviewable data let the kernel match work, enforce make/prove and grant access without code; skills put know-how where agents can use it only when needed. **Rejected:** code-defined agents (harder to review and version); one general agent with every tool (no least privilege, no independent proof); long prompts carrying all know-how (unversioned, always paid for).

#### ADR-24 — Cooperation through three verbs and deterministic matching

**Decision.** Agents cooperate only by `load_skill` (switch mode), `ask` (consult a specialist read-only, cached, or ask the operator) and `delegate` (a child task with its own checks and budget). Requests name needs; the kernel matches capabilities by a fixed sequence of filters; ambiguity or absence becomes an escalation whose answer pins the project's choice.

**Why.** Specialists mid-task and across factories, without agent-to-agent chat, untracked state or unpredictable routing. **Rejected:** free agent-to-agent messaging (unauditable, unbounded cost); model-based routing (non-deterministic, untestable); switch mode only (no independent expertise).

#### ADR-25 — Factories integrate through interface items

**Decision.** `core.interface` items name a boundary, its shape, contract, provider, consumers and checks. Factories reference each other only through interface items and `core.*` kinds; change propagates by the normal impact walk and regression sweep.

**Why.** Interface control documents are how engineering disciplines cooperate without coupling; Grindstone gets it from items, ChangeSets and checks with no new machinery. **Rejected:** shared cross-factory kinds (coupling); event subscriptions between factories (ordering and tracking problems).

#### ADR-26 — Delivery is a kernel port with factory adapters

**Status.** Amended by ADR-45 (the port's operations).

**Decision.** The kernel owns the delivery port (`prepare`, `deliver`, `observe`), its `delivery` decision and its idempotency ledger; factories ship adapters. Only verified subjects can be delivered; agents never hold delivery credentials.

**Why.** Every domain ships somewhere different; the rules for shipping safely are the same. **Rejected:** delivery as factory code calling remotes from a template step (bypasses idempotency and decisions).

#### ADR-27 — The SDLC factory owns git workspaces, copy-back and GitHub delivery

**Status.** Amended by ADR-40 (delivery modes).

**Decision.** Bare mirrors, worktrees, branches, copy-back path tiers, the CI-suite check method and the GitHub pull-request adapter are SDLC factory code behind kernel ports. The control plane commits with hooks disabled from private clones and is the only place that pushes, using a GitHub App installation token. Each delivery posts one verification status that the repository ruleset requires for merge. The workspace provider returns, with the subject, the extra checks its path policy requires and a permission request for each protected path, so path rules stay in the factory while the kernel enforces them. The kernel knows `git_commit` only as a subject kind.

**Why.** Keeps the kernel free of git policy while giving code the strongest copy-back safety: agent work reaches the repository only as a commit the control plane made and the check station proved. **Rejected:** git handling in the kernel (every factory would inherit software assumptions); agents pushing directly (credentials in agent reach); a personal access token (broader than one installation).

## People, autonomy, memory and scope

#### ADR-28 — Every question to a person is one typed decision

**Decision.** Approvals, agent questions, permission requests, manual checks, deliveries, suggestions, escalations and scope questions are all one decision record, shown identically in the UI, REST, VS Code and the operator plugin. Kinds are registry entries with an eligibility class, an answer schema and a recommendation source (fixed default, asking agent, or advisor). Flags set by the kernel mark what needs a person at every level. An answer is refused if the decision was superseded or its context changed; a decision superseded three times becomes an escalation. Related decisions are batched; a decision blocks only its scope; only permission requests expire, to deny. Waiting workflows park on typed continuations.

**Why.** One queue the operator can trust and one place to automate. **Rejected:** ad-hoc prompts per feature (untraceable, unautomatable); timeouts that approve (silent authority).

#### ADR-29 — An advisor recommends; change classes have computed floors

**Decision.** For approvals and questions that need judgment, an advisor capability — on the most capable configured model and never the author of the work — gives at least a minimal and a right option, plus a staged path when they differ. Each option carries its change class (local, design adjustment, design change, architectural), its impact and a short evidence-based assessment. It recommends the option that leaves the product and codebase in the best lasting state within the approved scope, even at substantial effort; effort decides only between equivalent outcomes. Grindstone computes a class floor from what an option changes and how far it reaches; the advisor cannot go below it. Scope expansion is flagged; architectural changes are always decided by a person.

**Why.** Encodes the project's engineering-judgment rule and keeps classification honest. **Rejected:** advice on every decision (cost); trusting a model's own classification (it under-classes).

#### ADR-30 — Autonomy is decided by fixed rules, with a tripwire

**Decision.** Each decision kind belongs to an eligibility class (`never`, `l2`, `l3`); factories cannot place a kernel kind lower. A project starts at L1 under an instance ceiling; the operator raises the level; the tripwire or the operator lowers it. L0 answers nothing; L1 pre-selects and batches; L2 lets policy answer unflagged `l2` decisions whose recommendation matches a written rule; L3 (R2) adds `l3` kinds such as delivery. Every policy answer records the rule it matched and can be reverted. The tripwire — a reverted policy answer, two failed deliveries in a row, a high-severity security finding, a budget overflow or a principle-flagged decision — drops the project to L1. Pause stops dispatch and policy answers.

**Why.** Delegation the operator can predict and audit. **Rejected:** confidence- or agreement-based eligibility (unpredictable, gameable).

#### ADR-31 — Project memory is principles and learnings; search only suggests

**Decision.** Memory is two kernel kinds: principles, which people own, and learnings, which agents propose and a fixed rule or a person accepts; a learning that mentions a principle always goes to a person, and a nightly audit flags learnings that contradict principles. Both reach context packs by a fixed retrieval rule. Search is full-text in Postgres over items, findings, learnings and report summaries — never source code; vector search follows in R2. Search results, similarity and unlinked mentions are suggestions only.

**Why.** Durable, reviewable memory without a separate store or opaque agent memory. **Rejected:** agent-managed free-form memory (unreviewable); code indexing (agents search the repository themselves); a hosted embedding API (another credential and egress).

#### ADR-32 — The outer loop maps external signals by fixed code

**Decision.** A scheduled poll reads pull-request review comments, failing checks on the default branch and labelled issues, and maps each by fixed code, with no agent reading signal text first: a review comment becomes an `untrusted` finding; a failing check a test-failure finding linked to its criteria; a labelled issue an `untrusted` proposal to start `/discover`. Other systems post to an authenticated intake endpoint. Everything derived from a signal stays `untrusted` and needs a person.

**Why.** External text is the main prompt-injection path; fixed mapping keeps it inert until a person looks. **Rejected:** a triage agent (an injection surface that adds no safety, since a person approves anyway).

#### ADR-33 — Discovery comes before planning; small changes take a fast path

**Decision.** A project starts with `/init`, a feature with `/discover`: bounded rounds of questions as decision batches, then a product definition and features a person approves, sends back or drops. `/plan` works only within approved scope and raises open questions as one batch before approval. `/patch` turns a short request into one ChangeSet against an approved specification — adjusted requirements plus one ticket — shown with its full impact on one approval card, then implemented like any other. Plain pull requests that touch no published file remain possible; the governed share of merges is a success measure.

**Why.** A specification is only as good as the agreement it rests on; and if the only governed path is the long one, small fixes go around Grindstone and intent rots. **Rejected:** unbounded clarification (never converges); exempting small changes from ChangeSets (breaks traceability); blocking plain pull requests (removes the operator's escape hatch).

#### ADR-34 — Walking skeleton first; Grindstone builds itself

**Decision.** M1 is the thinnest end-to-end path through every container and through the SDLC factory: a hand-written ticket executed by Claude Code in its own worktree, copied back, proven on the check station, delivered as a pull request gated by a verification status, with one decision card in the UI. Every later milestone is a vertical slice that improves the tool already in use. From the end of M1, Grindstone's own tickets run through Grindstone, orchestrated by a stable instance on the last closed milestone's release, never by the instance under development.

**Why.** The largest risks are in integration — the agent-host ecosystem, credentials, durability across real side effects — and a skeleton finds them in weeks; real use then shapes the detailed designs. **Consequences.** M1 implements each invariant as far as its scope reaches; later specifications extend modules without breaking earlier criteria. **Rejected:** building the full item model before any agent runs (integration risk found last).

#### ADR-35 — The foundation holds commitments; specifications hold designs

**Decision.** This set records product scope, architecture, concepts, component boundaries, invariants, decisions and the roadmap. Detailed designs — full models, tables, endpoints, state tables, configuration keys, thresholds — are written in specifications just in time, at the start of their milestone, against code that exists.

**Why.** Detail written long before its code goes stale, and keeping it consistent becomes the dominant cost. **Rejected:** a full-detail design document maintained ahead of the code.

#### ADR-36 — The MVP is SDLC on the kernel, with cooperation

**Decision.** The MVP delivers the kernel, the full SDLC factory, cooperation (`load_skill`, `ask`, `delegate`) used by SDLC reviewers, autonomy up to L2, and the `notes` fixture proving neutrality. Deferred: repository snapshot and restore, vector search, autonomy L3 and auto-merge, the pi agent, baseline generation from an existing codebase (R2); separately installable factories and the RE factory (R1); T2 stations (R3); T3 stations (R4).

**Why.** Makes the kernel general while keeping the MVP to one domain, built and used every day; nothing deferred requires a kernel change. **Rejected:** shipping RE in the MVP (doubles the surface before the kernel is proven); an SDLC-shaped core now with generalisation later (rework of every module). Q-11 confirmed this scope at the M0 kickoff.

## Kickoff amendments

#### ADR-37 — Limits bound runaway work; cost is recorded, never gating

**Decision.** Supersedes ADR-20. No task, run or tree has a numeric budget of turns, wall time, tokens or spend. Runaway work is bounded by shape: delegation depth at most two below the root and a live-children cap per task (I-17); a liveness timeout that fails a run `stalled` after a period with no agent activity, paused while a kernel tool call is open; the consult ceiling (ADR-38); storage limits; and provider quota and rate-limit signals, which park the run. One optional project cap — spend where the provider reports it, otherwise turns, per calendar month — is off by default; when enabled and reached, no new run starts in the project, running turns finish, and an escalation flagged `cap_reached` is raised, which also trips the autonomy tripwire. Cost is recorded on every run, rolls up the delegation tree and is shown per command, factory, capability and need. This amends the budget clauses of ADR-14, ADR-23, ADR-24 and ADR-30: where they say budget, read limits.

**Why.** Task size and scope vary too much for any per-task allowance to be right: a fixed ceiling either stops good work midway or is set so high it bounds nothing. The real cost risks of multi-agent work are runaway shapes — loops, stalls and unbounded fan-out — and those are size-independent. Subscription providers report quota exhaustion themselves; pay-per-token providers are covered by the optional project cap. **Consequences.** The budget-tree machinery, the consult allowance and the `budget_exhausted` cause and `budget_overflow` flag are removed; QG-5, QS-10, I-17, M3-05 and SPEC-17 are restated in terms of limits; a stuck session is caught by liveness instead of total wall time, so long productive runs are never cut short. **Rejected:** per-unit tree budgets set at the root (ADR-20; sizes vary too much, and every ceiling is a guess the operator must keep tuning); no guards at all (a delegation loop or a stuck session would run until a quota ends it); a total wall-time limit per run (stops long, productive runs).

#### ADR-38 — A consult holds the call open until it answers, under a ceiling

**Decision.** `ask` to a specialist blocks in the open MCP call until the consult child reports, however long that takes, up to a consult ceiling (seed 2 h, owned by SPEC-17, overridable per capability within instance bounds). While the call is open the kernel sends MCP progress notifications as keepalives, each agent's client-side tool timeout is set above the ceiling by its capability's configuration, and the caller's liveness timer is paused. The consult child is a durable task; its answer is cached by `(capability hash, question hash, input hashes)`, and an identical ask joins a consult already in flight, so a session that drops mid-wait re-asks and receives the in-flight or cached answer with no second run. At the ceiling the call returns `consult_ceiling`, the caller's turn suspends with outcome waiting, the consult keeps running, and an escalation offers wait longer, retry or cancel; the answer resumes the caller in a new session. Park-and-resume otherwise remains only as fault recovery, and as the fallback for an agent whose client cannot hold a call open (SPK-5).

**Why.** Specialist work can legitimately take longer than five minutes, and an answer delivered in the same session keeps the caller's working context; durability comes from the cache and single-flight join, not from parking. **Consequences.** A caller in an open consult holds its own lane while it waits — with one writing lane by default, a long consult delays other writing work, which the operations view shows; consults themselves run on the read-only lane, so no deadlock arises. **Rejected:** a fixed five-minute wait, then park (Q-9 default; reloads context for long consults); always park and resume (every consult pays a new session); an async handle polled by the agent (relies on the model to keep polling and costs extra tool calls).

#### ADR-39 — Skills are materialized per session outside the workspace and returned inline

**Status.** Amended by ADR-43 (skill tools listed from session start).

**Decision.** At session start the agent host materializes the skills a capability loads at start, read-only, into that session's private configuration directory outside the workspace — in the location the agent discovers skills from natively — and records them in the context pack. `load_skill` for any other skill in the capability's library returns the skill's instructions inline as the tool result and adds its declared tools, which works with every agent whether or not it discovers skills natively, and is recorded on the run. Skills, settings and hooks shipped inside a repository or workspace are still never loaded (ADR-18), and nothing materialized is reachable from the workspace or the copy-back (I-14).

**Why.** Native discovery uses each agent's own skill mechanism for the skills it always needs; inline return keeps mid-session loading uniform and fully recorded across Claude Code, Codex and later agents. **Rejected:** skills only inline (loses native behaviour for start skills); materializing into the workspace (configuration next to agent-writable files and repository content, against I-14); materializing the whole library natively (agents could use skills the run never records).

#### ADR-40 — Delivery states whether the remote enforces the gate

**Decision.** Amends ADR-27 and I-08. A delivery target is in one of two modes, observed by the adapter and never assumed. **Enforced:** the target branch's rules require the verification status with its source restricted to the Grindstone App, so the remote itself refuses an unverified merge. **Unenforced:** the remote cannot or does not require it — for example, rulesets on a private repository on GitHub's free plans. The adapter observes the mode at project setup and before every delivery, from the API that lists the rules in force on the target branch, and records each observation with its time; the mode is an observed fact, never configuration, and it is shown on the project and on every delivery card. In both modes the adapter opens the pull request and posts the verification status. In unenforced mode Grindstone performs the merge itself after the `delivery` decision, re-checking freshness and passing the head SHA it verified, so a concurrent push fails the merge. `observe` reports any merge of a Grindstone pull request it did not perform, and any change to a published file on the default branch that did not arrive through a delivery, as a high-severity `untrusted` `delivery_bypass` finding, counted against evidence integrity. Plain pull requests that touch no published file stay allowed (ADR-33) and count only against the governed share. A change from enforced to unenforced raises an escalation before the next delivery.

**Why.** One operator on a free plan with private repositories is a core user, and Grindstone's own repository is one. Refusing to deliver there fails the product goal; silently promising a guarantee the remote does not give fails it worse. Grindstone-performed merges plus bypass detection keep evidence integrity measurable and every bypass visible. **Consequences.** In unenforced mode Grindstone detects bypass but cannot prevent it, and says so. The App needs no permission beyond contents write, already granted. SPK-4 settles how the mode is detected. **Rejected:** refusing unenforced targets (excludes the operator's own repository); treating every target as enforced (a false guarantee); requiring a paid plan (a cost the product should not impose on its first user).

#### ADR-41 — Claude Code is the only agent until the operator adds another

**Decision.** Amends ADR-18. Claude Code on the operator's subscription is the only real agent in the MVP. Codex moves from M3 to whenever the operator adds a second provider, joining pi and other model APIs (R2). The abstraction stays whole: every agent runs through ACP behind the same host, a capability's agent is configuration, and the scripted agent (ADR-19) is a second ACP implementation exercised on every commit, so no Claude-specific path may enter the host or the kernel. Reviewer independence in the SDLC factory becomes a different model from the author or implementer, in a fresh read-only session that shares none of their context; it returns to a different model family, by configuration only, once a second agent exists. Make and prove (I-15) is unchanged: provers are still different capabilities, and mechanical proof still runs on the check station.

**Why.** The operator has a Claude subscription and no other provider; paying for a second only to meet a default is cost without a user. Make and prove does not depend on model family; family diversity reduces correlated blind spots, which a different model and a fresh, context-free review partly recover. **Consequences.** SPK-3 is deferred, with Q-3 and Q-4; M0-03 no longer waits on it; M3-06 is restated; SPEC-18 drops its Codex variants. Author and reviewer errors are more likely to be correlated; the mechanical provers (CI suite, tests on the check station) and the test reviewer's criterion-by-criterion verdicts carry more of the weight, and the risk is revisited when a provider is added. All agent work now depends on one vendor's terms; switching to an API key stays configuration only (ADR-18). **Rejected:** keeping Codex at M3 (a cost the operator declined); building on the Claude Agent SDK directly instead of ACP (locks the host to one vendor, as ADR-15 and ADR-18 already rejected); dropping the reviewer-independence policy (loses the protection a different model and fresh context still give).


#### ADR-42 — The agent host uses its packages unmodified, behind a launcher and a backend wrapper

**Status.** Accepted on 17 October 2026, from SPK-1.

**Decision.** Amends ADR-15. The agent host uses `@ahpd/sdk`, `@ahpd/agent-acp` and each agent's ACP adapter unmodified. Grindstone adds two pieces of its own. **A backend wrapper** around the ACP backend creates each session's agent with that session's environment, Unix user and kernel MCP server — an HTTP server entry with the per-task bearer token in its headers — read from the control API's own session record, never from session configuration an AHP client can read. **A vendored launcher** in front of each agent's ACP adapter runs the credential self-test (ADR-18) and merges Grindstone's per-session agent options into every session it opens — for Claude Code, every settings source off — so no repository configuration reaches a session. The host is given a people directory, because the AHP SDK checks a client's grants only when it has one; a viewer is never granted the answer to a permission request.

**Why.** SPK-1 found no need for a patch: `@ahpd/agent-acp` passes a session's MCP servers, with headers, to ACP's session creation, and Claude's ACP adapter takes per-session options from the session's metadata. A patch is a fork to rebase on every release of a package that releases every few days; a wrapper and a launcher use only published interfaces. **Consequences.** Q-1 is resolved without a patch. An upgrade of these packages is a deliberate commit that re-runs the host's protocol smoke test (the risk table's mitigation is unchanged). **Rejected:** patching the vendored ACP plugin, the default this record replaces (a fork to maintain against a fast-moving upstream); host-wide MCP servers with one shared token (breaks per-task authority, ADR-16).

#### ADR-43 — A skill's tools are listed from session start and refused until the skill is loaded

**Status.** Accepted on 17 October 2026, from SPK-5.

**Decision.** Amends ADR-39. `load_skill` still returns the skill's instructions inline and is recorded on the run. The tools that the skills in a capability's library declare are listed on the kernel MCP surface from session start, and the kernel refuses a call to a skill's tool until that skill is loaded in the run, with the structured error `skill_not_loaded` naming the skill to load. The tool list a session sees never changes after it starts.

**Why.** SPK-5 found that Claude Code (2.1.300) never re-lists a server's tools after a tool-list change in a non-interactive session over HTTP: it holds no stream a notification could arrive on, so a tool added mid-session never reaches the agent, in that turn or the next. A fixed list with refusal works with every agent whether or not it handles list changes, and every use is still recorded, which is what ADR-39 rejected native whole-library loading for. **Consequences.** The kernel MCP surface carries every library tool of the capability from the start; a capability with a large library pays in listed tools, which agents with deferred tool search absorb. **Rejected:** adding the skill's tools by a tool-list change (does not reach Claude Code); one generic dispatcher tool for every skill tool (hides each tool's schema from the agent; kept as the fallback if a capability's library grows too large to list).

#### ADR-44 — Semantic hashes omit fields at their default

**Status.** Accepted on 17 October 2026, from SPEC-01 (section 6).

**Decision.** Amends ADR-08 and the hashing contract. A semantic field whose value equals its declared default is omitted from the canonical form before hashing. Changing a semantic field's default is a breaking change under the schema compatibility check (FF-03), with a version bump and an upgrade note that says how stored hashes are treated. Semantic hashes are written with their algorithm, `sha256:<64 lowercase hex>`.

**Why.** Read literally, the hash covers every semantic field, so adding an optional, defaulted field to a kind — a compatible change by ADR-05's rule — would add it to every item's canonical form, change every hash, and make all evidence in every project stale on an ordinary upgrade. Omitting defaults keeps compatible changes compatible for hashes too. The prefix lets a later algorithm coexist without a format migration. **Consequences.** The serialized form of a record still carries every field; only the canonical form for hashing omits defaults. **Rejected:** hashing every field and re-hashing all stored items on each compatible change (a mass staleness event per upgrade); bare hex hashes (an algorithm change would need a migration everywhere).

#### ADR-45 — The delivery port reports the gate and completes deliveries through optional operations

**Status.** Accepted on 18 October 2026, from the first review of the M1 specifications (SPEC-03 architecture review, A2).

**Decision.** Amends ADR-26. The delivery port has six operations. `observe_mode` reports whether the remote enforces the gate (ADR-40). `prepare`, `deliver` and `observe` keep ADR-26's meaning. Two are optional, with no-op defaults, and an adapter declares which it supports: `publish_gate_state` shows the remote the delivery's current verification state, and `accept` completes the delivery on the remote and is called only in unenforced mode, after the kernel re-checks the gate, with the subject it verified. The contract uses these kernel-neutral names; each adapter documents what they mean for its remote (for GitHub, a commit status and a merge with the verified head SHA). The kernel calls the operations in order, re-checks the gate before `deliver` and before `accept`, and holds every idempotency key; adapters only perform.

**Why.** ADR-40 made the enforcement mode and outside merges kernel facts, and the gate re-check before a Grindstone-performed merge must be the same for every adapter. Folding status and merge into `deliver` would make every adapter re-implement the re-check and the ledger; naming them after a git host would put git words in a kernel port that a report export or a fabrication package never needs. **Consequences.** SDK 0.1.0 ships the six operations. An adapter whose remote has no gate reports no mode, and both optional operations are skipped. **Rejected:** three operations with status and merge inside `deliver` (duplicated safety code per adapter); `publish_status` and `merge` as kernel names (git-host vocabulary in the kernel, FF-12).

#### ADR-46 — Dependencies are the latest stable release compatible with the other pins

**Status.** Accepted on 18 October 2026, from the first review of the M1 specifications (summary, question 1).

**Decision.** Amends ADR-01 and the constraints table. Every dependency is the latest stable release that is compatible with the other pinned dependencies, pinned exactly. An exception, a dependency held below its latest release, names its constraint in `docs/m0/versions.md`: which dependency's declared range blocks the latest release, and what lifts it. Exceptions are re-checked at every upgrade and end as soon as the constraint lifts. Pinning, digests and deliberate upgrades are unchanged.

**Why.** The first case is TypeScript: 7.0.2 is the latest, but SvelteKit 3.1.0 and svelte-check 4.7.7 declare peer ranges that stop at TypeScript 6, so the web UI cannot use 7 yet. Read literally, ADR-01 would force an unsupported pair. **Rejected:** holding the whole repository at the newest version every package supports (gives up current releases everywhere for one package); ignoring declared peer ranges (unsupported combinations in CI and production).

# Roadmap

The order of work, what closes each milestone, and what is still unknown.

## Delivery strategy

Six milestones take Grindstone from an empty repository to the MVP; four releases after it add factories and station tiers. The order puts the riskiest integrations first, real use as early as possible, and proof of domain neutrality before the SDLC factory grows large (ADR-34, ADR-36).

*Diagram (not reproduced): roadmap — milestones M0 to M5, three gates (self-hosting at M1, kernel neutrality at M2, MVP at M5), and releases R1 to R4.*

- **Walking skeleton first, through a factory.** M1 runs one hand-written ticket through every container — agent station, kernel MCP, copy-back, check station, delivery adapter, one decision — in the thinnest form that keeps every invariant it touches, and does so through a skeleton SDLC factory so the kernel/factory seam exists from the first line of code.
- **Prove neutrality early.** M2 closes only when the code-free `notes` factory runs a task, a check, a ChangeSet and a decision end to end with no kernel change (M2-05). After that gate, a kernel specification that needs an SDLC name is a defect (FF-12).
- **Vertical slices after.** Each milestone adds one capability end to end — contracts, kernel module, factory data, interface, tests — and ends runnable. No milestone leaves a layer half-built.
- **Grindstone builds itself.** From M1 its own tickets run through it; from M2 its own specifications are SDLC items; from M4 its features start with `/discover`. A stable instance on the last closed milestone's release orchestrates the work; the instance under development runs only in CI and local tests. The stable instance is upgraded only at a milestone close, after its migrations pass.
- **Plan one milestone ahead.** Specifications for a milestone are written while the previous one closes, against code that exists (ADR-35). Later milestones stay at outcome level here and are re-planned at each review.
- **Milestone review.** At each close: exit criteria pass on the GitHub test repository, success measures are read, risks and open questions are revisited, fitness functions are reviewed, and any change to scope or order is recorded as a decision.
- **Releases are outcomes, not plans.** R1–R4 are listed so the kernel keeps room for them; each is planned with its own foundation addendum after the MVP review.

## Milestones and exit criteria

A milestone closes when every exit criterion passes on the GitHub test repository. Criteria about mechanisms run in CI against the scripted agent (ADR-19) and, for the kernel, against the `notes` fixture factory; criteria that name a real agent are recorded live runs kept with their logs. Criteria of earlier milestones must keep passing. Each specification maps the criteria it delivers to its own acceptance criteria.

### M0 — Foundations

Repository, CI and four empty services running; the unknowns that could change the design are settled.

- [ ] M0-01: `docker compose up` brings `grindstone`, `agent-host`, `runner` and `postgres` to healthy with the `blobs`, `repos`, `workspaces` and `runs` volumes mounted only where ADR-01 allows, every image pinned by digest.
- [ ] M0-02: CI runs lint, type checks, tests and the M0 fitness functions — import boundaries (FF-01), generated-contract drift (FF-02), pins (FF-04) and traceability over `docs/` including this foundation (FF-13); fixtures prove that a floating tag, a kernel-to-factory import and a dangling ID each fail the build.
- [ ] M0-03: SPK-1, SPK-2, SPK-4 and SPK-5 reports are filed (SPK-3 is deferred by ADR-41); Q-1 to Q-11 are resolved or their defaults confirmed; resolved dependency versions and the Claude credential-precedence list are recorded from primary sources.
- [ ] M0-04: The GitHub test repository with its ruleset and a GitHub App installation, the runner toolchain image, a fixture project with tagged tests and the benchmark project exist and are wired into CI.

### M1 — Walking skeleton

A hand-written ticket becomes a verified pull request through every container and the skeleton SDLC factory, and Grindstone starts building itself.

- [ ] M1-01: Live run: a ticket with acceptance criteria, imported from a file as a ChangeSet approved on a decision card, is matched by need to `sdlc.implementer` and executed by Claude Code on the operator's subscription in its own worktree; the SDLC workspace provider copies the work back into the mirror and commits with hooks disabled; after a `delivery` decision the `sdlc.github_pr` adapter pushes and opens the pull request.
- [ ] M1-02: The pull request's verification status succeeds only when every criterion's tagged test passes on the check station at the subject commit against the ticket's current item hashes; a new head commit or a changed criterion sets it back to pending; on the test repository, whose ruleset is enforced, the ruleset blocks merge until it succeeds; on a repository whose ruleset is not enforced, the adapter detects the unenforced mode, merges only itself with the verified head SHA, and reports a merge made outside it as a `delivery_bypass` finding (ADR-40).
- [ ] M1-03: With the scripted agent: an invalid report is refused with structured errors and fixed in the same turn; a turn without a report gets one corrective prompt and then fails `missing_report`; an `ask` to the operator parks the task, and its answer resumes it in a new session on the same workspace.
- [ ] M1-04: Killing `grindstone` between each external action and its record — session, prompt, copy-out, push, pull request, status — and replaying duplicate host events resumes with no duplicate session, turn, blob, push, pull request or status.
- [ ] M1-05: From `agent-host` and `runner` no GitHub, database or MCP signing credential is readable and a push to GitHub fails; nothing mounts the Docker socket; repository settings never reach a session; a hook written in a workspace never runs in `grindstone`; copy-back refuses protected paths and holds reviewed-tier paths for their reviewer; deployment and workspace mount lints (FF-05, FF-06) pass.
- [ ] M1-06: The run records the item revisions, capability hash, factory version, provider, model, subject version, context pack hash and prompts it was given.
- [ ] M1-07: Make and prove: a check plan whose prover resolves to the maker's capability is refused at load; the implementer's own test runs are stored as working notes and never satisfy a required check; the test reviewer must pass before the status can succeed.
- [ ] M1-08: A Grindstone ticket for M2 is executed, verified and merged through Grindstone.

### M2 — Traceable intent

The full item model and relation graph; evidence goes stale exactly when what it was proven against changes; the kernel is proven domain-neutral.

- [ ] M2-01: Every SDLC kind and the five `core.*` kinds with artifacts, header items, typed references, mentions and embeds; a revision with an unresolved reference is refused; edges are derived from content; an unlinked item ID becomes a link suggestion.
- [ ] M2-02: Freshness property tests for every subject kind: evidence, consult answers and context packs go stale exactly when an input hash, the subject version or a relevant environment field changes, naming the mismatch; Python and TypeScript hash implementations agree on the golden vectors, one after a Markdown round trip.
- [ ] M2-03: An operator's change to a requirement shows every affected item for a verdict before it applies, then re-runs exactly the dependent checks; the scheduled regression sweep re-checks proven criteria on the default branch, and only a failing re-check reopens the task; impact walk and freshness meet the capacity envelope (FF-14).
- [ ] M2-04: Manifest rules gate approvals — an uncovered requirement blocks a breakdown approval, an interface without provider or consumer blocks its approval — and all rules run nightly.
- [ ] M2-05: The code-free `notes` factory installs, is enabled on a project and runs K1 and K4 end to end with no change to `grindstone`; a factory that redefines a `core.*` name or registers outside its namespace is refused; the conformance kit (FF-11) and kernel neutrality check (FF-12) pass for `sdlc` and `notes`.
- [ ] M2-06: Item pages, rendered generically from kind schemas, show every relation in both directions, unlinked mentions, a local graph and revision diffs; `/plan` drafts a specification through the spec author and auditor with bounded rounds (S2); Grindstone's own M3 specifications are held as SDLC items.

### M3 — Safe change and cooperation

Discoveries and decisions flow back into intent through reviewed ChangeSets, and agents call specialists; the core loop is closed.

- [ ] M3-01: An implementer's finding becomes one ChangeSet across a specification and a ticket (S3); impact rounds reach a fixed point with a recorded verdict from the impact reviewer for every marked item; it applies once, atomically, and exactly the dependent checks re-run.
- [ ] M3-02: A decision answered mid-run produces one ChangeSet; a running task pinned to a touched item receives it at its next turn, or is cancelled if a pinned item was removed; a pending decision whose context changed is superseded and raised again.
- [ ] M3-03: Two ChangeSets on the same item apply one after the other with nothing lost; a re-walk whose review set differs from the approved one asks again; a revert applies the inverse, and a revert over a later change raises a `revert_conflict` decision (S4).
- [ ] M3-04: Batched decisions show on one card; an answer to a superseded decision is refused; only permission requests expire, and they deny; a `scope_expansion` or `untrusted` ChangeSet waits for a person at every level.
- [ ] M3-05: `ask` returns a structured consult answer, and an identical ask hits the cache until an input changes; `delegate` creates a child with its own checks whose approved, pinned output resumes the parent; `load_skill` is recorded on the run; depth and live-children overflow return structured errors (property tests on delegation trees). A delegating parent frees its writing lane while its child runs on it. A consult longer than the agent's default tool timeout answers in the open call; a session dropped mid-consult re-asks and receives the same answer with no second run; a consult past its ceiling suspends the caller and raises an escalation. A run with no activity for the liveness timeout fails `stalled`, while a run waiting in an open `ask` does not. With the project cap enabled, reaching it stops new runs and raises an escalation flagged `cap_reached`. Live run: S5.
- [ ] M3-06: Live run: the auditor and code reviewer run on a different Claude model from the author and implementer, chosen by configuration only (ADR-41); the security reviewer is added as a required check at collect time when the path policy matches the changed files, and a protected path raises a permission decision before verifying; a failed run raises an escalation, and the retry starts from the current base with the previous run's diff.
- [ ] M3-07: A fresh install from `compose.yaml` and the documented secrets runs M1-01 and M3-01 within the install target (QS-12); the success measures have a recorded baseline (Q-8).

### M4 — Discovery and planning

From an idea to approved tickets through agents, with the operator deciding in the browser.

- [ ] M4-01: With scripted agents, `/init` on an empty repository drafts principles, the conventions skill and project configuration, and `/discover` asks product questions in batches through `ask(operator)`; principles, product and features apply only after a person approves; policy answers none of these at any level.
- [ ] M4-02: `/plan` on an approved milestone produces an audited specification and then tickets with a dependency graph; coverage rules gate the breakdown approval; a requirement outside scope is flagged `scope_expansion`. Live run: Claude Code completes `/discover` and `/plan`.
- [ ] M4-03: With fixture advice, the advisor gives a decision a minimal, a right and a staged option with change class, impact and assessment; a class below the computed floor is raised to it; the accepted recommendation is recorded with its rationale and rejected options.
- [ ] M4-04: A new capability, skill and template step added as files run with no code change; `grindstone check` refuses an invalid manifest, an unbounded loop and a step naming an unknown need; ambiguous matching raises an escalation whose answer pins the project's choice.
- [ ] M4-05: Behind operator login the browser shows decision cards, ChangeSet diffs, findings, template runs, delegation trees with their costs and live sessions; the operator steers a session, and steering is recorded but cannot end it; VS Code attaches to the same session; a permission request is answered on its card and refused through AHP.
- [ ] M4-06: `/patch` turns a short request into one ChangeSet that adjusts requirements and adds one ticket with criteria, shown with its full impact on one approval card; once approved the ticket executes and merges like any other.
- [ ] M4-07: A Grindstone feature for M5 goes from `/discover` to merged pull requests through Grindstone.

### M5 — MVP

Projects learn, the outer loop runs, policy answers routine decisions, and Grindstone is operable day to day.

- [ ] M5-01: At L1 a learning that meets the tag rule is accepted by policy, one that mentions a principle is asked of a person, an accepted learning appears in the next context pack its retrieval rule selects, and the nightly audit reports a learning that contradicts a principle.
- [ ] M5-02: Full-text search returns each fixture query's expected item in its top three; a missing link found by search is raised as a link suggestion, and nothing changes until a person accepts it.
- [ ] M5-03: A pull-request review comment becomes an `untrusted` finding with no agent reading it first, then a ChangeSet a person approved; a failing default-branch check becomes a finding linked to its criteria and `/repair` fixes it; a labelled issue becomes a proposal whose acceptance starts `/discover`.
- [ ] M5-04: At L2 policy answers exactly the eligible decisions and records the rule it matched; flagged and `never`-class decisions go to a person; reverting a policy answer applies its inverse and drops the level to L1 with an escalation; pause stops dispatch and policy answers.
- [ ] M5-05: The operator plugin lists and answers decisions and starts commands from Claude Code through the same API as the UI.
- [ ] M5-06: Operations: backup and restore of Postgres and the blob store onto a fresh host, followed by a regression sweep; upgrade across a migration with parked workflows resuming once; blob garbage collection never removes a rooted blob, including one written by a run whose ChangeSet is still awaiting approval; the operations view shows lanes, queues, spend per factory and capability, stale evidence, waiting decisions and the capacity envelope.
- [ ] M5-07: One full Grindstone milestone runs through Grindstone at L2, with the success measures read at its close.

## Spikes and open questions

Spikes are time-boxed experiments in M0 that settle facts the design depends on. Each files a short report in `docs/spikes/` with what was tried, what worked, and the exact versions and steps. A spike result that contradicts a decision record is answered by a superseding record before the M1 specifications are written; the default is the recorded fallback, not a redesign.

| Spike | Box | Settles |
| --- | --- | --- |
| SPK-1 Host, Claude and VS Code | 2 days | A host on `@ahpd/sdk` with the vendored ACP plugin runs a Claude Code session in a given workspace, as a different user from the host, on the subscription token; the session calls a stub kernel MCP server (FastMCP in FastAPI) with its own per-task token; a permission request is answered through the control API and refused from a browser client; VS Code attaches; the credential self-test, disabling repository settings, and behaviour on a host restart mid-turn are recorded (Q-1, Q-2, Q-6). Fallback: M1 drives the Claude ACP adapter through a minimal host behind the same control API and events; live sessions in the browser move to M4 |
| SPK-2 DBOS in FastAPI | 2 days | DBOS in the FastAPI lifespan survives a kill during a step, a message wait, a child workflow and a scheduled run with no duplicate effects; idempotent messages; a concurrency-1 queue serializes work across projects; a parked workflow resumes exactly once after an application-version bump; a parent on the writing lane waiting on a child on the read-only lane does not deadlock |
| SPK-3 Codex and pi | 1 day | **Deferred until a second provider is added (ADR-41).** Codex through its ACP adapter with an API key reaches an HTTP MCP server and runs read-only and workspace-write sandboxes; pi through its ACP adapter reaches the kernel MCP with a per-task token and reports on every turn; whether Codex's subscription login works headless in a container; how each discovers skills natively from a session configuration directory (Q-3, Q-4, Q-5) |
| SPK-4 GitHub mechanics | 1 day | On the test repository with a GitHub App installation and a ruleset: a status set by the App satisfies the required check; a status at an old head stops counting after the branch updates; auto-merge on a behind pull request waits for the update and the status, and disarming works; pull-request lookup by branch finds closed ones (Q-7); the delivery mode is detectable through the API on the public testbed (enforced) and on a private repository (unenforced); a merge with an expected head SHA fails after a concurrent push |
| SPK-5 Cooperation mechanics | 2 days | With Claude Code (and each further agent when added): an MCP tool call held open with progress keepalives while a child task runs for 2, 10, 30 and 120 minutes — the client, server and model timeouts and how each is raised by configuration (Q-9); a session dropped mid-wait re-asking and joining the in-flight consult; the ceiling suspend; `load_skill` returning instructions inline and adding tools mid-session; cost and latency of a cached and an uncached consult on the fixture project. Fallback: for an agent whose call cannot be held open, consults park and resume |

**Open questions.** The operator answered every open question at the M0 kickoff (17 October 2026). Answers marked *confirm* stand unless the named spike contradicts them; a contradiction is answered by a superseding record, defaulting to the recorded fallback.

| ID | Question | Answer | Status |
| --- | --- | --- | --- |
| Q-1 | Can the stock ACP agent plugin, or a community fork, pass a per-session MCP server with its own token? | Yes, unmodified: a backend wrapper adds the session's server and token, and a vendored launcher sets the agent's options (ADR-42) | Resolved by SPK-1 |
| Q-2 | Which AHP protocol line does `@ahpd/sdk` implement, and how does current VS Code attach to it? | AHP 1.0, accepting 0.9 clients; VS Code attaches as a remote agent host with the token | Decided; SPK-1 confirms |
| Q-3 | Does Codex's subscription login work headless in a container? | Use subscription login if SPK-3 shows it works headless; an API key is the configuration-only fallback, as for Claude | Deferred with SPK-3 (ADR-41) |
| Q-4 | How does the Codex ACP adapter receive Codex's sandbox mode? | Codex's own configuration file, supplied by the capability | Deferred with SPK-3 (ADR-41) |
| Q-5 | Does pi's ACP adapter pass per-session environment, and how do agents load skills? | Start skills materialized per session outside the workspace; `load_skill` returns bodies inline (ADR-39); skill tools are listed from start and refused until loaded (ADR-43). pi's environment handling waits for R2 | Decided (ADR-39); SPK-1 and SPK-3 confirm native discovery |
| Q-6 | Does FastMCP run on the current official MCP SDK, mount in FastAPI and verify a bearer token per request? | FastMCP mounted in FastAPI; otherwise the official SDK's server directly | Decided; SPK-1 confirms |
| Q-7 | How do auto-merge, a strict required status and branch updates interact for an App-set status? | Auto-merge waits for the update and a fresh status at the new head | Decided; SPK-4 confirms |
| Q-8 | Are the success-measure targets right? | The initial targets stand | Confirmed; reset at the M3 review from measured baselines |
| Q-9 | How long can an agent's MCP tool call stay open? | Redesigned: the call stays open until the consult answers, under a ceiling (ADR-38) | Decided (ADR-38); SPK-5 measures the timeouts to configure |
| Q-10 | What is the budget unit when providers do not report usage? | Redesigned: no budgets; limits bound runaway work and cost is recorded (ADR-37) | Decided (ADR-37) |
| Q-11 | Is the MVP scope in ADR-36 right? | Yes, as recorded | Confirmed by the operator |

## Spec map

Twenty-seven specifications deliver the MVP. Each is either a **kernel** specification (a module in `grindstone`; may not name a factory kind) or a **factory** specification (a package under `factories/`; may use only the kernel SDK). Every exit criterion of M1–M5 is delivered by at least one specification; M0's criteria are milestone work with no specification.

| Spec | Title | Kind | Owns | Delivers | Cites |
| --- | --- | --- | --- | --- | --- |
| **M1** |  |  |  |  |  |
| SPEC-01 | Contracts, IDs, hashing and code generation | Kernel | `contracts` | M1-06 | ADR-05, ADR-08; I-02 |
| SPEC-02 | Store, runtime, lanes and blob store | Kernel | `store` | M1-04 | ADR-02, ADR-03, ADR-04; I-06 |
| SPEC-03 | Platform: registries, loader and configuration | Kernel | `platform` | M1-07 | ADR-21, ADR-23; I-14, I-15, I-18 |
| SPEC-04 | Items, thin ChangeSet apply and decision records | Kernel | `intent`, `change`, `decisions` | M1-01 | ADR-08, ADR-10, ADR-28; I-03, I-11, I-13 |
| SPEC-05 | Deployment, users and secrets | Kernel | Compose deployment | M1-05 | ADR-01, ADR-17; I-09 |
| SPEC-06 | Agent station and task runs | Kernel | `work`, `stations` | M1-01, M1-03, M1-06 | ADR-14, ADR-15, ADR-17, ADR-37 (liveness); I-03, I-06 |
| SPEC-07 | Kernel MCP surface, first cut | Kernel | `surface` (MCP) | M1-03 | ADR-16; I-03, I-10 |
| SPEC-08 | Check station, evidence and the delivery port | Kernel | `evidence`, `delivery` | M1-02, M1-07 | ADR-12, ADR-26; I-04, I-05, I-08, I-15 |
| SPEC-09 | SDLC skeleton factory | Factory | `factories/sdlc`: implementer, test reviewer, workspace provider, CI suite, `sdlc.github_pr` | M1-01, M1-02, M1-05, M1-07, M1-08 | ADR-27; I-08, I-15 |
| SPEC-10 | Operator surface, first cut | Kernel | `surface` (REST, events), web shell | M1-01, M1-08 | ADR-06, ADR-28; I-11 |
| **M2** |  |  |  |  |  |
| SPEC-11 | Item model, relation graph and item pages | Kernel | `intent` | M2-01, M2-06 | ADR-08, ADR-09; I-01, I-02 |
| SPEC-12 | Freshness, impact walk and regression sweep | Kernel | `evidence`, `change` | M2-02, M2-03 | ADR-10, ADR-11, ADR-12; I-05, I-13 |
| SPEC-13 | Manifests, rules and the conformance kit | Kernel | `platform` | M2-04, M2-05 | ADR-13, ADR-21; I-18 |
| SPEC-14 | SDLC specification authoring | Factory | `factories/sdlc`: specification kinds, spec author, auditor, `/plan` specify step | M2-06 | ADR-22, ADR-33; I-15 |
| **M3** |  |  |  |  |  |
| SPEC-15 | Decision service | Kernel | `decisions` | M3-02, M3-04 | ADR-28, ADR-30; I-07, I-11 |
| SPEC-16 | Change pipeline | Kernel | `change` | M3-01, M3-02, M3-03 | ADR-10; I-13 |
| SPEC-17 | Cooperation, matching and limits | Kernel | `work` | M3-05 | ADR-24, ADR-37, ADR-38, ADR-39; I-10, I-16, I-17, I-19 |
| SPEC-18 | SDLC reviewers | Factory | `factories/sdlc`: impact, code and security reviewers, path policy, reviewer model configuration | M3-01, M3-06, M3-07 | ADR-12, ADR-18, ADR-23, ADR-41; I-15 |
| **M4** |  |  |  |  |  |
| SPEC-19 | Template and capability engine | Kernel | `work` | M4-04 | ADR-22, ADR-23, ADR-24; I-14 |
| SPEC-20 | SDLC discovery, planning and patch | Factory | `factories/sdlc`: `/init`, `/discover`, `/plan` break-down, `/patch` | M4-01, M4-02, M4-06, M4-07 | ADR-33; I-07 |
| SPEC-21 | Advisor | Factory | `factories/sdlc`: advisor capability, change classes | M4-03 | ADR-29; I-10 |
| SPEC-22 | Planning UI and VS Code | Kernel | web UI, VS Code extension | M4-05 | ADR-06, ADR-15 |
| **M5** |  |  |  |  |  |
| SPEC-23 | Memory and full-text search | Kernel | `memory` | M5-01, M5-02 | ADR-31; I-10 |
| SPEC-24 | Outer loop and `/repair` | Factory | `factories/sdlc`: signal mapping, `/repair`, repairer | M5-03 | ADR-32; I-07 |
| SPEC-25 | Autonomy L2 and policy | Kernel | `decisions` | M5-04 | ADR-30; I-12 |
| SPEC-26 | Operator plugin | Kernel | Claude Code operator plugin | M5-05 | ADR-06, ADR-23 |
| SPEC-27 | Operations | Kernel | Backup, upgrade, GC, operations view | M5-06, M5-07 | ADR-01, ADR-03, ADR-04 |

**Kernel or factory.** M5-03's signal mapping is software-specific, so its specification is a factory specification; the kernel parts it relies on — `untrusted` findings and the regression sweep — already exist from SPEC-12 and SPEC-16. The advisor is a factory capability serving the kernel need `core.advise`; another factory can offer its own advisor for the same need.

## Ownership as the system grows

Vertical slices mean several things appear in thin form before their full form. Each is **introduced** by one specification, which defines it in its owning module or factory; later specifications **extend** it — adding states, fields, kinds, methods or rules — and never redefine what exists. A specification that needs something not listed here claims it in its own Owns section, and the reviewer checks no other claims it. Factory specifications may extend only factory-owned rows and may *use*, never extend, kernel rows.

| Lifecycle or contract | Owner | Introduced by | Extended by |
| --- | --- | --- | --- |
| Contracts, typed IDs, hashing | `contracts` | SPEC-01 | SPEC-11 |
| Revisions | `intent` | SPEC-04 | SPEC-11 |
| Event outbox and event union | `platform` | SPEC-03 | SPEC-10, SPEC-22 |
| Registries and manifest schema | `platform` | SPEC-03 | SPEC-13, SPEC-19 |
| Kernel SDK | `platform`, with port contracts from SPEC-06 and SPEC-08 in 0.1.0 | SPEC-03 | SPEC-13, SPEC-17, SPEC-19 |
| Blob store and garbage collection | `store` | SPEC-02 | SPEC-27 |
| Lanes | `store` | SPEC-02 | SPEC-17 |
| Station registry | `stations` | SPEC-06 | SPEC-17 |
| Item model, artifacts, references | `intent` | SPEC-04 | SPEC-11 |
| ChangeSet lifecycle and apply | `change` | SPEC-04 | SPEC-12, SPEC-16 |
| Impact walk and verdicts | `change` | SPEC-04 (one round, `unaffected` only) | SPEC-12, SPEC-16 |
| Decision record, kinds, flags and continuations | `decisions` | SPEC-04 | SPEC-15, SPEC-25 |
| Autonomy state, policy and tripwire | `decisions` | SPEC-15 | SPEC-25 |
| Task lifecycle, runs, turns and reports | `work` | SPEC-06 | SPEC-17, SPEC-19 |
| Context pack | `work` | SPEC-06 | SPEC-17, SPEC-23 |
| Matching and limits | `work` | SPEC-17 | SPEC-19 |
| Kernel MCP tool set | `surface` | SPEC-07 | SPEC-11, SPEC-17, SPEC-23 |
| REST API and event stream | `surface` | SPEC-10 | SPEC-22, SPEC-26 |
| Checks, evidence and freshness | `evidence` | SPEC-08 | SPEC-12 |
| Delivery port and idempotency ledger | `delivery` | SPEC-08 | SPEC-27 |
| Container topology, users and secrets | Compose deployment | SPEC-05 | SPEC-27 |
| SDLC item kinds and lifecycles | `factories/sdlc` | SPEC-09 | SPEC-14, SPEC-20 |
| SDLC workspace provider and copy-back tiers | `factories/sdlc` | SPEC-09 | SPEC-18 |
| SDLC capabilities and skills | `factories/sdlc` | SPEC-09 | SPEC-14, SPEC-18, SPEC-20, SPEC-21, SPEC-24 |
| SDLC templates and commands | `factories/sdlc` | SPEC-09 | SPEC-14, SPEC-20, SPEC-24 |
| `sdlc.github_pr` adapter and verification status | `factories/sdlc` | SPEC-09 | SPEC-24 |
| `notes` fixture factory | `factories/notes` (test) | SPEC-13 | SPEC-17, SPEC-19 |

## Releases after the MVP

Releases are outcomes, not plans. Each starts with a short foundation addendum — new decision records, spikes and exit criteria — approved at the previous review, and each must close without a breaking change to the kernel SDK; a release that finds it needs one stops and raises a decision.

| Release | Outcome | Main additions | Kernel change expected | Depends on |
| --- | --- | --- | --- | --- |
| R1 — Factories as packages, RE static | A third-party or in-house factory installs as its own package; a reverse-engineering project analyses trusted binaries and delegates code to SDLC (S6) | Factory packaging and release signing, factory-specific UI views, the `re` factory (static analyst with Ghidra headless and rea, finding writer, `reproduce` and `cross_tool` checks, report export) | None; factory views use existing UI extension points | MVP |
| R2 — Restore, semantic search, L3 | Projects carry a restorable snapshot of intent; search finds by meaning; verified pull requests can merge without a person | Repository snapshot and restore, vector search and near-duplicate merging, autonomy L3 and auto-merge, baseline generation from an existing codebase, the pi agent | None | MVP |
| R3 — T2 stations | Untrusted code and dynamic analysis run in a fresh microVM per run | microVM station, network sandbox profiles, dynamic RE capabilities, DAST for a `qa` factory | None; tiers are registry entries | R1 |
| R4 — T3 stations, hardware and computer use | Agents operate desktop applications and attached devices under runbooks | Full-VM station with device passthrough, bench and flashing tools as tool servers, screen-and-input toolbox, runbook items gating irreversible actions, a first hardware-adjacent factory (`pcb` or `cad`) | None; the `irreversible` flag and I-20 already exist | R3 |

**What would count as a design failure.** If R1's RE factory needs a new kernel verb, kind or decision class, or if R3 or R4 need the kernel to know a station's internals, the kernel boundary was drawn wrong. The M5 review checks this explicitly against the factory sketches before R1 is planned.

## Risks and mitigations

Risks are revisited at every milestone review. Each specification lists the risks it mitigates.

| Risk | Mitigation | Proven by |
| --- | --- | --- |
| The kernel abstraction is wrong or premature: software needs fight the grammar, or generality slows the MVP | The SDLC factory is built alongside the kernel from M1, so every seam has a real user; the `notes` factory proves neutrality at M2; generality beyond that is not built; the M5 review tests the boundary against the factory sketches | M1-01, M2-05, M5 review |
| Indirection makes the system hard to follow: needs, matching, templates, manifests | Matching is deterministic and shown before a command runs; templates have six step types and no scripting; every run records the capability and template it used; the UI shows delegation trees | M4-04, M4-05 |
| Cooperation costs more than it saves, or loops | Depth ≤ 2, live-children cap, consult cache with single-flight join, consult ceiling, read-only lane, optional project cap, spend per capability visible; overflow is a structured error, never silent | M3-05 |
| Long-open MCP tool calls are unreliable in some agents | SPK-5; park-and-resume fallback with the same semantics | SPK-5, M3-05 |
| Factories weaken invariants through prompts or adapters | Conformance kit in each factory's CI; make/prove and namespace rules enforced by the loader; factories are operator-installed and pinned | M1-07, M2-05 |
| Cross-factory work produces stale results nobody notices | Results cross only as pinned items and blobs; interface items carry review edges; the regression sweep re-checks both sides | K3; S6 in R1 |
| The agent-host ecosystem is young and moves fast | Exact pins, a thin host using its packages unmodified behind a wrapper and a launcher (ADR-42), a CI protocol smoke test, upgrades only as deliberate commits; pi deferred to R2 | SPK-1, M4-05 |
| Claude subscription terms or credential selection change | Switching to an API key is configuration only; start-up guard and self-test against outranking credentials; credential list re-read on every adapter upgrade; token-expiry warning | SPK-1, M1-01 |
| Agent-run code reads model credentials, which have network egress | Accepted at T1; per-provider spend limits; rotation runbook; per-run isolation at T2 (R3) | M1-05, M5-06 |
| Agent-written code reaches Grindstone's credentials or forges evidence | Evidence only from the check station or another capability; host tokens unreadable by agents; signed host events; private clones with hooks disabled; CI cannot set the status | M1-02, M1-05, M1-07 |
| Agents stall, skip reports or exhaust context | One corrective prompt, then a typed failure; liveness timeout; failure causes with retry rules; escalation instead of loops | M1-03, M3-05, M3-06 |
| Removing budgets lets an API-key project overspend before anyone notices | Optional project cap; spend visible per tree and capability; provider-side spend limits recommended in the install runbook | M3-05, M3-07 |
| A long open consult holds the caller's writing lane | Consults run on the read-only lane; the operations view shows held lanes; the consult ceiling escalates | M3-05 |
| The skeleton takes longer than planned because integrations fight back | Spikes first; every part at its thinnest; scope is cut by deferring parts to M2, never by weakening an invariant or merging kernel and factory code | M0-03, M1 review |
| Workflows duplicate or lose side effects across crashes and upgrades | DBOS with idempotency keys; parked waits; explicit application versions; crash-and-resume tests per workflow (FF-10) | SPK-2, M1-04, M5-06 |
| Impact review is slow or noisy on large changes | One hop per round; embeds and mentions need no verdict; group verdicts; a round cap that raises a decision; performance budget (FF-14) | M2-03, M3-01 |
| A reviewer marks items unaffected too readily | Every verdict needs a reason; affected evidence still goes stale mechanically; auditors see what a verdict stopped | M3-01 |
| Prompt injection through external signals or analysed content | Fixed-code mapping with no agent reading first; untrusted content reaches only drafting capabilities; everything derived stays `untrusted` and needs a person | M5-03 |
| The policy answers wrongly at higher autonomy | L1 by default; eligibility classes; always-asked flags; every answer revertible; the tripwire; L3 deferred | M5-04 |
| On free plans the remote does not enforce the merge gate on private repositories | Delivery modes: Grindstone merges itself and reports every bypass as a finding; the mode is visible on every delivery (ADR-40) | M1-02 |
| With one agent family, author and reviewer share blind spots | Reviewers on a different model in a fresh read-only session; mechanical provers and the test reviewer carry the gate; revisit when a second provider is added (ADR-41) | M3-06 |
| Dogfooding couples Grindstone's development to its own bugs | A manual path stays open (plain pull requests that touch no published file); the scripted agent and test repository are independent of Grindstone's own repository; a stable instance orchestrates | M1-08 |
| The implementer weakens the tests it writes | Test reviewer as a required prover; protected and reviewed copy-back tiers; operator reviews pull requests below L3 | M1-05, M1-07 |
| Ceremony drives the operator around the system, and intent rots | `/patch` for small changes; scope decisions instead of refused copy-backs; mentions notify; group verdicts; governed share is a success measure | M4-06, M3-01 |
| Verification is slow in a cache-less runner | A job runs only the ticket's criteria; dependencies baked into the toolchain image; a shared build cache stays out because repository code could taint later evidence | M3 review |


# Planning playbook

How planning agents turn this foundation into specs that fit together. It adds no decisions.

## Working rules

1. **Read the foundation first, all of it.** Every specification cites the invariants, quality scenarios and decision records it implements, and uses the terms of the glossary and the Concepts tab exactly.
2. **One specification per entry in the spec map.** A specification delivers the exit criteria listed for it — for a shared criterion, the clause it names — may add acceptance criteria of its own, and never delivers another milestone's criteria. Milestone-level criteria are checked at the milestone review. A specification too large to review in one sitting is split into numbered parts under the same ID.
3. **Know which side of the line you are on.** A kernel specification owns a module in `grindstone` and may not name a factory kind, capability, template, method or adapter — its examples use the `notes` factory. A factory specification owns part of a package in `factories/<ns>/` and may use only `grindstone.sdk`. A specification that needs both is two specifications.
4. **Respect the module map.** A specification depends on specifications of its own or an earlier milestone, without cycles, and uses other modules only through their service interfaces, events and contracts — never their tables. Where a lower module must trigger a higher one, it uses a continuation or an event (Components tab).
5. **Own state once.** Each specification lists the state, lifecycles, contracts and configuration keys it owns. Every lifecycle has exactly one owning specification, which alone defines and writes its transitions. The Roadmap's ownership table says which specification introduces each and which may extend it.
6. **Decide in the right place.** A choice inside one module or one factory is the specification's to make, with its reason and rejected options. A choice that crosses a module or factory boundary, changes a contract others use, adds a component, adds a dependency that crosses a module or factory boundary or is exposed through a contract or the SDK, adds a kernel kind, a check shape, a step type, a decision class or a station tier, or contradicts a record is proposed as a new decision record and accepted before dependent work proceeds.
7. **Never invent answers.** Anything undecided becomes an open item with a stated default and the step that resolves it: a time-boxed spike or the first implementation step.
8. **Check current facts.** Versions, APIs, policies and limits are checked against primary sources when the specification is written, and cited; dependencies are the latest stable release compatible with the other pins, pinned exactly (ADR-46).
9. **Prefer less.** Each new component, dependency or abstraction states why configuration, an off-the-shelf part or existing glue would not do. In a factory, data beats code: a new adapter or check method states why a manifest entry could not do.
10. **Write just in time.** Specifications for a milestone are written while the previous one closes, against the code that exists. When implementation shows a better design inside the specification's scope, the specification is revised in the same pull request; it never silently drifts from the code.
11. **Scale evidence with change size.** A local change needs its impact and tests. A design change also needs a target design, a migration path and a staged plan. An architectural change — anything touching the concepts, an invariant, the module map or the SDK — also needs an independent review.
12. **Extend, don't redefine.** New names enter through registries in their own namespace; no specification changes the meaning of a name another relies on. Contract changes are additive — new optional or defaulted fields, new kinds and states — so they pass the schema diff; a breaking change follows ADR-05, with a version bump and an upgrade path.
13. **Keep make and prove apart in every design.** Any workflow a specification defines names, for each produced subject, who makes it and who proves it, and they are never the same capability (I-15).
14. **Add the fitness function with the structure.** A specification that adds a module, a boundary, a lifecycle or an external effect adds or extends the fitness function that guards it.

**Walking-skeleton specifications (M1).** SPEC-01 to SPEC-10 cover only the M1 slice and are written compactly: every template heading stays, but a section with nothing to say for M1 reads "Not in M1 — see SPEC-nn" or "n/a" with a reason, and a checklist item that cannot apply is marked n/a with a reason. Aim for two to four pages each. The ten may be reviewed together in one pass by a reviewer that wrote none of them. Ownership, cited invariants, delivered exit criteria and acceptance criteria tied to tests are never skipped: they are what later specifications extend.

## Specification lifecycle and template

1. **Draft** — written from the template while the previous milestone closes, in `docs/specs/SPEC-NN-<slug>.md`.
2. **Review** — the author runs the validation checklist; a reviewer that did not write it reviews it (make and prove applies to specifications too). A specification that changes a design across modules, touches the SDK or proposes a decision record also gets an independent architecture review.
3. **Accepted** — the checklist passes and proposed records are accepted. Its requirements and acceptance criteria are broken down into tickets.
4. **Implemented** — every acceptance criterion has a passing test or check, and every exit criterion it delivers passes.
5. **Revised** — when implementation teaches something, the specification changes in the same pull request as the code.

From M2, Grindstone's own specifications are held as `sdlc.spec` artifacts; from M4 new ones are drafted through `/plan`. The template is the same either way: requirements become `sdlc.requirement` items and acceptance criteria become `sdlc.criterion` items.

**IDs in specifications.** Each specification allocates project-unique item IDs in blocks so they survive import unchanged: SPEC-nn uses REQ-nnxx, DEC-nnxx, SCN-nnxx, NG-nnxx and OQ-nnxx (the third requirement of SPEC-06 is REQ-0603), and plans its tickets as TKT-nnxx with criteria AC-nnxx-k (AC-0601-2). Tests carry those criterion IDs from their first commit. Foundation identifiers (I-, QG-, QS-, FF-, ADR-, Mn-nn, Q-, SPK-, K, S) are cited as text, not items, and the traceability check resolves them against `docs/foundation/`.

```markdown
# SPEC-NN — <title>
Status: draft | in review | accepted | implemented · Milestone: Mn
Kind: kernel | factory <ns> · Owns: <modules or factory parts>

## 1. Purpose
One paragraph: what this makes possible and for whom.

## 2. Scope
In scope. Out of scope, each with the specification, milestone or release that covers it.

## 3. Foundation links
Implements: I-nn, ADR-nn, QS-nn — and how.
Delivers: Mn-nn → AC-nnxx-k, …
Depends on: SPEC-nn — exactly what is used from each (factory specs: SDK surface only).
Scenarios: K1–K4 or S1–S6 steps this specification makes true.

## 4. Requirements
REQ-nnxx: one testable statement each.

## 5. Design
Contracts: models, schemas, events, with schema versions.
State and ownership: tables in the owned schema; lifecycle transition tables and their writer.
Behaviour: workflows and steps; the idempotency key of every external action;
  failure causes, timeouts and retries; typed errors returned.
Interfaces: REST, kernel MCP tools, SDK functions, UI, CLI.
Configuration: keys, defaults, validation in grindstone check.
Security: trust boundaries touched, station tier, secrets, untrusted inputs.
Make and prove: for each subject produced, who makes it and who proves it.
Fitness functions: added or extended.

## 5F. Factory manifest (factory specifications only)
Item kinds (fields, semantic flags, relations and impact rules, lifecycles).
Capabilities (offers, workspace, permissions, may prove, tier, limits).
Templates (steps, edges, max_rounds, decisions).
Check methods and their kernel shape. Subjects and workspace providers.
Delivery adapters. Interface shapes provided or consumed.
Decision kinds and eligibility classes. Conformance kit results.

## 6. Decisions
DEC-nnxx: decision · reason · rejected options.
Proposed records: ADR drafts, if any.

## 7. Tickets and acceptance criteria
TKT-nnxx: summary · implements REQ-nnxx · depends on TKT-… · declared paths.
AC-nnxx-k: statement · verifies REQ-nnxx · method · test name.

## 8. Test plan
Per AC: unit, property, golden round-trip, crash-and-resume, in-memory tool,
  contract, conformance kit, scripted agent, integration, security,
  performance or live run.

## 9. Open items and risks
OQ-nnxx: question · default · resolved by.
Risks this specification mitigates or adds.

## 10. Rollout
Migrations, schema and SDK version bumps, factory upgrade steps,
  upgrade path for stored data and in-flight workflows.
```

Section 5F is required for factory specifications and absent from kernel specifications. A kernel specification that cannot explain itself without a software example has a design that leaks.

## Validation checklist

A specification is accepted only when every item holds. The reviewer records the result in the specification's pull request.

1. Every section of the template is present; nothing says "TBD" without an open item, a default and a resolution step.
2. Every requirement is one testable statement with a stable ID.
3. Every acceptance criterion names the requirement it verifies, its method and the test that proves it; every requirement has at least one.
4. Every exit criterion the spec map assigns — or the named clause of a shared one — maps to acceptance criteria; nothing assigned to another specification is claimed.
5. Every invariant, quality scenario and decision record the specification touches is cited, and no design element contradicts one.
6. Dependencies are only on own- or earlier-milestone specifications, without cycles, each naming exactly what is used, and they follow the module map.
7. No state, lifecycle, contract or configuration key is owned twice; anything owned elsewhere is used only through its owner's interface; the ownership table is respected.
8. Every external action has an idempotency key or lookup, and a crash-and-resume test covers it.
9. Every boundary is typed by a Pydantic contract with a schema version; generated artifacts are named.
10. Stored data changes come with a migration and an upgrade path for in-flight workflows.
11. Trust boundaries are respected: no credential reaches a station beyond what its tier allows; untrusted inputs are marked, validated and scoped.
12. Anything that could be a stored flag but is derivable is computed instead.
13. Every new component or dependency states its reason and exact pinned version, checked against a cited primary source.
14. Cross-module and cross-factory choices are proposed as decision records, not decided inline.
15. Every service operation returns typed errors from the documented classes; none is swallowed.
16. The test plan uses the required kinds from the testing strategy; live runs only where a real agent is the point.
17. Terms match the glossary and the Concepts tab; new terms are defined once.
18. The specification is small enough to review in one sitting, or is split into parts.
19. **Kernel specifications** name no factory kind, capability, template, method or adapter, and pass with the `notes` factory alone.
20. **Factory specifications** register every name in their own namespace, use only `grindstone.sdk`, and include a complete section 5F that passes the conformance kit.
21. Every produced subject has a named maker and a different named prover; no required check can be satisfied by its maker.
22. Every cooperation designed (`ask`, `delegate`, `load_skill`) states its need, mode, the limits that bound it and what crosses the boundary as pinned items or blobs.
23. Every action that cannot be undone by a ChangeSet is marked `irreversible` and reaches a person.
24. The fitness functions that guard what the specification adds exist or are extended, and pass.

## Traceability and changing the foundation

**The chain.** Quality goal → quality scenario → invariant or decision record → exit criterion → specification acceptance criterion → test. The Roadmap's spec map links exit criteria to specifications; each specification links them to its acceptance criteria; each test carries the ID of the criterion it proves. The traceability check (FF-13) fails when an exit criterion has no specification, an acceptance criterion has no test, a document cites an ID that does not exist, or a superseded record is cited as binding. From M2, Grindstone runs the same checks on its own specifications as items.

**Changing the foundation.** The operator, as product owner, approves every change to this set. A change updates every tab that states the affected decision in the same edit, and is checked for matching counts, coverage and stale references.

| Change | How |
| --- | --- |
| A decision | A new record superseding the old one; Product, Architecture, Concepts, Components and Factories text updated in the same edit; every citation checked |
| The concepts, an invariant, the module map or the SDK | A decision record plus an independent architecture review; every factory's conformance kit and every fitness function re-run |
| Scope, non-goals or success measures | Product and Roadmap updated together with a decision record; flagged as a scope change |
| Milestone order or exit criteria | Edited at a milestone review, with the reason in the revision history; criteria of closed milestones never change |
| A new factory | Its own specification set under this playbook; a foundation change only if it needs a kernel change, then treated as above |
| A fact from a spike or a primary source | The affected open question is closed with its answer; a record only if a decision changes |

**Revision history**

| Version | Date | Change |
| --- | --- | --- |
| 4.6 | 18 October 2026 | From the first review of the M1 specifications, accepted by the operator: ADR-45 (the delivery port's operations: `observe_mode`, `prepare`, `deliver`, `observe`, and optional `publish_gate_state` and `accept`; amends ADR-26) and ADR-46 (dependencies are the latest stable release compatible with the other pins; amends ADR-01). The Concepts delivery port, the SDK's adapter ports and the constraints table follow. The ownership table splits revisions (SPEC-04) from contracts, lanes (SPEC-02) from the station registry (SPEC-06), has SPEC-04 introduce the one-round walk, and names SPEC-06 and SPEC-08 as contributors to SDK 0.1.0. Editorial: `storage_limit` replaces `budget_exhausted` in the blob store; limits replace budgets in project configuration; `request_permission` is a suspending tool; kinds declare an ID pattern; a delivery is complete when it reaches `delivered`; lifecycle columns have an enum or an equivalent constraint; the decision index lists ADR-42 to ADR-46. Playbook rule 6 names which dependencies need a record. |
| 4.5 | 17 October 2026 | Accepted by the operator: ADR-44 (semantic hashes omit fields at their default, hashes written `sha256:<hex>`; amends ADR-08 and the hashing contract; from SPEC-01, carried by its first review); and, from the M0 spikes, ADR-42 (the agent host uses its packages unmodified behind a backend wrapper and a vendored launcher; amends ADR-15; resolves Q-1) and ADR-43 (a skill's tools are listed from session start and refused until it is loaded; amends ADR-39). The agent-host component, the skills concept, the glossary's hash, the hashing contract, Q-1, Q-5 and the risk table follow. |
| 4.4 | 17 October 2026 | ADR-41: Claude Code is the only agent for now; Codex deferred with SPK-3, Q-3 and Q-4; reviewer independence becomes a different Claude model in a fresh session until a second family exists. M0-03, M3-06, SPEC-18, the capabilities table and the risks follow. |
| 4.3 | 17 October 2026 | ADR-40: delivery observes whether the remote enforces the merge gate; in unenforced mode Grindstone merges itself and reports bypasses. I-08, M1-02, SPK-4, the threat model, the evidence-integrity measure and the risks updated; ADR-27 marked amended. |
| 4.2 | 17 October 2026 | M0 kickoff: open questions Q-1 to Q-11 answered by the operator; ADR-37 replaces budgets with limits (supersedes ADR-20), ADR-38 holds consults open until they answer under a ceiling, ADR-39 materializes start skills per session and returns `load_skill` bodies inline; QS-15 added; the task lifecycle table restated in text, since the diagram that held it was not reproduced; diagram placeholders replaced by captions; the export's duplicate title removed. This repository copy is the maintained source from this version on. |
| 4.1 | 17 October 2026 | From an external review: delegating and asking the operator end the turn and free the lane (no writing-lane deadlock); the workspace provider returns a collect outcome with extra checks and permission requests, so path policy stays in the factory; budgets split into run limits and a per-unit tree budget, replacing a fixed fraction of the parent; blobs are rooted from the moment they are written; any kind may have a lifecycle and lifecycle state is never hashed; compact walking-skeleton specifications for M1. |
| 4.0 | 17 October 2026 | First self-contained foundation: product, architecture with quality scenarios, threat and failure models and fitness functions, kernel concepts, component specifications, factories with the complete SDLC factory, 36 decision records, roadmap M0–M5 with 39 exit criteria and 27 specifications, and this playbook. |


