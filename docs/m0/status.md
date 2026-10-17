# M0 status and handover

Updated 17 October 2026. The living handover between sessions: update it when a step finishes.

## Done
- Foundation v4.4: Q-1 to Q-11 answered; ADR-37 limits instead of budgets, ADR-38 consults stay open under a ceiling, ADR-39 skills materialized per session, ADR-40 delivery modes for remotes that do not enforce rulesets, ADR-41 Claude Code is the only agent for now.
- Scaffold: uv + pnpm monorepo, twelve kernel modules plus `grindstone.sdk`, factories `sdlc` and `notes`, standard-library runner, agent host, generated TypeScript contracts.
- M0-01: four services healthy under `compose.yaml`; `make smoke` verifies health, mounts and network isolation.
- M0-02: CI workflow with FF-01, FF-02, FF-04, FF-13 and failing fixtures; Dependabot.
- M0-03 (partly): versions recorded (`docs/m0/versions.md`); spike plans in `docs/spikes/`.
- M0-04 (partly): `ex1tium/grindstone-testbed` is public with the fixture project on `main`; the operator created the GitHub App (installed on the testbed only), imported the testbed ruleset, and set the cloud environment variables `GRINDSTONE_CLAUDE_OAUTH_TOKEN`, `GRINDSTONE_GITHUB_APP_ID`, `GRINDSTONE_GITHUB_APP_INSTALLATION_ID`, `GRINDSTONE_GITHUB_APP_PRIVATE_KEY_B64`.
- Environment verified (17 October 2026): the four variables are set and the App key signs a JWT; the testbed's `main` rules require `grindstone/verification` from the App (`integration_id` matches the App ID), strict.
- SPK-4 partly run (report in the plan): experiment 6 passes; experiment 7 measured (6 calls a poll, ETag 304s are free); experiment 9's public half recorded.
- SPEC-01 drafted (`docs/specs/`), with one proposed decision record (hashes omit defaulted fields); awaiting independent review.

## Next, in order
1. **SPK-4, the App experiments (1 to 5, 8 to 11)**, from a host that reaches `api.github.com` directly. A cloud session cannot: its GitHub proxy substitutes its own credentials for any token and refuses `/app/*`, commit-status writes and the Actions API (report in `docs/spikes/SPK-4-github-mechanics.md`). The operator runs `spk4/run.py` (testbed branch `claude/youthful-franklin-oq4j5j`) locally, following `docs/spikes/SPK-4-local-run.md`, and pushes `spk4/results/`; the next session reads them and completes the report.
2. **SPK-2 DBOS in FastAPI** (runs in a cloud session; can start while step 1 waits) and **SPK-1 host and Claude** (SPK-1 uses `GRINDSTONE_CLAUDE_OAUTH_TOKEN`).
3. **SPK-5 cooperation**, after SPK-1.
4. Remaining M0-04: runner toolchain image and the benchmark project generator; wire the testbed into CI.
5. Independent review of SPEC-01; then SPEC-02 to SPEC-10 from the spike results.

## Open with the operator
- SPK-4 App experiments: the operator runs them locally (decided 17 October 2026; guide in `docs/spikes/SPK-4-local-run.md`, including enabling testbed Actions and auto-merge first). The same constraint holds for M1 delivery: a cloud session can never act as the App.
- Both repositories are public (decided 17 October 2026), so Actions minutes are free and the `main` ruleset on `ex1tium/grindstone` can be enforced: import `.github/rulesets/grindstone-main.json` if not done. With both public, ADR-40's unenforced mode is still built and tested (SPK-4 flips the testbed private for that experiment), because other operators' private repositories need it.
- Where the stable self-hosting instance runs: decided at the M1 review.
