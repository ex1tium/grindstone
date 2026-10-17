# SPEC-03 architecture review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). The playbook requires an independent architecture review for a specification that touches the SDK. SPEC-03 introduces `grindstone.sdk` 0.1.0; SPEC-06 and SPEC-08 define its port contracts. The review therefore covers:
- SPEC-03's registries, loader, configuration, events and SDK;
- the ports and contexts of SPEC-06 (`WorkspaceProvider`, `CollectOutcome`) and SPEC-08 (`SubjectResolver`, `CheckMethod`, `DeliveryAdapter`);
- SPEC-09, as the SDK's first user.

It was checked against the module map (`scripts/ff/module_map.py`, `.importlinter`), the Components tab ("Kernel SDK", "Module map"), ADR-07, ADR-21, ADR-26 and ADR-40, I-15 and I-18, and the kernel-stability success measure.

**Verdict: changes required.** Three findings block approval (A1, A2, A3). The shape of the kernel–factory seam is right, and the structure is sound:
- kinds as validated data;
- names only in a factory's namespace;
- make and prove checked at load and again at plan time;
- adapters behind ports with kernel-held idempotency;
- secrets only through grants.

The blocking findings concern what the SDK can actually be built as, and what factories will have to implement for years. The kernel-stability measure allows no breaking SDK change after M2, so 0.1.0 is the cheapest moment to get them right.

## Blocking

**A1. The SDK's read services and contexts cannot be built within FF-01 as written.** The module map lets `grindstone.sdk` import only `contracts` and `platform`. The SDK table in SPEC-03 offers:
- `items.read(ctx, ref)`, which needs `intent`;
- `blobs.open(ctx, hash)`, which needs `store`, forbidden to the SDK;
- `storage.dir(ctx)` and `secrets.read(ctx, name)`, which `platform` can serve.

Every port also takes a `ctx` that no specification defines; SPEC-03 defers the contexts to SPEC-06. Two questions are therefore open. How does a factory reach `intent` through a package that may not import it? And what stops one factory from building a `ctx` that claims another factory's secrets?
*Change:* define in SPEC-03, once, the SDK context as a protocol in `grindstone.sdk`, implemented only by kernel code and handed to adapters by the calling module (`work`, `evidence` or `delivery`). It carries the project, the factory identity, the run or check where relevant, and bound service handles (items by pin, blobs by hash, storage directory, secrets). The handles are created at the composition root from `intent`, `store` and `platform`. The SDK then imports nothing new, a factory never constructs a context, and the secret check reads the factory identity the kernel bound, not one the caller supplied. Contexts specific to one port (the workspace provider's run, the resolver's destination) extend the base protocol in the specification that owns that port.

**A2. The delivery port is wider than ADR-26, which needs a record.** ADR-26 fixes the port as `prepare`, `deliver` and `observe`. SPEC-08's `DeliveryAdapter` has six operations: `observe_mode`, `prepare`, `deliver`, `publish_status`, `merge` and `observe`. SPEC-03 publishes them in SDK 0.1.0. The reasons are good: DEC-0804 keeps the gate re-check before merging and the idempotency keys in kernel code, and ADR-40 amended I-08 so that the enforcement mode and outside merges are kernel facts. But "status" and "merge" are git-host words in a kernel port. Every later adapter must implement them (an RE report export has neither), and the change contradicts a record's text. Playbook rule 6 applies.
*Change:* propose a record amending ADR-26. It should set out:
- the port's operations;
- that `observe_mode` reports whether the remote enforces the gate (ADR-40);
- that `publish_status` and `merge` are optional, with no-op defaults and a declared capability flag, for remotes with no gate or no acceptance step;
- kernel-neutral names in the contract, for example `publish_gate_state` and `accept`, with the GitHub meaning documented in SPEC-09.

The operator accepts it before SPEC-08's TKT-0804.

**A3. Cross-factory load rules depend on load order.** The loader validates and registers factories one at a time "in name order". REQ-0307 (make and prove) and REQ-0308 ("a need offered by some loaded capability") are checked "over every loaded factory", which at that moment means only the factories already loaded. Two failure modes follow:
- a later factory can add a capability that would have made an earlier template invalid;
- a factory refused later can remove the only offer of a need an earlier template relies on.

The result then depends on the factories' names.
*Change:* load in two phases. Phase 1 validates each manifest alone: schema, namespace, SDK range, kinds, capability files. Phase 2 runs the cross-factory rules over the union of everything phase 1 accepted, refuses the offending factories, and repeats until nothing more is refused. Only then is everything registered and frozen. Add an acceptance criterion with two fixture factories whose result must not depend on their names.

## Minor

