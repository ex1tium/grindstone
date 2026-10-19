# M0 milestone review

Prepared 19 October 2026 from `main` at c502c87, whose CI run is <https://github.com/ex1tium/grindstone/actions/runs/39262057690>. The review follows the Roadmap's milestone-review procedure: exit criteria, success measures, risks and open questions, fitness functions, and changes to scope or order. Each section ends with what the operator confirms. When everything is confirmed, M0's checkboxes in the foundation are ticked, and from then on M0's criteria never change.

**Status: confirmed on 19 October 2026. M0 is closed.**

## 1. Exit criteria

| Criterion | Evidence | Verdict |
| --- | --- | --- |
| **M0-01** Four services healthy, each volume mounted only where ADR-01 allows, every image pinned by digest | CI job "Compose smoke test (M0-01)" runs `scripts/compose_smoke.py` on every pull request and on `main`. It checks: each container's health; that each mounts exactly its allowed volumes, with no other bind mounts beyond its secret files and no Docker socket; and that the stations cannot reach PostgreSQL. FF-04 checks image digests. | Met |
| **M0-02** CI runs lint, type checks, tests and FF-01, FF-02, FF-04, FF-13 over `docs/`; fixtures prove a floating tag, a kernel-to-factory import and a dangling ID each fail the build | CI job "Lint, types, tests, fitness functions". The fixtures are `test_floating_tag_fixture_fails_the_build`, `test_kernel_importing_a_factory_fails_the_build` and `test_dangling_id_fixture_fails_the_build`. Since #9 the Python suite also passes on Windows. | Met |
| **M0-03** SPK-1, SPK-2, SPK-4 and SPK-5 filed (SPK-3 deferred by ADR-41); Q-1 to Q-11 resolved or defaults confirmed; versions and the Claude credential-precedence list recorded from primary sources | All four reports are in `docs/spikes/`, each with status "done". SPK-1's VS Code half is deferred (section 2). Q-1 to Q-11 are each decided, confirmed or deferred by a record (Roadmap table, corrected in v4.8). Versions are in `docs/m0/versions.md` with their sources. The precedence list is in SPK-1, experiment 4 (36 sources tested). | Met, with the deferral in section 2 |
| **M0-04** Testbed with its ruleset and a GitHub App installation, the runner toolchain image, a fixture project with tagged tests, and the benchmark project, all wired into CI | `ex1tium/grindstone-testbed` requires `grindstone/verification` from the App (checked 17 October 2026; SPK-4 proved that only the App's status satisfies it). CI job "Fixture project in the runner image (M0-04)" runs the testbed's tagged tests in the runner image with no network or credentials. `tests/test_benchmark_project.py` generates the 20,000-item project in CI against a golden digest. The `main` ruleset requires all three jobs (checked 19 October 2026). | Met |

**The operator confirms:** M0-01 to M0-04 are met.

## 2. Deferrals that need the operator's explicit acceptance

| Deferral | Recorded in | Why it does not block M1 |
| --- | --- | --- |
| SPK-1, experiment 6: VS Code attaching to a live session | SPK-1 status line; `docs/m0/status.md` ("Decided by the operator, 17 October 2026"); Q-2 (v4.8) | M1 needs no VS Code. M4-05 does, and SPEC-22 runs the experiment on the operator's machine. AHP 1.0.0 is already confirmed with a headless client. |
| SPK-3 (Codex and pi), Q-3 and Q-4 | ADR-41 | Claude Code is the only agent until the operator adds another. The scripted agent keeps the ACP abstraction honest on every commit. |

**The operator confirms:** both deferrals.

## 3. Success measures

None can be read yet. Every measure counts merged ticket pull requests, consults or decisions, and none exist before M1. Q-8 confirms the initial targets, and their baselines are recorded at M3 (M3-07).

**The operator confirms:** there is nothing to read at M0.

## 4. Risks

The spikes moved these risks:

| Risk | Movement at M0 |
| --- | --- |
| The skeleton takes longer than planned because integrations fight back | Lower. All four spikes passed with no package patch (ADR-42), and two findings became records (ADR-42, ADR-43). |
| Workflows duplicate or lose side effects across crashes | Lower. SPK-2 found no duplicate effect after SIGKILL during steps, waits, child workflows or schedules. M1-04 still has to prove it for Grindstone's own effects. |
| Long-open MCP tool calls are unreliable in some agents | Lower for Claude Code. SPK-5 held calls open for 45 minutes with keepalives. Other agents are untested (SPK-3 deferred). |
| The agent-host ecosystem is young and moves fast | Unchanged. The packages are used unmodified behind a wrapper (ADR-42), so an upgrade is a deliberate commit plus a smoke test. |
| On free plans the remote does not enforce the merge gate on private repositories | Understood. SPK-4 showed the mode is detectable and that merging with the verified SHA refuses a concurrent push. M1-02 builds both modes. |
| With one agent family, or one model making and reviewing, author and reviewer share blind spots | Higher by choice (ADR-47): reviewers may use the maker's model. Mechanical proof and the test reviewer carry the gate, and the risk is revisited at M3. |

The other risks are unchanged and are proven by later milestones, as the risk table states.

**The operator confirms:** the risk table stands, with the movements above.

## 5. Open questions

- **Foundation:** Q-1 to Q-11 are all closed for M0, as decided, confirmed, or deferred by ADR-41.
- **Carried to M1:** the specifications' open questions, each with a default and an owner. Those that need the operator, or are decided at the M1 review:
  - OQ-0501: whether secret files on the operator's WSL2 host keep their ownership. The deployment fails closed if they don't.
  - OQ-0502: whether agent egress stays open at T1.
  - OQ-0604 and OQ-0503: whether eight agent users are enough.
  - OQ-0804: whether one gate-state queue keeps up.
  - OQ-0901: which M2 ticket becomes M1-08's.
  - OQ-0902: the App on `ex1tium/grindstone` before M1-08.
- **Before M1-01's live run:** the models for the `primary` and `secondary` slots. They may be the same (ADR-47).

**The operator confirms:** these carry forward.

## 6. Fitness functions

FF-01, FF-02, FF-04 and FF-13 run in CI with failing fixtures (M0-02). M1's tickets build FF-05 to FF-10: FF-07 and FF-09 in SPEC-02, FF-08 in SPEC-04, and the deployment and workspace lints FF-05 and FF-06 for M1-05. The rest arrive with their milestones: FF-11 and FF-12 at M2, FF-14 at M2 against the benchmark project. No fitness function proved wrong or noisy in M0.

**The operator confirms:** the fitness-function plan stands.

## 7. Changes to scope or order made during M0

Every change is already a decision record:
- **ADR-37 to ADR-41**, at kickoff: limits instead of budgets; consults held open under a ceiling; skills materialized per session; delivery modes; Claude Code as the only agent for now.
- **ADR-42 to ADR-44**, from the spikes and SPEC-01: an unmodified host behind a wrapper; skill tools listed from the start; semantic hashes that omit default fields.
- **ADR-45 and ADR-46**, from the M1 specification review: the delivery port's operations; dependency currency.
- **ADR-47**, from the operator: reviewer models are configuration.

Milestone order and the M1 to M5 exit criteria are unchanged, apart from M3-06's restatement under ADR-47.

**The operator confirms:** no further change to scope or order.

## 8. Ready for M1

- The ten M1 specifications are accepted, with SPEC-06 in two parts. Their 45 tickets are the backlog, built in the specification graph's order: SPEC-01, SPEC-02, SPEC-03, then SPEC-04 and SPEC-05, SPEC-06 part 1, SPEC-07 and SPEC-08, SPEC-06 part 2, SPEC-09 and SPEC-10. The live runs M1-01, M1-02 and M1-08 come last.
- Re-check 1 gives the implementing tickets two notes: collect must not block on FIFOs, and must guard against hard links.

## Confirmation

Confirmed on 19 October 2026. Each section's evidence was re-checked at confirmation against the repository, CI and the live rulesets.

| Section | Confirmed | Checked at confirmation |
| --- | --- | --- |
| 1. Exit criteria | Yes | Every image is pinned by digest: `postgres` in `compose.yaml`, and every `FROM` and `COPY --from` in `docker/`. The smoke test probes that both stations are refused by PostgreSQL, that the runner is refused by the control plane, and that the agent host reaches it. CI runs `make lint`, `typecheck`, `test`, `ff`, `smoke` and `fixture`. The testbed's live rule requires `grindstone/verification` from integration 5358336 with strict checks; this is the App, as verified on 17 October 2026 and by SPK-4's refused forgeries. SPK-1's precedence list covers 36 sources. |
| 2. Deferrals | Yes | M4-05 needs VS Code, and the spec map gives it to SPEC-22. SPK-3, Q-3 and Q-4 are deferred by ADR-41. |
| 3. Success measures | Yes | Nothing to read before M1. |
| 4. Risks | Yes | The movements in section 4 match the spike reports and ADR-47. |
| 5. Open questions | Yes | Each carried question has a default and an owner in its specification. |
| 6. Fitness functions | Yes | Each of FF-05 to FF-10 has a ticket and an acceptance criterion: FF-05 and FF-06 in TKT-0505 (AC-0501-1, AC-0510-1); FF-07 and FF-09 in TKT-0206 (AC-0215-1, AC-0216-1); FF-08 in TKT-0405 (AC-0420-1); FF-10 in TKT-0203 (AC-0204-2). FF-11, FF-12 and FF-14 are M2's. |
| 7. Scope and order | Yes | ADR-37 to ADR-47 cover every change; the milestone order is unchanged. |
