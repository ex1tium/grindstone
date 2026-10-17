# SPEC-10 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist, the foundation v4.5 and the operator's decisions for M1 (local password, Argon2, session cookie, loopback). Cross-cutting findings are in `M1-specifications-review-1.md`. The TypeScript 6 question is judged in the summary (question 1): it needs a record.

**Verdict: approve after minor changes.** It is a clean, small surface:
- one public API with no private endpoints;
- server-side sessions with HMAC-stored identifiers;
- CSRF by a custom header with no CORS;
- idempotency keys passed down as the services' client keys, so a crash between effect and response still returns the original result;
- cards rendered from kind and payload with no `{@html}`;
- end-to-end tests on the operator's real path.

## Minor

**F1. Ownership of the Argon2 parameters (summary, X6).** SPEC-05 owns them, and SPEC-10 cites them.

**F2. The HTTP status for limit-class errors.** Mapping the whole limit class to 429 suits rate limits, but `storage_limit` and `not_available` are not "too many requests", and clients retry 429s. *Change:* 429 only for the login rate limit; 409 for the other limit codes, with `retryable` from the envelope.

**F3. How the channel is decided.** REQ-1004 records `ui` "from the web shell, otherwise `api`". *Change:* say how: the generated client sends `X-Grindstone-Client: web`. The value is the operator's own claim, which is acceptable because every request is the operator's.

**F4. The `operators` table.** The Components tab's data model lists `operators` in schema `surface`, and SPEC-10 drops it while there is one operator. That is reasonable. Say that SPEC-22 or SPEC-26 adds it if a second credential type needs one. No foundation change: the table's names are seeds.

**F5. The TypeScript 6 pin.** Keep DEC-1003 as written, and cite the record the operator accepts for it (summary, proposed record 2).

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement | pass |
| 4 | Exit criteria mapped | pass (M1-01 and M1-08, the operator's side) |
| 5 | Citations, no contradiction | minor: TypeScript 6 against ADR-01's "latest stable" (F5) |
| 6 | Dependencies | minor: the cycle with SPEC-05 (F1) |
| 7 | Ownership | pass (REST and events here, MCP in SPEC-07) |
| 8 | Idempotency and crash tests | pass (AC-1007-1) |
| 9 | Typed boundaries | pass (OpenAPI generated; drift and compatibility checked) |
| 10 | Migration | pass |
| 11 | Trust boundaries | pass (B4; no HTML rendering of payloads) |
| 12 | Derivations computed | pass |
| 13 | Dependencies pinned from a primary source | pass: `argon2-cffi` 25.1.0, `argon2-cffi-bindings` 26.1.0, and every npm pin match the registries on 17 October 2026; the SvelteKit 3.1.0 and svelte-check 4.7.7 peer ranges stop at TypeScript 6, as DEC-1003 says |
| 14 | Cross-module choices as records | minor: F5 |
| 15 | Typed errors | pass, F2 aside |
| 16 | Test plan | pass (Playwright on the built stack with the scripted preset) |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory name | pass |
| 20 | Factory 5F | n/a |
| 21 | Maker and prover | n/a |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | n/a (the `delivery` card is where they would be asked) |
| 24 | Fitness functions | pass (FF-02, FF-03 extended); FF-07 itself is X2 |