**A4. The SDK's contents are spread across three specifications.** The port contracts are SPEC-06's and SPEC-08's, so are `CollectOutcome`, `JobPayload`, `ModeObservation`, `VerificationState`, `Observation` and the kernel's `ReviewVerdict`, while SPEC-03 owns the package. SPEC-09 already depends on all of them. *Change:* SPEC-03 lists every name SDK 0.1.0 exports, in one table, with its owning specification. Each owner's contract lives in `grindstone.contracts`, so the SDK only re-exports. `grindstone.sdk.__version__` is `0.1.0`. The ownership table is amended accordingly (summary, X3).

**A5. `storage.dir(ctx)` is a new kernel service the foundation's SDK table does not list.** It gives factory code a filesystem directory on `repos`. The foundation describes `repos` as rebuildable from GitHub and outside backups, and says nothing on disk is ever the only copy of a record. *Change:* add a DEC in SPEC-03 that states the service's reason and its contract:
- the directory is per factory and project;
- it is disposable: a factory must be able to rebuild it, and nothing in it is a record;
- it is excluded from backups;
- it is removed when the project is deleted.

Name it neutrally (it is not git-specific). This needs no record, because the SDK table gives areas, not an exhaustive list.

**A6. Event consumers run as independent workflows, so delivery order is not guaranteed.** REQ-0314 promises exactly once, not in order: two events for one consumer can start workflows that run concurrently. The M1 consumers read current state, so this is safe today. *Change:* state the rule that consumers must be order-independent and read current state, or give each consumer an ordered queue of concurrency 1, and test one consumer under reordering.

**A7. Factory event types and the generated union.** REQ-0301 registers event types from factories, but the union is "assembled in `grindstone.contracts.events`" and generated for TypeScript, which only kernel models can reach at build time. *Change:* M1 factories register no event types (SPEC-09 has none), and SPEC-03 says so. Factory events arrive later as an envelope with a factory-owned payload schema.

**A8. Task modes against offer modes.** Tasks have modes `work`, `consult` and `check`; offers serve `delegate`, `consult` and `check`. SPEC-06 states the mapping (`work` matches `delegate`), and SPEC-03's make-and-prove rule relies on the same mapping without stating it. *Change:* define the mapping once, in SPEC-03's `CapabilityDecl` contract, and cite it from SPEC-06.

**A9. Registering a need against offering one.** The rule "every name starts with `<namespace>.`" is listed for needs. The foundation, though, has factories offer `core` needs (`core.review.impact`, `core.advise`) and other factories' needs (S6: RE asks for `sdlc.implement`, which SDLC offers). *Change:* say that a factory registers needs only in its namespace, and may offer its own or `core` needs. Whether a factory may offer another factory's need is a cross-factory question: either refuse it in M1 (the reviewer's recommendation) or bring it to the operator.

**A10. The loader imports factory code before validation.** `importlib.resources.files(module)` imports the factory package, so its `__init__.py` runs before the manifest is validated. DEC-0301's reason against Python kinds ("a factory's import could run before validation") applies to the loader itself. Factories are trusted (B5), so this is not a vulnerability. *Change:* read `manifest.yaml` through `importlib.metadata` distribution files, which import nothing, and import the package only in step 4; or require, with a loader test, that a factory's package `__init__` defines nothing.

**A11. Capability overrides drop "extra skills".** The Concepts tab allows a project to override model and effort, limits, extra skills from the factory's library and extra prompt text. SPEC-03 allows all but extra skills while citing that passage. *Change:* state the omission as an M1 deferral (no M1 capability has skills) and name the specification that adds it (SPEC-17 or SPEC-19).

## What holds

- Kinds as data only (DEC-0301) is the right default for 0.1.0. Adding Python-declared kinds later is an additive, minor SDK change.
- All-or-nothing registration per factory, a frozen registry after start, and history in `platform.factories` but not as a source (DEC-0304) keep one truth.
- Make and prove at load (REQ-0307), repeated against the actual maker and its delegators at plan time (SPEC-08, REQ-0801), covers I-15 at both ends. The load rule over-approximates by counting `consult` offers as makers, which is safe.
- Secrets reach factory code only by declared name and project grant, and never enter logs, events or the database.
- The transactional outbox with gapless per-project sequence numbers, under a row lock in the caller's unit of work, gives the SSE stream its resume guarantee. Under SERIALIZABLE isolation, concurrent emitters retry, which SPEC-02's unit of work already does.
- The event dispatcher starts consumers as workflows registered at the composition root, so lower modules never import higher ones.

## Next

The author of SPEC-03 (with SPEC-06 and SPEC-08 for A1, A2 and A4) makes the changes. The operator decides the delivery-port record (A2). This review is then re-checked for A1 to A3 only.
