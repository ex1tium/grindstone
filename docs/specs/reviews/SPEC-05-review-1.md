# SPEC-05 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist, the foundation v4.5, SPK-1's report and the M0 `compose.yaml`. Cross-cutting findings are in `M1-specifications-review-1.md`. The judgment on DEC-0501, the author's question 4, is in the summary: sound, with the conditions below.

**Verdict: approve after minor changes.** This is the specification that turns I-09 into tests on real images, and it does so thoroughly:
- a secret table with readers;
- capability sets checked in `/proc`;
- one agent user per lane slot;
- a launcher floor that per-session options cannot lower;
- an init plus parent-death signals;
- the hostile repository in a live run.

## Minor

**F1. The `postgres` row contradicts the blanket rule.** "Every container keeps `no-new-privileges`, a read-only root, `cap_drop: ALL`", but `postgres` keeps "image default". The M0 `compose.yaml` gives `postgres` neither `cap_drop` nor a read-only root. Its entrypoint needs its default capabilities to read the operator-owned 0600 secret and to `chown` its data directory. *Change:* state `postgres` as the one exception (image default capabilities, writable root and data volume, `no-new-privileges`), and make FF-05's capability rule and AC-0502-1 say the same.

**F2. Reading the staging archive.** The layout says the archive is "extracted from the staging archive as the agent user", but agent users cannot read `staging/`, by design (2750 `grindstone:gs-workspaces`, archive 0640). *Change:* say that the host, a member of `gs-workspaces`, reads the archive and streams it to an extractor running as the agent user, and test that the agent user cannot open the archive itself (AC-0506-1).

**F3. Runner egress.** The networks list says `runner-egress` carries the runner "to package registries", but Compose cannot restrict a network to registries, so it is open egress. The risks table already bakes dependencies into the toolchain image, and M0-04's fixture runs with no network. *Change:* either give the runner no network in M1 (the reviewer's recommendation; drop `runner-egress`) or say plainly that its egress is open, as OQ-0502 does for agents.

**F4. Loopback inside `agent-host` is shared with agents.** The AHP listener on loopback is reachable from agent processes in the same network namespace. Its protection is the people directory and tokens, not the address. *Change:* say so in the listener section, and add to AC-0511-1 a connection from an agent user to the AHP listener without a token, which must be refused.

**F5. Ownership of the Argon2 parameters (summary, X6).** SPEC-05 owns the parameters it writes. SPEC-10 cites them.

**F6. Hashing inside `make secrets`.** `make secrets` "stores its Argon2id hash" from a POSIX shell script on the host. *Change:* name the tool, for example `uv run --frozen python -m grindstone.surface.hashpw`, which uses SPEC-10's pinned `argon2-cffi`, and keep the password off argv.

**F7. Cite the Compose behaviour DEC-0501 relies on.** Per-secret `uid`, `gid` and `mode` are ignored for file secrets outside Swarm. *Change:* cite the Compose specification or Docker documentation, per playbook rule 8.

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement | pass |
| 4 | Exit criteria mapped | pass (M1-05: credentials, push, socket, settings, lints; SPEC-09 has hooks and tiers) |
| 5 | Citations, no contradiction | pass |
| 6 | Dependencies | minor: the cycle with SPEC-10 (F5, X6) |
| 7 | Ownership | pass (launcher, people directory and helper here; host core in SPEC-06) |
| 8 | Idempotency | pass (`make secrets` never overwrites; AC-0513-1) |
| 9 | Typed boundaries | pass |
| 10 | Migration | pass (M0 checkouts run `make secrets` once) |
| 11 | Trust boundaries | pass; F3 and F4 clarify what holds |
| 12 | Derivations computed | n/a |
| 13 | Dependencies | pass (none new) |
| 14 | Cross-module choices as records | pass (OQ-0502 names the record an egress proxy would need) |
| 15 | Typed errors | pass |
| 16 | Test plan | pass. The live run AC-0508-2 is justified: Claude Code's own settings loading is the point |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory name | pass; the GitHub App key appears as a deployment secret, which the deployment must name |
| 20 | Factory 5F | n/a |
| 21 | Maker and prover | n/a |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | n/a |
| 24 | Fitness functions | pass (FF-05 and FF-06 added, with fixtures) |
