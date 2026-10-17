# SPEC-07 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist, the foundation v4.5, SPK-1 and SPK-5. Cross-cutting findings are in `M1-specifications-review-1.md`.

**Verdict: approve after minor changes.** The surface is as narrow as ADR-16 asks:
- per-turn tokens checked against live state on every request;
- reads limited to pins;
- `propose` that never writes intent;
- a fixed tool list per mode (ADR-43);
- structured errors as results, not protocol failures;
- keepalives at the interval SPK-5 measured.

## Minor

**F1. Token validity needs SPEC-06's turn state.** Revocation "by state" checks that the run is `active` at the token's turn. A suspended run is still `active` at that turn (SPEC-06 review, F2). *Change:* verify that the token's turn is open (not ended or suspended), using the run and turn states SPEC-06 adds. Extend AC-0702-1 with "a token whose turn suspended is refused".

**F2. Paths in `report.files`.** They are untrusted arguments, and SPEC-06 later reads them. *Change:* the contract refuses absolute paths, `..` segments, NUL bytes and paths over a length bound, so no later reader has to.

**F3. `request_permission` suspends.** The Components tab lists only `delegate` and `ask(need="operator")` as suspending tools (summary, X7). DEC-0702's reasoning, that a lane must not be held for a person, covers `request_permission` too. *Change:* say so in a DEC, so the foundation alignment has a source.

**F4. Unpinned IDs reveal existence through `propose`.** A proposal referencing an unpinned ID gets `reference_unresolved` or not, so it can probe which IDs exist outside the task's pins. M1 has one project and one operator, so this is acceptable. *Change:* record it as an accepted risk, or limit references in proposals to pinned items plus items created in the same draft, the reviewer's preference.

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement | pass |
| 4 | Exit criteria mapped | pass (M1-03, refusal clause) |
| 5 | Citations, no contradiction | pass, F3 aside |
| 6 | Dependencies | pass (SPEC-06's hook for minting is an inversion; X6) |
| 7 | Ownership | pass (`surface.mcp` here, REST in SPEC-10) |
| 8 | Idempotency | pass (no external effects; repeats handled by services) |
| 9 | Typed boundaries | pass (tool schemas generated, drift and compatibility checked) |
| 10 | Migration | pass (tool set `grindstone/1`) |
| 11 | Trust boundaries | pass, F1 and F2 aside |
| 12 | Derivations computed | pass (open calls in memory) |
| 13 | Dependencies pinned from a primary source | pass: `fastmcp` 4.1.0 (2026-10-08) and `mcp` 2.3.0 (2026-10-02) are the latest on PyPI |
| 14 | Cross-module choices as records | pass |
| 15 | Typed errors | pass |
| 16 | Test plan | pass (in-memory tool tests) |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory name | pass |
| 20 | Factory 5F | n/a |
| 21 | Maker and prover | pass (no tool writes evidence) |
| 22 | Cooperation | pass (only `ask(operator)` in M1; the rest is SPEC-17's) |
| 23 | Irreversible actions | n/a |
| 24 | Fitness functions | pass (FF-02 and FF-03 extended) |
