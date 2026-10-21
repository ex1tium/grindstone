# Foundation v4.10 confirmation 3

Scope: commit `9365e0f` (revision 6) on `docs/foundation-v4-10-vision`, diffed against `e07f52f`. The pass is limited to D1 to D7 of `foundation-v4-10-confirmation-2.md` and to anything revision 6 broke. At `9365e0f`, FF-13 traceability reports 0 violations and `uv run pytest -q` passes (43 tests).

**Verdict: ADR-54 can be accepted.** D1 to D7 are closed. One minor point for the R1 addendum remains (E1). It does not block acceptance, because it concerns R1-only machinery.

| Finding | State | Reason |
| --- | --- | --- |
| D1 | Closed | The new bullet "Where taint ends" covers every part of the fix. Exposure belongs to runs and their unapproved output, never to the approved ledger or repository. A person's approval clears the revisions it applies, and a `delivery` answer clears the subject. From R1, text an exposed run wrote stays external-marked. The approval card shows the external text verbatim and is never batched with trusted decisions. Unapproved subjects and workspaces propagate exposure to retries, rework rounds, the conflict-resolution task and reviewers. ADR-32's status pointer states the end rule. |
| D2 | Closed | `read_items` and `search` withhold `untrusted` items and the reports of exposed runs from an unexposed run. A capability that must read them declares so and is exposed from session start, so exposure stays decidable before the session opens. |
| D3 | Closed | Exposure is part of the consult cache key and of the single-flight join. ADR-38's status and index row note the amendment, and ADR-54 lists ADR-38 among the records it amends. |
| D4 | Closed | "Approving a check": approval goes through a decision flagged `untrusted` (class `never`) that shows the full definition and binds to its hash. Any change raises it again. |
| D5 | Closed | Provable fields go down to members of a structured field such as an interface contract. Free-text members an exposed run wrote are external-marked. |
| D6 | Closed | ADR-53's status and index row say "(amended by 54, proposed)", as ADR-32's do. ADR-54's own status ("accepted once its architecture review confirms it") keeps the I-07, QS-07 and threat-row text conditional on acceptance. |
| D7 | Closed | The risk row now states exposure, propagation through read tools and the cache, the end of taint at a person's approval, and clearance only by independently authored checks. |

## Revision 6

Revision 6 broke nothing. The amendment lists (ADR-54's status, the ADR-32, ADR-38 and ADR-53 status lines, and the index) agree. The revision history records revision 6. I-07, QS-07, the threat row and the risk row are consistent with the rewritten record.

**E1 (minor, for the R1 addendum).** The read-tool rule withholds `untrusted` items and reports of exposed runs. From R1, approved revisions can also carry external-marked text, and "reading it exposes the reader". That read could happen mid-session through `read_items` or `search`, after exposure was fixed. Fix, when R1 is specified: the read tools also withhold external-marked text from an unexposed run, or show only a placeholder, unless its capability declared it. This keeps exposure fixed before the session opens.
