# M0 status and handover

Updated 17 October 2026. The living handover between sessions: update it when a step finishes.

## Done
- Foundation v4.4: Q-1 to Q-11 answered; ADR-37 limits instead of budgets, ADR-38 consults stay open under a ceiling, ADR-39 skills materialized per session, ADR-40 delivery modes for remotes that do not enforce rulesets, ADR-41 Claude Code is the only agent for now.
- Scaffold: uv + pnpm monorepo, twelve kernel modules plus `grindstone.sdk`, factories `sdlc` and `notes`, standard-library runner, agent host, generated TypeScript contracts.
- M0-01: four services healthy under `compose.yaml`; `make smoke` verifies health, mounts and network isolation.
- M0-02: CI workflow with FF-01, FF-02, FF-04, FF-13 and failing fixtures; Dependabot.
- M0-03 (partly): versions recorded (`docs/m0/versions.md`); spike plans in `docs/spikes/`.
- M0-04: `ex1tium/grindstone-testbed` is public with the fixture project on `main`; the operator created the GitHub App (installed on the testbed only), imported the testbed ruleset, and set the cloud environment variables `GRINDSTONE_CLAUDE_OAUTH_TOKEN`, `GRINDSTONE_GITHUB_APP_ID`, `GRINDSTONE_GITHUB_APP_INSTALLATION_ID`, `GRINDSTONE_GITHUB_APP_PRIVATE_KEY_B64`. The runner image is the fixture project's toolchain: `make fixture` (CI job `fixture`) runs the testbed's tagged tests in it as `gs-runner`, with no network, no capabilities, a read-only root and subject, and no credentials, and maps every `@verifies` criterion to a passing test. `make benchmark` generates the benchmark project (`scripts/benchmark.py`): 20,000 items in the fixture's Markdown style, no dangling references, reproducible (golden digest in `tests/test_benchmark_project.py`), with an impact probe (`P-08` reaches 500 items) for FF-14 at M2.
- Environment verified (17 October 2026): the four variables are set and the App key signs a JWT; the testbed's `main` rules require `grindstone/verification` from the App (`integration_id` matches the App ID), strict.
- SPK-4 (17 October 2026, run by the operator as the App; report in `docs/spikes/SPK-4-github-mechanics.md`): all eleven experiments pass. Only the App's status satisfies the check (forgeries by an admin and by a workflow's own token are refused); a new head or a behind base needs a fresh status; Q-7 confirmed; delivery mode detectable through `rules/branches` (`403` when private on the free plan); merging with the verified SHA refuses a concurrent push; bypasses visible; 6 calls a poll, ETag 304s free, 5,000 calls an hour; pushes without hooks work.
- SPK-2 (17 October 2026; report in `docs/spikes/SPK-2-dbos-fastapi.md`): all nine experiments pass. No duplicate effect after SIGKILL during steps, `recv`, `sleep`, child workflows and scheduled runs; idempotent messages; the writing lane serializes; a writing parent must delegate rather than wait on a writing child. For SPEC-02: set `application_version` explicitly and drain before an incompatible workflow change (DBOS recovers only its own version; the default is a hash of the workflow source); use DBOS's `_async` calls in the FastAPI lifespan.
- SPK-1 (17 October 2026; report in `docs/spikes/SPK-1-host-claude-vscode.md`): experiments 1–9 pass; the VS Code half of experiment 6 is deferred. No package patch: a backend wrapper gives each session its kernel MCP server and token, environment and Unix user; the vendored plugin is a launcher (`settingSources: []`, credential self-test). AHP 1.0.0; FastMCP 4.1.0 on MCP SDK 2.3.0 verifies tokens per request. For SPEC-05: grants are enforced only with a `users` directory; agents outlive a killed host unless it is PID 1 or sets a parent-death signal; the host needs exactly `CAP_SETUID` and `CAP_SETGID`; run directories `<agent>:gs-workspaces` 2750. Proposed amendment to ADR-15 (no patch) in the report.
- SPK-5 (17 October 2026; report in `docs/spikes/SPK-5-cooperation.md`): Claude Code holds an `ask` open for 45 minutes (longest run, shortened from 120 with the operator) with progress every 30 s; without keepalives it aborts at the 5-minute idle window; defaults already allow about 28 h. Single-flight join, cache, ceiling and resume, and liveness on the kernel's open-call count all work. **Claude Code never sees a tool added mid-session** (`tools/list_changed`): proposed ADR-39 change, skill tools listed from start and refused until loaded. Uncached small consult: 4 s, $0.03; cached: free.
- Foundation v4.5 (accepted by the operator, 17 October 2026): ADR-44, semantic hashes omit fields at their default (from SPEC-01); ADR-42, the agent host uses its packages unmodified behind a backend wrapper and a vendored launcher (amends ADR-15, resolves Q-1); ADR-43, a skill's tools are listed from session start and refused until loaded (amends ADR-39). SPK-2's version-and-drain finding needs no record (the foundation already names explicit application versions and an upgrade path for in-flight workflows); it goes into SPEC-02 and SPEC-27.
- SPEC-01 reviewed (`docs/specs/reviews/SPEC-01-review-1.md`), then revised (revision 1) by the same session at the operator's instruction: all nine findings answered; the item ID grammar now admits every foundation form, unordered collections are refused in semantic content, ADR-44 cited.

