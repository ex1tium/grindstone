# SPEC-03 — Platform: registries, loader and configuration
Status: in review (revision 2 answers confirmation 1, `docs/specs/reviews/M1-specifications-confirmation-1.md`; revision 1 answers review 1 and architecture review 1, `docs/specs/reviews/SPEC-03-review-1.md`, `SPEC-03-architecture-review-1.md`) · Milestone: M1
Kind: kernel · Owns: `grindstone.platform` (registries, factory manifest schema and loader, kinds declared as data, instance and project configuration, `grindstone check`, the event outbox, event union and dispatcher, secret grants) and `grindstone.sdk` 0.1.0

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

The kernel ships no domain of its own: every kind, specialist, workflow, proof method, workspace and delivery target arrives as a registered name from a factory (ADR-21, ADR-23). This specification builds the place those names live and the gate they pass through:
- registries;
- a loader that validates each factory's manifest before anything of it is used, and refuses names outside its namespace (I-18) and check plans in which a maker could prove its own work (I-15, M1-07);
- configuration as validated, hashed data that no agent can reach (I-14);
- the transactional outbox through which every state change becomes one typed event.

It also fixes the first cut of the kernel SDK, the only package a factory imports.

## 2. Scope

In scope:
- Registries and the `core` names the kernel registers.
- The manifest schema and the loader, including kinds declared as data and compiled into contracts.
- Load-time rules: namespaces, references, make and prove, check-method shapes, linear templates.
- Instance and project configuration, their hashes and `grindstone check`.
- Secret grants.
- The event outbox, per-project sequence numbers, the event union and the dispatcher that delivers events to module consumers once.
- `grindstone.sdk` 0.1.0.

Out of scope:
- Manifest rules as registered Python functions, nightly rule runs and the conformance kit: SPEC-13 (M2).
- Template graphs with edges, `fan_out`, `check`, `change` and `decide` steps, and bindings over the item graph: SPEC-19 (M4). M1 templates are linear.
- Interpreting a kind's lifecycle table, references and rendering: SPEC-04. This specification parses and validates the declarations.
- Matching beyond the load-time check: SPEC-06 (thin), then SPEC-17.
- The event stream to clients: SPEC-10. This specification provides the outbox it reads.
- Enabling a factory through a `scope` decision: SPEC-15 (M3). In M1 the operator's authenticated configuration command is the only way to change a project's configuration, and it is recorded with provenance (OQ-0301).
- Separately installable factory packages: R1.

## 3. Foundation links

Implements:
- ADR-21: a factory is one package with a seven-part manifest registering names only in its namespace, data first, code only for adapters and check methods. The `notes` fixture shows that a code-free factory is valid.
- ADR-23: capabilities are versioned, hashed files; projects override a bounded set of fields; nothing here is proposable.
- I-18: names only in the factory's own namespace; `core.*` meaning is never redefined; the kernel never imports a factory (FF-01).
- I-15, M1-07 (load clause): a check plan whose prover can be its maker is refused at load.
- I-14: configuration lives in the control plane's store and files, never in a workspace; no tool proposes it.
- I-06: every configuration a run used is hashed, so SPEC-06 can record it.
- ADR-05: manifests, configuration and events are Pydantic contracts with schema versions; events form a discriminated union.
- ADR-13 is not implemented here. Rules arrive with SPEC-13, and nothing in M1 needs a registered rule.

Delivers:
- M1-07, the load clause: "a check plan whose prover resolves to the maker's capability is refused at load" → AC-0307-1, AC-0307-2. SPEC-08 delivers the plan-time guard, and SPEC-09 the SDLC check plan.

Depends on:
- SPEC-01: `Contract`, `semantic_hash`, `item_id_type` with kind patterns and examples, `ErrorEnvelope` and its code registry.
- SPEC-02: the unit of work, migrations, the workflow helper and deterministic workflow IDs for the event dispatcher.

Scenarios: K1 step 1 (a template step names a need, inputs and a check by another need) and step 2 (the need resolves to a registered capability).

## 4. Requirements

