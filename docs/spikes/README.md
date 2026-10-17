# Spikes

Time-boxed experiments in M0 that settle facts the design depends on (Roadmap, "Spikes and open questions"). Each spike has one file here: the plan first, then the report, filled in when the spike runs. A result that contradicts a decision record is answered by a superseding record before the M1 specifications are written; the default is the recorded fallback, not a redesign.

| Spike | Box | Plan | Blocks |
| --- | --- | --- | --- |
| SPK-1 Host, Claude and VS Code | 2 days | [SPK-1](SPK-1-host-claude-vscode.md) | SPEC-05, SPEC-06, SPEC-07, SPEC-10 |
| SPK-2 DBOS in FastAPI | 2 days | [SPK-2](SPK-2-dbos-fastapi.md) | SPEC-02, SPEC-06 |
| SPK-3 Codex and pi | 1 day | [SPK-3](SPK-3-codex.md) | SPEC-18 (M3); Q-3, Q-4, Q-5 |
| SPK-4 GitHub mechanics | 1 day | [SPK-4](SPK-4-github-mechanics.md) | SPEC-08, SPEC-09 |
| SPK-5 Cooperation mechanics | 2 days | [SPK-5](SPK-5-cooperation.md) | SPEC-17 (M3); ADR-38 configuration |

Order: SPK-1 and SPK-2 first and in parallel (the largest integration risks), then SPK-4, then SPK-5 and SPK-3. Everything runs in Claude Code cloud sessions prepared by the SessionStart hook, with credentials from the cloud environment (`docs/m0/operator-setup.md`, step 5).

## Rules

- **Throwaway code.** Spike code lives under `spikes/<spike>/` on a branch and is never merged into `packages/`, `factories/`, `agent-host/` or `runner/`. What survives is the report: facts, versions, commands and the decision they support.
- **Exact versions.** Record every package, image and CLI version used, and the date. A result is only as good as the versions it was observed on.
- **Primary sources.** Cite the documentation, source file or issue each claim rests on.
- **Pass or fail per experiment.** Each experiment states its pass criterion before it runs; the report says which held.
- **Make and prove.** The report is reviewed by someone who did not run the spike.

## Report template

Append to the plan file when the spike runs:

```markdown
## Report

Ran: <date> · By: <who or which session> · Host: <OS, Docker version>
Versions: <package@version, image@digest, CLI versions>

| # | Experiment | Result | Evidence |
| --- | --- | --- | --- |
| 1 | ... | pass / fail / partial | log excerpt, file, link |

### Answers
Q-n: <answer> — confirms / contradicts the recorded decision.

### Consequences
What the M1 specifications must now do; any superseding decision record needed.

### Steps to reproduce
Exact commands.
```