- SPEC-02 to SPEC-10 drafted (17 October 2026), all by one session, which therefore reviews none of them. Each is in `docs/specs/`, status draft, with `make check` passing:
  - SPEC-02 store, runtime, lanes and blobs;
  - SPEC-03 platform, which introduces SDK 0.1.0;
  - SPEC-04 items, thin ChangeSet and decisions;
  - SPEC-05 deployment, users and secrets;
  - SPEC-06 agent station and task runs;
  - SPEC-07 kernel MCP surface;
  - SPEC-08 check station, evidence and delivery port;
  - SPEC-09 SDLC skeleton factory;
  - SPEC-10 operator surface.

  Every M1 exit criterion maps to acceptance criteria in the specifications the spec map assigns, and every requirement has at least one acceptance criterion and one ticket. New package versions are recorded in `docs/m0/versions.md` under "Resolved for the M1 specifications".

## Next, in order
1. **Review, in a session that wrote none of them.** The playbook allows one pass over all ten.
   - **SPEC-01:** confirm that revision 1 closes every finding of review 1. That session both reviewed and revised it, so this check stands in for an independent one.
   - **SPEC-02 to SPEC-10:** run the validation checklist. SPEC-03 also needs the independent architecture review the playbook requires for a specification that touches the SDK. SPEC-06 and SPEC-08 define SDK ports too.
   - **Points the author asks the reviewer to judge:**
     - Playbook rule 6 says a new dependency is proposed as a decision record. SPEC-01's precedent records dependencies as specification decisions with primary-source pins (checklist item 13). Does any new one need a record: SQLAlchemy as a direct dependency, PyYAML, argon2-cffi, PyJWT with cryptography, Playwright, TypeScript 6 in `web/`?
     - M1 thinnings of foundation text that is not an ADR:
       - in M1 a factory is enabled by the operator's configuration command, not a `scope` decision (SPEC-03, OQ-0301);
       - approval verdicts are `unaffected` only (SPEC-04, DEC-0402);
       - a task is done once its delivery is delivered, before merge (SPEC-08, DEC-0805).
     - The spec-level dependency between SPEC-06 and SPEC-08 is acyclic only per module: `stations` ← `evidence` ← `work`.
     - SPEC-05's root entrypoints, which copy 0600 secrets into each service user's tmpfs (DEC-0501).
2. **Operator approval** of the ten, and of any records the review proposes. Then the tickets in each specification's section 7 are ready to break down.
3. **M0 milestone review:** the exit criteria (the `fixture` CI job must pass on the pull request), risks and open questions.

## Decided by the operator (17 October 2026), for SPEC-02 to SPEC-10
- **Where M1's real delivery runs:** decided at the M1 review. The specifications carry it as an open item whose default is the operator's machine (Docker Desktop with WSL2 runs the four Linux containers; the App key stays there). A cloud session can never act as the App (SPK-4).
- **Operator login:** a local password. One operator account, the password hashed with Argon2, a session cookie, and the UI and API bound to loopback by default (SPEC-10 owns it; SPEC-05 provisions the secret).
- **Models for M1's agents:** set later. The specifications keep the model as capability configuration with a stated default (implementer and test reviewer on different Claude models, ADR-41); the operator chooses before M1-01's live run.
- **SPK-1's VS Code half:** deferred to M4, with SPEC-22, on the operator's machine (M4-05 needs it; M1 does not).

## Open with the operator
- Before M1-01's live run: choose the models for the `primary` and `secondary` slots in `deploy/grindstone.toml` (SPEC-06, SPEC-09; different by default).
- Before M1-08: install the GitHub App on `ex1tium/grindstone` and require `grindstone/verification` from it in that repository's ruleset (SPEC-09, OQ-0902).
- At the M1 review: whether agent egress stays open at T1 (SPEC-05, OQ-0502), and where M1's real delivery runs (default: the operator's machine; SPEC-05, OQ-0501 checks secrets there).
- Re-import `.github/rulesets/grindstone-main.json` on `ex1tium/grindstone`: it now also requires the `fixture` CI job (M0-04). The ruleset is otherwise active (checked 17 October 2026).
- Open a pull request for this branch when ready: the `fixture` CI job runs only on pull requests and `main`.
- Anything that must act as the App runs on the operator's machine (`docs/spikes/SPK-4-local-run.md`).
- With both repositories public, ADR-40's unenforced mode is still built and tested (SPK-4 flips the testbed private for that experiment), because other operators' private repositories need it.
