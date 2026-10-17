# Rulesets

Repository rulesets in GitHub's import format (Settings → Rules → Rulesets → New ruleset → Import a ruleset). They are kept here so the rules are reviewed like code; GitHub does not apply them from this folder.

| File | Repository | What it enforces |
| --- | --- | --- |
| `grindstone-main.json` | `ex1tium/grindstone` | Pull requests only, squash merge, linear history, no force push or deletion; both CI jobs must pass on an up-to-date branch. The checks' source is GitHub Actions (App ID 15368), so nothing else can satisfy them. No approving review is required: with one operator, an author cannot approve their own pull request |
| `testbed-main.json` | `ex1tium/grindstone-testbed` | Pull requests only; `grindstone/verification` must pass on an up-to-date branch (M1-02, SPK-4) |

**After importing `testbed-main.json`:** edit the `grindstone/verification` check and set its source to the Grindstone GitHub App. The App ID only exists once you create the App, so the file cannot carry it. Without a source restriction, any workflow in the testbed could post that status and satisfy the check; SPK-4 experiment 2 verifies the restriction holds.

**Plan and delivery modes** (ADR-40). GitHub's free plans enforce rulesets on public repositories only. Both repositories are public, so both rulesets are enforced: SPK-4 and M1-02 test the enforced path for real, and `main` on `ex1tium/grindstone` is protected. Grindstone still builds and tests the unenforced mode, for other operators' private repositories; SPK-4 switches the testbed to private for that one experiment.
