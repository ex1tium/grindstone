# M0 status and handover

Updated 17 October 2026. The living handover between sessions: update it when a step finishes.

## Done
- Foundation v4.4: Q-1 to Q-11 answered; ADR-37 limits instead of budgets, ADR-38 consults stay open under a ceiling, ADR-39 skills materialized per session, ADR-40 delivery modes for remotes that do not enforce rulesets, ADR-41 Claude Code is the only agent for now.
- Scaffold: uv + pnpm monorepo, twelve kernel modules plus `grindstone.sdk`, factories `sdlc` and `notes`, standard-library runner, agent host, generated TypeScript contracts.
- M0-01: four services healthy under `compose.yaml`; `make smoke` verifies health, mounts and network isolation.
- M0-02: CI workflow with FF-01, FF-02, FF-04, FF-13 and failing fixtures; Dependabot.
- M0-03 (partly): versions recorded (`docs/m0/versions.md`); spike plans in `docs/spikes/`.
- M0-04 (partly): `ex1tium/grindstone-testbed` is public with the fixture project on `main`; the operator created the GitHub App (installed on the testbed only), imported the testbed ruleset, and set the cloud environment variables `GRINDSTONE_CLAUDE_OAUTH_TOKEN`, `GRINDSTONE_GITHUB_APP_ID`, `GRINDSTONE_GITHUB_APP_INSTALLATION_ID`, `GRINDSTONE_GITHUB_APP_PRIVATE_KEY_B64`.
- SPEC-01 drafted (`docs/specs/`), with one proposed decision record (hashes omit defaulted fields); awaiting independent review.

## Next, in order
1. **Verify the environment** (no values printed): the four variables exist; mint an App installation token (JWT from the key, then the installation token); read `ex1tium/grindstone-testbed`; read its active rules on `main` and confirm `grindstone/verification` is required. If the check's source is not yet restricted to the App, have the App post a first status on a commit so the operator can select it.
2. **SPK-4 GitHub mechanics** (`docs/spikes/SPK-4-github-mechanics.md`): needs only the App. Spike code goes under `spikes/spk-4/` on a branch and is not merged; the report is appended to the plan.
3. **SPK-2 DBOS in FastAPI** and **SPK-1 host and Claude** (SPK-1 uses `GRINDSTONE_CLAUDE_OAUTH_TOKEN`).
4. **SPK-5 cooperation**, after SPK-1.
5. Remaining M0-04: runner toolchain image and the benchmark project generator; wire the testbed into CI.
6. Independent review of SPEC-01; then SPEC-02 to SPEC-10 from the spike results.

## Open with the operator
- Both repositories are public (decided 17 October 2026), so Actions minutes are free and the `main` ruleset on `ex1tium/grindstone` can be enforced: import `.github/rulesets/grindstone-main.json` if not done. With both public, ADR-40's unenforced mode is still built and tested (SPK-4 flips the testbed private for that experiment), because other operators' private repositories need it.
- After SPK-4: set the testbed check's source to the App if GitHub only offered it after a first status.
- Where the stable self-hosting instance runs: decided at the M1 review.