REQ-0301: Registries hold every kind, edge type, need, capability, template, check method, subject kind, subject resolver, workspace provider, delivery adapter, decision kind, error code and event type by full namespaced name, and the kernel registers its `core` names before any factory loads.
REQ-0302: The loader discovers factories through the entry-point group `grindstone.factories`, reads each factory's `manifest.yaml` from its distribution's files with a safe YAML loader and without importing the package, validates it against the manifest schema, and registers all of its names or none.
REQ-0303: A manifest that registers a name outside its namespace, registers a name already registered, offers a need of another factory's namespace, or declares a factory SDK range the running SDK does not satisfy is refused.
REQ-0304: A refused factory stays unloaded and is listed in the start-up report with the file, field and rule that failed; projects that enable it are paused; the kernel and every other factory still start.
REQ-0305: Item kinds are declared as data: fields from a fixed type vocabulary, each semantic unless marked presentation, typed references with target kinds, cardinality and edge type, an ID pattern with example IDs, and optionally a lifecycle table. The loader compiles each kind into a `Contract` subclass whose hash follows SPEC-01.
REQ-0306: A capability is validated at load: its prompt and skill files exist, its report schemas are valid JSON Schema, its offers name needs it may offer, a capability with a writing workspace declares no check methods it may perform, and, in M1, a capability whose `permissions.otherwise` is `decision` is refused until SPEC-15 gives permission decisions their expiry (SPEC-06 part 2, DEC-0608). Its hash is the semantic hash of its declaration together with the SHA-256 of every file it names.
REQ-0307: A template step whose check plan names a prover need that any loaded capability offering the step's maker need also offers, or that the step's own capability offers, is refused at load (make and prove).
REQ-0308: Every template step names a need offered by some loaded capability in the step's mode, and M1 templates are a linear sequence of `task` and `deliver` steps.
REQ-0309: Every factory check method declares exactly one kernel execution shape (`command`, `test`, `reproduce`, `cross_tool`, `review` or `manual`), and a step whose check uses a method of an unregistered shape is refused.
REQ-0310: Instance configuration is read from `grindstone.toml` into one typed contract, with secrets named by file path only; an invalid file stops start-up with the file, field and rule.
REQ-0311: Project configuration is a TOML document stored by the control plane as numbered versions with their hash and provenance; each enabled factory's section is validated against the schema that factory registered; no workspace, tool or report can change it.
REQ-0312: `grindstone check` validates instance, factory and project configuration together and exits non-zero naming the file, field and rule of every error; a project whose current configuration is invalid is paused.
REQ-0313: A module records an event in the same unit of work as the change it describes, with a UUIDv7 event ID and a per-project sequence number that increases by one with no gaps; events are instances of one discriminated union of registered event models.
REQ-0314: Each registered event consumer receives each event of its types exactly once, as a workflow whose ID is derived from the consumer and the event ID, and the dispatcher resumes from its cursor after a crash.
REQ-0315: A factory reads a secret only through the context the kernel hands its adapter, by a name its manifest declares and its project grants; any other name is refused with `secret_not_granted`, and no decision is raised.
REQ-0316: `grindstone.sdk` 0.1.0 exports exactly the names in section 5's export table, imports only `contracts` and `platform`, and gives factories services only through context objects that kernel code constructs; the context and port protocols are defined in `grindstone.contracts.ports`, so no kernel module that builds a context or calls a port imports the SDK; FF-01 refuses any other import from `grindstone` in a factory.
REQ-0317: The registries answer, for any loaded name, its factory, factory version, manifest hash and, for a capability, its hash; the instance and project configuration hashes are readable for any project.
REQ-0318: Cross-factory load rules (make and prove, offered needs, references to other kinds) are evaluated over the union of the factories accepted alone, repeated until no further factory is refused, so the result never depends on the factories' names or load order.
REQ-0319: Event consumers are order-independent: each reads current state through its owner's interface rather than relying on the order in which events of different sequence numbers reach it.

## 5. Design

**Contracts** (in `grindstone.contracts.platform`, schema version 1 each unless noted):

