# SPEC-03 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist and the foundation v4.5. The independent architecture review the playbook requires for an SDK specification is `SPEC-03-architecture-review-1.md`; its blocking findings A1 to A3 are this specification's blocking findings too. Cross-cutting findings are in `M1-specifications-review-1.md`.

**Verdict: changes required**, for A1 to A3. The checklist findings below are minor.

## Minor

**F1. OQ-0301 should name grants.** The Factories tab puts the project's grants of tiers, egress and secrets on the same `scope` decision as enabling. In M1 both are configuration, so OQ-0301 should cover both. The judgment on the thinning itself is in the summary (question 2a).

**F2. The error code for an ungranted secret.** `permission_required` is an authority-class code, which "raises or refreshes a decision". A factory adapter reading a secret its project did not grant is a configuration or programming error, and no decision follows. *Change:* register a validation-class code (for example `secret_not_granted`), or say explicitly that no decision is raised.

**F3. Extra skills in capability overrides** (architecture review, A11).

**F4. The model slot in overrides.** `CapabilityDecl.agent.model` is "a named model slot", while `ProjectConfig` overrides `model`. *Change:* say whether an override names a slot or a model. The reviewer recommends a slot, so models stay instance configuration (SPEC-06).

**F5. M1-07's load clause is delivered.** AC-0307-1 and AC-0307-2 cover it. No change; noted for traceability.

**F6. Test plan.** All 17 criteria are listed. AC-0304-1 should also check that the refused factory's projects are reported paused by `GET /api/v1/projects/{p}` (SPEC-10), since pause is derived and shown nowhere else.

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement | pass |
| 4 | Exit criteria mapped | pass (M1-07, load clause) |
| 5 | Citations, no contradiction | **fail**: A2 (ADR-26's port operations, published in SDK 0.1.0) |
| 6 | Dependencies | pass (SPEC-01, SPEC-02) |
| 7 | Ownership | pass; SDK contributors (X3, A4) |
| 8 | Idempotency | pass (dispatcher by workflow ID; AC-0314-1) |
| 9 | Typed boundaries | pass |
| 10 | Migration | pass |
| 11 | Trust boundaries | **fail**: A1 (a factory-constructed context could claim another factory's secrets) |
| 12 | Derivations computed | pass (project pause derived) |
| 13 | Dependencies pinned from a primary source | pass: `pyyaml` 6.0.3 (2025-09-25) and `packaging` 26.3 (2026-08-04) are the latest on PyPI |
| 14 | Cross-module choices as records | **fail**: A2 |
| 15 | Typed errors | pass, F2 aside |
| 16 | Test plan | pass; A3 needs an order-independence criterion |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory name | pass (fixtures in the `notes` style) |
| 20 | Factory 5F | n/a |
| 21 | Maker and prover | pass (REQ-0307) |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | n/a |
| 24 | Fitness functions | pass (FF-01 extended); FF-07 itself is X2 |
