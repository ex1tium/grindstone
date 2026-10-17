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
- SPK-4 (17 October 2026, run by the operator as the App; report in `docs/spikes/SPK-4-github-mechanics.md`): all eleven experiments pass. Only the App's status satisfies the check (forgeries by an admin and by a workflow's own token are refused); a new head or a behind base needs a fresh status; Q-7 confirmed; delivery mode detectable through `rules/branches` (`403` when private on the free plan); merging with the verified SHA refuses a concurrent push; bypasses visible; 6 calls a poll, ETag 304s free, 5,000 calls an hour; pushes without hooks work.
- SPK-2 (17 October 2026; report in `docs/spikes/SPK-2-dbos-fastapi.md`): all nine experiments pass. No duplicate effect after SIGKILL during steps, `recv`, `sleep`, child workflows and scheduled runs; idempotent messages; the writing lane serializes; a writing parent must delegate rather than wait on a writing child. For SPEC-02: set `application_version` explicitly and drain before an incompatible workflow change (DBOS recovers only its own version; the default is a hash of the workflow source); use DBOS's `_async` calls in the FastAPI lifespan.
- SPK-1 (17 October 2026; report in `docs/spikes/SPK-1-host-claude-vscode.md`): experiments 1–9 pass; the VS Code half of experiment 6 is deferred. No package patch: a backend wrapper gives each session its kernel MCP server and token, environment and Unix user; the vendored plugin is a launcher (`settingSources: []`, credential self-test). AHP 1.0.0; FastMCP 4.1.0 on MCP SDK 2.3.0 verifies tokens per request. For SPEC-05: grants are enforced only with a `users` directory; agents outlive a killed host unless it is PID 1 or sets a parent-death signal; the host needs exactly `CAP_SETUID` and `CAP_SETGID`; run directories `<agent>:gs-workspaces` 2750. Proposed amendment to ADR-15 (no patch) in the report.
- SPEC-01 drafted (`docs/specs/`), with one proposed decision record (hashes omit defaulted fields); awaiting independent review.

## Next, in order
1. **SPK-5 cooperation** (`docs/spikes/SPK-5-cooperation.md`).
2. Remaining M0-04: runner toolchain image and the benchmark project generator; wire the testbed into CI.
3. Independent review of SPEC-01; then SPEC-02 to SPEC-10 from the spike results.

## Open with the operator
- SPK-1's VS Code half (experiment 6): attach VS Code to a host as a remote agent host, on a machine VS Code can reach. Small; can wait for the first session on such a machine.
- Anything that must act as the App runs on the operator's machine (decided 17 October 2026; `docs/spikes/SPK-4-local-run.md`): a cloud session's GitHub proxy never lets it act as the App. The same holds for M1 delivery.
- Both repositories are public (decided 17 October 2026), so Actions minutes are free and the `main` ruleset on `ex1tium/grindstone` can be enforced: import `.github/rulesets/grindstone-main.json` if not done. With both public, ADR-40's unenforced mode is still built and tested (SPK-4 flips the testbed private for that experiment), because other operators' private repositories need it.
- Where the stable self-hosting instance runs: decided at the M1 review.