| Model | Holds |
| --- | --- |
| `FactoryManifest` | `name` (the namespace), `version` (semantic), `sdk` (a version range), and the declarations `kinds`, `edges`, `capabilities` (paths to capability files), `templates`, `check_methods`, `workspace_providers`, `delivery_adapters`, `decision_kinds`, `secrets` (names), `config_schema` (path to a JSON Schema for the project's section of this factory), `code` (optional: a module whose `ADAPTERS` maps adapter and method names to classes) |
| `KindDecl` | `name`, `id` (`pattern`, `examples`, and optionally `allocate`, a format such as `FND-{n}` for kinds whose IDs the kernel allocates), `fields` (name → `FieldDecl`), `lifecycle` (optional: `states`, `initial`, `transitions` of `from`, `to`, `writer`) |
| `FieldDecl` | `type`: `string`, `text`, `integer`, `boolean`, `enum` (with `values`), `ref` (with `kinds`, `edge`, `cardinality` one or many), `blob`, or `list` of one of those; `presentation` (default false); `required`; `default` |
| `EdgeDecl` | `name`, `inverse`, `from_kinds`, `to_kinds`, `impact` (`review`, `notify` or `render`), `check_dependency` (bool) |
| `CapabilityDecl` | The fields of Concepts, "Capability": `id`, `version`, `prompt`, `agent` (`preset`, `model` as a named model slot, `effort`), `skills` (`library`, `start`), `toolbox`, `workspace` (`write` with a named workspace provider, or `read_only`), `permissions` (`allow`, `otherwise`: `deny` or `decision`), `produces` (`reports`, `kinds`), `offers` (`need`, `modes` from `delegate`, `consult`, `check`, `accepts`, `yields`, `tags`), `may_check` (`method`, `subjects`), `tier`, `limits` |
| `TemplateDecl` | `name`, `command`, `args` (JSON Schema), `steps`: `task` (`name`, `need`, `mode`, `inputs`, `output`, `checks` of `method`, `by`, `required`, `targets`, `limits`) or `deliver` (`name`, `adapter`, `from` a task step) |
| `CheckMethodDecl` | `name`, `shape`, `env_relevant` (bool), `config_schema` |
| `InstanceConfig` | Sections contributed by their owners: `[store]` (SPEC-02); `[stations]`, `[agents]`, `[limits]`, `[host]` (SPEC-06); `[checks]`, `[delivery]` (SPEC-08); `[surface]`, whose `mcp_*` keys are SPEC-07's and the rest SPEC-10's; and this specification's `[platform]` (`factories_allowed`), `[images]` (name → digest-pinned reference) and `[secrets]` (name → file path) |
| `ProjectConfig` | `[project]` (`name`), `[factories]` (namespace → exact version), `[grants]` (`tiers`, `secrets`), `[checks]` (`image`, a name from `[images]`), `[capabilities."<id>"]` (overrides: `model`, a model slot name as in `CapabilityDecl`, never a model; `effort`, `limits`, `extra_prompt`), and `[factories.<ns>]` sections validated by that factory's schema |
| `EventEnvelope` | `event_id` (UUIDv7), `project` (a project ID, or the instance stream's nil ID), `seq`, `type`, `occurred_at`, `payload` |

Each registered event model has a literal `type` and a schema version. The union of all kernel event models is assembled in `grindstone.contracts.events` and generated for TypeScript like every other contract (FF-02). This specification adds `factory.loaded`, `factory.refused`, `project.configured` and `config.invalid`.

Kernel error codes declared here, in `grindstone.contracts.errors` (SPEC-01): `manifest_invalid`, `config_invalid`, `name_conflict` and `secret_not_granted` (validation), and `factory_unavailable` (transient). The registry's `core` names copy the whole kernel list; the registry itself is how factories add codes.

**Modes.** A task's mode and an offer's mode map one to one: a `work` task matches offers serving `delegate`, `consult` matches `consult`, and `check` matches `check`. `CapabilityDecl` documents the mapping; SPEC-06's matching and the make-and-prove rule below both use it.

**Needs.** A factory registers needs only in its own namespace, by offering them, and may also offer `core` needs (`core.review.impact`, `core.advise`). Offering another factory's need is refused (`manifest_invalid`); requesting one, in a template or a `delegate` call, stays allowed, which is all that S6 and K3 need.

**Events from factories.** In SDK 0.1.0 factories register no event types; the union is kernel-only, so it can be generated at build time. Factory events, if a later factory needs them, arrive as an envelope with a factory-owned payload schema in a minor SDK version.

**Registries.**
- In memory, built at start-up in two phases (REQ-0318), then frozen. A factory version change takes effect only on restart.
- `platform.factories` records each load: `name`, `version`, `manifest_hash`, `status` (loaded or refused), `report`, `loaded_at`. The table is history, insert-only, and the registries are rebuilt from the packages at each start.
- The `core` names: the five kernel kinds and their fields (as declared by SPEC-04), the needs `core.review.impact`, `core.advise` and `operator`, the six check shapes, the subject kinds `git_commit`, `blob`, `blob_set` and `item_revision`, the kernel decision kinds (SPEC-04), and every kernel error code and event type.

**Loader.**
1. Discover entry points in group `grindstone.factories`. For each, read `manifest.yaml` and the files it names from the distribution's file list through `importlib.metadata`, which imports nothing, so no factory code runs before its manifest is validated. A code-free factory's module is an empty `__init__.py`.
2. Parse with `yaml.safe_load` (DEC-0302) and validate into `FactoryManifest`.
3. **Phase 1, each factory alone:** schema, namespaces, SDK range, kinds, edges, lifecycles, capability files, check-method shapes, collecting every error. A factory with any error is refused.
4. **Phase 2, across factories:** over the union of the factories phase 1 accepted and the `core` names, check cross-namespace references, offered needs and make and prove. Refuse every factory with an error, then repeat phase 2 over the remaining union until a pass refuses nothing. A factory refused in a pass is not reconsidered when a later refusal removes the capability that caused its error; this is deterministic and safe, and the start-up report names, for every refusal, the other factory's capability or need involved. Because each pass checks the same set, the outcome does not depend on names or order (REQ-0318).
5. Only then import each accepted factory's `code` module if it declares one, check that every adapter, provider and method it names implements its SDK port, compile kinds, and register everything in one step.

Rules, each failing with `manifest_invalid` and the path of the offending field:
- Every name starts with `<namespace>.`. Edge names, needs, kinds, capabilities, templates, methods, providers, adapters, decision kinds and secrets are all namespaced; only `core` registers `core.*`.
- No name is registered twice (`name_conflict`).
- The SDK range is satisfied: a PEP 440 specifier set evaluated with `packaging` (DEC-0303), for example `>=0.1.0,<0.2.0`.
- Each `ref` field names registered or same-manifest kinds and an edge whose `from_kinds` and `to_kinds` admit it. A reference outside the namespace may target only `core.*` kinds (I-19, ADR-25).
- Each kind's ID pattern is an anchored regular expression, and each example matches it and SPEC-01's base grammar.
- Each lifecycle has its `initial` among its `states`, and each transition names states of the table and exactly one writer. SPEC-04 defines the writers.
- Capabilities and check methods as REQ-0306 and REQ-0309.
- Templates as REQ-0307 and REQ-0308.
- Every adapter, provider and method a manifest names exists in `ADAPTERS` and implements its SDK port (step 5).

**Make and prove at load (REQ-0307).** For each `task` step with maker need `N` and each check with a prover need `P`:
- `makers(N)` is the set of loaded capabilities that offer `N` with mode `delegate` or `consult`.
- `provers(P)` is the set that offer `P` with mode `check`.
- The step is refused if the two sets intersect, or if any capability in `provers(P)` has a writing workspace.
- Mechanical checks, whose `by` is a check station, cannot be makers by construction.

The check is over every factory accepted by phase 1, because matching (SPEC-06, SPEC-17) can pick any enabled capability. A refused template refuses its whole factory, so a factory never runs half-checked. SPEC-08 repeats the guard when a task's check plan is built, against the actual maker (I-15).

**Kinds as data.** `KindDecl` compiles with `pydantic.create_model` into a `Contract` subclass named after the kind:
- the type vocabulary maps to SPEC-01's admitted types (no floats; lists are ordered tuples);
- `presentation: true` adds SPEC-01's `Presentation` mark;
- every kind gets a presentation field `title`;
- `ref` fields become typed `ItemId` fields for their target kinds' patterns.

Kinds are data only in M1 (DEC-0301). SPEC-04 owns what the fields mean at revision time.

**Capability hash.** `semantic_hash` of the `CapabilityDecl` with every file path replaced by the SHA-256 of the file's normalised bytes (prompt, skills, report schemas). Changing a prompt changes the hash, and so the run manifest of every later run (I-06).

**Configuration.**
- `grindstone.toml` is read with `tomllib`. Its location comes from `GRINDSTONE_CONFIG`, default `/etc/grindstone/grindstone.toml`, mounted read-only (SPEC-05).
- Project configuration is held in `platform.project_configs (project, version, toml, hash, provenance, created_at)`, insert-only; the current version is the highest.
- `platform.projects (id UUIDv7, slug, created_at)` gives projects their identity.
- A configuration change is one unit of work: validate, insert the version, emit `project.configured`.
- Validation checks:
  - each factory listed in `[factories]` is loaded at exactly that version;
  - each grant names a secret its factory declares;
  - `[checks].image` names an allowed image;
  - capability overrides touch only `model`, `effort`, `limits` and `extra_prompt` (Concepts, "Where capabilities come from"), and name existing capabilities;
  - each `[factories.<ns>]` section validates against that factory's `config_schema`.
- The `.grindstone/` export of the project configuration to the repository is SPEC-09's; the control plane's copy is the source of truth.

**`grindstone check`.** A CLI subcommand of the control-plane image. It loads factories exactly as start-up does, validates `grindstone.toml`, and, against the database if one is reachable or against files given with `--project FILE`, every project configuration. It prints one line per error, `file:field: rule`, and exits 1 if any. Start-up runs the same checks: an invalid instance configuration stops the process, and an invalid project configuration pauses that project (`config.invalid`).

**Secrets (REQ-0315).** `[secrets]` maps names to files: unprefixed for the kernel's own secrets (SPEC-05), namespaced for factory secrets (for example `notes.archive_token`). A factory reads one through `ctx.secrets.read(name)`. The context's factory and project were bound by the kernel when it built the context, so platform checks that this factory declares the name and this project grants it, and only then reads the file. A refusal is `secret_not_granted`: a configuration error, with no decision raised. Values are never logged, emitted in events or written to the database.

**Event outbox.**
- `platform.events (project, seq, event_id, type, schema_version, payload JSONB, occurred_at)`, primary key `(project, seq)`, with `event_id` unique.
- `platform.event_seq (project, last_seq)`: `emit(uow, event)` runs `UPDATE … SET last_seq = last_seq + 1 RETURNING` in the caller's unit of work, so sequence numbers are gapless per project and serialized with the change they describe.
- After commit, `NOTIFY platform_events` wakes the dispatcher and the SSE stream.

**Dispatcher (REQ-0314, REQ-0319).** Modules register consumers at the composition root (`platform.consume(name, types, workflow)`), which keeps lower modules from importing higher ones. A task in the lifespan reads events after each consumer's cursor in `platform.event_cursors (consumer, project, seq)`. For each event it starts `evt-<consumer>-<event_id>` through `store.start`, then advances the cursor. A crash between start and cursor update repeats a start, which DBOS ignores for an existing ID (SPEC-02). Consumers are workflows and follow SPEC-02's rules for their own effects. Two events for one consumer can run concurrently, so delivery is exactly once but not ordered: a consumer reads current state through its owner's interface (for example a task's current state, not the state named in the event) and does nothing when the state has moved on (REQ-0319).

**Kernel SDK 0.1.0** (`grindstone.sdk`, `__version__ = "0.1.0"`). The SDK holds no logic of its own: it re-exports contracts from `grindstone.contracts`, the context and port protocols (also in `grindstone.contracts`, below), and the platform registration helpers. It imports only `contracts` and `platform` (FF-01).

**Contexts (architecture review, A1).** Every port method takes a context, and factories never build one. `Context` is a protocol in `grindstone.contracts.ports`, re-exported by the SDK, with:
- `project` and `factory`, bound by the kernel;
- `items`: read a revision by `ItemRef`, rendered and typed (`intent.read_pinned`);
- `blobs`: open a blob by hash (`store.open_blob`);
- `storage`: the factory's storage directory for this project (DEC-0306);
- `secrets`: read a granted secret (REQ-0315).

The implementation lives in the composition root (`grindstone.app`), which alone may import `intent` and `store` together with `platform`. It registers a context builder with `platform` at start-up, and the module that calls an adapter (`stations`, `evidence` or `delivery`) asks `platform.context_for(project, factory)` for one. So no SDK import grows, and the factory identity a secret check reads is one the kernel bound. Contexts specific to one port extend `Context` in the specification that owns the port: `RunContext` (SPEC-06 part 1), `CheckContext` and `DeliveryContext` (SPEC-08).

**Where the protocols live (DEC-0308).** `Context`, its extensions, its service handles (`ItemReader`, `BlobReader`, `FactoryStorage`, `SecretReader`) and the four port protocols (`WorkspaceProvider`, `SubjectResolver`, `CheckMethod`, `DeliveryAdapter`) are `typing.Protocol` classes in `grindstone.contracts.ports`, beside the models the ports exchange. Every kernel module may import `contracts`, so `platform` (the loader's port check, `context_for`), `stations`, `evidence` and `delivery` type their calls under pyright strict without importing the SDK, which the module map forbids them. `grindstone.sdk` re-exports the same objects. Protocols are not models: the schema bundle and the TypeScript generation (FF-02) export only models listed in `EXPORTED`, which never lists a protocol.

**Exports (architecture review, A4).** Every name in SDK 0.1.0, with its owner:

| Names | Owner |
| --- | --- |
| `ItemRef`, `BlobRef`, `SubjectRef`, `SemanticHash`, `ErrorEnvelope`, `item_id_type`, `semantic_hash` | SPEC-01 |
| `FactoryManifest`, `KindDecl`, `FieldDecl`, `EdgeDecl`, `CapabilityDecl`, `TemplateDecl`, `CheckMethodDecl`, `Context`, `ItemReader`, `BlobReader`, `FactoryStorage`, `SecretReader`, `register_error_code` | SPEC-03 |
| `WorkspaceProvider` (`prepare`, `collect`, `discard`), `SubjectResolver` (`materialize`, `read_file`), `RunContext`, `Materialization`, `CollectOutcome` | SPEC-06 part 1 |
| `CheckMethod` (`build_job`, `environment`, `interpret`), `CheckContext`, `CheckSpec`, `JobPayload`, `TestOutcome`, `TargetResult`, `ReviewVerdict`, `DeliveryAdapter` (`observe_mode`, `prepare`, `deliver`, `observe`, and the optional `publish_gate_state` and `accept`, ADR-45), `DeliveryContext`, `PreparedDelivery`, `ModeObservation`, `VerificationState`, `Observation` | SPEC-08 |

The port signatures belong to the specifications named, which are written against this SDK version. A name added after acceptance is a minor SDK version; a name changed or removed is a major one (ADR-05). Testing helpers (the in-memory kernel and the conformance kit) arrive with SPEC-13.

**State and ownership.** Schema `platform`: `factories`, `projects`, `project_configs`, `events`, `event_seq`, `event_cursors`. No lifecycle columns; project pause is derived from the latest configuration's validity and the factory load status, never stored (FF-09).

**Behaviour.** Loading and configuration are start-up and request-time code with no external effects. The dispatcher's only effect is starting workflows, which is idempotent by ID.

**Interfaces.** Python: `registries` (read-only lookups), `load_factories()`, `check()`, `context_for(project, factory)`, `project_status(project)` (configuration validity and factory load status, from which paused is derived), `set_project_config(uow, project, toml, provenance)`, `project_config(project)`, `emit(uow, event)`, `consume(...)`, `events_after(project, seq)`. CLI: `grindstone check`.

**Security.**
- Factories are operator-installed code, trusted like a dependency but bounded at B5. They are pinned in `uv.lock`, never fetched at run time, and validated before use.
- YAML is parsed with the safe loader only, so no object construction is possible.
- Manifests and configuration are never in a workspace, so no agent can change them (I-14). SPEC-05's FF-06 proves the mount side.

**Make and prove.** This module produces no subjects. The load-time rule above is what enforces make and prove for every factory.

**Fitness functions.**
- FF-01 is extended: a factory package imports from `grindstone` only `grindstone.sdk`.
- FF-07 covers schema `platform`.
- The loader's refusal tests are the seed of the conformance kit (FF-11, SPEC-13).

## 6. Decisions

DEC-0301: Item kinds are declared only as data in M1 and compiled into contracts · One path serves code-free factories (the `notes` fixture, M2-05) and SDLC alike, and data can be validated before any factory code runs · Rejected: kinds as Python classes in factories (two declaration paths; a factory's import could run before validation). SPEC-11 may add Python-declared kinds if a kind needs a validator that data cannot express.
DEC-0302: YAML manifests parsed with PyYAML's safe loader, `pyyaml==6.0.3` (PyPI, released 25 September 2025, the latest; wheels for CPython 3.14) · Factory manifests are YAML by the foundation (Factories, "Code in a factory") · Rejected: TOML manifests (deep nesting reads poorly); `ruamel.yaml` (round-trip editing, which we do not need, at the cost of a larger dependency).
DEC-0303: SDK ranges are PEP 440 specifier sets checked with `packaging==26.3` (PyPI, released 4 August 2026, the latest; already in the lockfile as a test dependency) · Semantic versions such as `0.1.0` are valid PEP 440 versions, and the comparison is the one Python packaging already trusts · Rejected: a hand-written semver range parser (custom code for a solved problem).
DEC-0304: The registries are rebuilt from packages at every start and frozen; `platform.factories` is a history of loads, not a source · Factories are code pinned in the lockfile, so the package is the truth · Rejected: storing manifests in the database (two sources that can disagree).
DEC-0305: Events reach module consumers as workflows whose IDs are derived from consumer and event · Exactly-once delivery comes from SPEC-02's deterministic IDs with no consumer-side deduplication table · Rejected: per-consumer processed-event tables (duplicated idempotency code in every module).
DEC-0306: Each factory gets a storage directory per project, on the `repos` volume, through `ctx.storage` · A factory whose subjects live in a remote needs local mirrors and private working copies, which the foundation puts on `repos`, and a factory must not choose paths itself. The directory is disposable: a factory must be able to rebuild it from its remote, nothing in it is a record, it is excluded from backups (Operations, "Backup"), and it is removed when the project is deleted · Rejected: a version-control service in the kernel (domain knowledge in the kernel); letting factories pick paths on `repos` (one factory could write another's).
DEC-0307: Phase 2 of loading runs over the union of factories accepted alone, to a fixed point · A rule that reads "every loaded factory" while factories load one by one gives answers that depend on names · Rejected: name order (non-deterministic as factories are added); validating each factory against the kernel only (misses a maker in another factory, I-15).
DEC-0308: The context and port protocols are defined in `grindstone.contracts.ports` and re-exported by the SDK · The kernel modules that build contexts or call ports may import `contracts` but not `sdk`, and the protocols carry no logic, so they belong with the contracts they exchange (confirmation 1, C2) · Rejected: protocols in `grindstone.sdk` (FF-01 refuses the kernel's imports of them); adding `sdk` to those modules' allowed imports (a module-map change, and the SDK would become a dependency of the kernel it fronts); untyped calls (`Any`, which pyright strict refuses and which hides port mismatches).

## 7. Tickets and acceptance criteria

TKT-0301: Registries, `core` names, manifest contracts, SDK 0.1.0 surface and contexts · implements REQ-0301, REQ-0316, REQ-0317 · depends on TKT-0101 · paths `packages/grindstone/src/grindstone/platform/`, `packages/grindstone/src/grindstone/sdk/`, `packages/grindstone/src/grindstone/contracts/platform.py`, `packages/grindstone/src/grindstone/contracts/ports.py`, `packages/grindstone/tests/platform/`.
TKT-0302: Loader in two phases, kinds as data, capability hashing, load-time rules including make and prove · implements REQ-0302 to REQ-0309, REQ-0318 · depends on TKT-0301 · same paths plus `pyproject.toml` (pyyaml, packaging) and `packages/grindstone/tests/fixtures/factories/`.
TKT-0303: Instance and project configuration, secrets, `grindstone check` · implements REQ-0310 to REQ-0312, REQ-0315 · depends on TKT-0302, TKT-0201 · platform paths plus `packages/grindstone/src/grindstone/__main__.py`.
TKT-0304: Event outbox, union, dispatcher · implements REQ-0313, REQ-0314, REQ-0319 · depends on TKT-0202 · platform and contracts paths.

AC-0301-1: After start-up with no factories, the registries hold the five `core` kinds, the `core` needs, the six check shapes, the four kernel subject kinds and the kernel decision kinds, and registering a `core.*` name from a fixture factory fails `manifest_invalid` · verifies REQ-0301 · unit · `test_core_names_registered_first`.
AC-0302-1: A fixture factory in the `notes` style, with an empty module and a `manifest.yaml`, is discovered through its entry point and loaded; a manifest with a YAML tag that would construct an object is refused; a fixture package whose `__init__` would write a marker file is not imported until its manifest passes, and not at all when it fails · verifies REQ-0302 · unit · `test_loader_discovers_and_parses_safely`.
AC-0302-2: A manifest with one invalid template registers none of its kinds, capabilities or templates · verifies REQ-0302 · unit · `test_loader_registers_all_or_nothing`.
AC-0303-1: Each of: a kind named outside the namespace, a capability whose name collides with another factory's, an offer of another factory's need, and an SDK range of `>=0.2.0` — is refused with the offending field named · verifies REQ-0303 · unit · `test_namespace_and_sdk_range_rules`.
AC-0304-1: With one valid and one refused fixture factory, the process starts, the start-up report names the refused factory's file, field and rule, and `project_status` reports a project enabling it as paused while a project enabling the other runs · verifies REQ-0304 · integration · `test_refused_factory_does_not_stop_kernel`.
AC-0305-1: A kind declared with a presentation field, a `ref` field and an ID pattern compiles to a contract whose hash ignores the presentation field, whose `ref` field refuses an ID not matching the target kind's pattern, and a float field type is refused at load · verifies REQ-0305 · unit · `test_kinds_compile_to_contracts`.
AC-0306-1: Changing one byte of a capability's prompt file changes its hash; a capability with a writing workspace and a non-empty `may_check` is refused; a report schema that is not valid JSON Schema is refused · verifies REQ-0306 · unit · `test_capability_validation_and_hash`.
AC-0307-1: A fixture template whose `task` step needs `notes.write` and whose check is by need `notes.review`, where one capability offers both, is refused at load with `manifest_invalid` naming the step and the capability · verifies REQ-0307 · unit · `test_load_refuses_maker_as_prover`.
AC-0307-2: The same template with `notes.review` offered only by a read-only capability that does not offer `notes.write` loads · verifies REQ-0307 · unit · `test_load_accepts_separate_prover`.
AC-0308-1: A template step naming a need no loaded capability offers in its mode, or a template with a step type other than `task` and `deliver`, is refused · verifies REQ-0308 · unit · `test_template_steps_validated`.
AC-0309-1: A check method declaring an unknown shape, or two shapes, is refused · verifies REQ-0309 · unit · `test_check_methods_map_to_one_shape`.
AC-0310-1: A `grindstone.toml` with an inline secret value, or an image not pinned by digest, stops start-up naming the field · verifies REQ-0310 · unit · `test_instance_config_validation`.
AC-0311-1: Setting a project configuration twice creates versions 1 and 2 with different hashes and provenance; a factory section that fails the factory's schema is refused with its field named, and the previous version stays current · verifies REQ-0311 · integration · `test_project_config_is_versioned_and_validated`.
AC-0312-1: `grindstone check` on an invalid instance file and an invalid project file exits 1 and prints one `file:field: rule` line per error; on valid files it exits 0 · verifies REQ-0312 · unit · `test_grindstone_check_cli`.
AC-0313-1: Two concurrent units of work emitting events for one project produce sequence numbers with no gap or duplicate, and an event written in a rolled-back unit of work does not appear · verifies REQ-0313 · property · `test_event_sequence_gapless`.
AC-0314-1: The dispatcher killed between starting a consumer workflow and advancing its cursor delivers that event to that consumer exactly once after restart · verifies REQ-0314 · crash-and-resume · `test_event_dispatch_once`.
AC-0315-1: An adapter reading a secret its factory declares but the project does not grant, or one its factory does not declare, is refused with `secret_not_granted` and raises no decision; a granted one is returned and never appears in logs; an adapter has no way to build a context naming another factory · verifies REQ-0315 · unit · `test_secret_grants`.
AC-0316-1: A fixture factory importing `grindstone.platform` fails FF-01; one importing `grindstone.sdk` passes · verifies REQ-0316 · contract · `test_ff01_factories_use_sdk_only`.
AC-0316-2: `grindstone.sdk.Context`, `WorkspaceProvider`, `SubjectResolver`, `CheckMethod` and `DeliveryAdapter` are the same objects as in `grindstone.contracts.ports`; FF-01 passes with `platform`, `stations`, `evidence` and `delivery` typed against `contracts.ports`, and a fixture kernel module importing `grindstone.sdk` fails it; the schema bundle contains no protocol · verifies REQ-0316 · contract · `test_port_protocols_live_in_contracts`.
AC-0318-1: Two fixture factories, where the second's capability would make the first's template violate make and prove, give the same result (both evaluated, the first refused) whichever is named first; and a factory whose need's only offer is in a refused factory is refused in the next pass · verifies REQ-0318 · unit · `test_load_rules_independent_of_order`.
AC-0319-1: A fixture consumer given two events for one task in reverse order ends in the same state as in order · verifies REQ-0319 · unit · `test_consumer_order_independent`.
AC-0317-1: For a loaded capability the registries return its factory, factory version, manifest hash and capability hash, and these equal the values recorded in `platform.factories` for that start · verifies REQ-0317 · unit · `test_registry_provenance_lookups`.

## 8. Test plan

- Unit, with fixture factories in the `notes` style under `packages/grindstone/tests/fixtures/factories/`: AC-0301-1, AC-0302-1, AC-0302-2, AC-0303-1, AC-0305-1, AC-0306-1, AC-0307-1, AC-0307-2, AC-0308-1, AC-0309-1, AC-0310-1, AC-0312-1, AC-0315-1, AC-0317-1, AC-0318-1, AC-0319-1.
- Integration, on real Postgres: AC-0304-1, AC-0311-1.
- Property: AC-0313-1.
- Crash-and-resume: AC-0314-1.
- Contract (FF-01 fixture): AC-0316-1, AC-0316-2.

## 9. Open items and risks

OQ-0301: How are a factory enabled on a project, and its grants of tiers, egress and secrets, approved in M1? · Default: by the operator's authenticated configuration command (SPEC-10), recorded as a configuration version whose provenance has `author_kind: person`; no agent-facing or policy path writes project configuration (REQ-0311); the `scope` decision the Factories tab names for both arrives with SPEC-15, which converts such configuration changes into that decision · Resolved by SPEC-15.
OQ-0303: When may a project override a capability's extra skills (Concepts, "Where capabilities come from")? · Default: not in M1, where no capability has skills; the override arrives with skills in SPEC-17 · Resolved by SPEC-17.
OQ-0302: Does every factory need its own project-configuration schema? · Default: optional; a factory without one accepts no section · Resolved by TKT-0303.

Risks mitigated: factories weakening invariants (load-time namespace and make-and-prove rules); configuration drift between runs (hashes recorded per run); lost or duplicated events (outbox in the same transaction, idempotent dispatch).
Risk added: a load-time make-and-prove check over all loaded factories can refuse a factory because of another factory's capability. Mitigation: the error names both capabilities; with two factories in the MVP this is unlikely, and SPEC-17's matching revisits it per project.

## 10. Rollout

The first migration creates schema `platform`. SDK 0.1.0 is the first version; factories declare `sdk = ">=0.1.0,<0.2.0"`. `grindstone.toml` gains its first sections; SPEC-05 ships the instance file for the Compose deployment. No stored data exists before M1.
