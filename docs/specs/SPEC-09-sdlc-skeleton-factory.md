# SPEC-09 — SDLC skeleton factory
Status: draft · Milestone: M1
Kind: factory `sdlc` · Owns, in `factories/sdlc/`:
- the kinds `sdlc.requirement`, `sdlc.criterion` and `sdlc.ticket` with their edges and lifecycles;
- the capabilities `sdlc.implementer` and `sdlc.test_reviewer`;
- the template `sdlc.implement` (`/implement`);
- the check method `sdlc.ci_suite`;
- the workspace provider `sdlc.git` and the `git_commit` resolver;
- the delivery adapter `sdlc.github_pr`;
- the project configuration section `[factories.sdlc]`;
- the testbed's fixture intent in bundle form.

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

M1 proves the kernel/factory seam with a real user from the first line of code (ADR-34). This specification is that user: the thinnest SDLC factory that takes one hand-written ticket through implementation by Claude Code in its own worktree, copy-back into the mirror with hooks disabled, proof on the check station and by a test reviewer, and delivery as a pull request whose verification status the remote's ruleset requires (ADR-27, ADR-40). It uses only `grindstone.sdk`. Everything about git and GitHub lives here, and the kernel knows `git_commit` only as a subject kind.

## 2. Scope

In scope:
- **Kinds and edges.** Requirement, criterion and ticket, with their edges; lifecycles declared, with M1 writing only initial states.
- **Capabilities and template.** The implementer and the test reviewer, their prompts and report schemas. The `/implement` template in its linear form.
- **Proof.** The CI-suite check method, with criteria mapped from `@verifies` annotations.
- **Workspaces.** Mirrors and private clones on `repos`; workspace archives; copy-back with free, reviewed and protected tiers; the `git_commit` resolver.
- **Delivery.** The GitHub pull-request adapter: App authentication, mode probe, push, find-or-create pull request, verification status, merge in unenforced mode, observe with bypass detection.
- **Project configuration.** The section, and the testbed's configuration.
- **Live runs.** M1-01, M1-02 and M1-08.

Out of scope:
- **Other kinds and work.** Product, feature, milestone, exit criterion, spec header, design decision, ADR kinds and specification authoring: SPEC-14 (M2) and SPEC-20 (M4).
- **Reviewers.** Code, security and impact reviewers, the security path policy, reviewer-model enforcement, findings and learnings from `/implement`, and rework rounds: SPEC-18 (M3).
- **Lifecycle writers.** Transitions after the initial state (ticket `in_progress` … `done`, requirement `implemented` and `verified`), which S1's last step names: SPEC-11 and SPEC-12 add the writers.
- **Branch upkeep.** Updating a behind branch and re-verifying it (Q-7), which needs the regression sweep: SPEC-12 and SPEC-24. In M1 a behind pull request waits, and its status stays as posted for its head.
- **Signals.** Review comments and external check failures as findings: SPEC-24 (M5).
- **Repository export.** Rendering `docs/` artifacts and the `.grindstone/` export into the repository: SPEC-14.

## 3. Foundation links

Implements:
- **ADR-27, as amended by ADR-40.** Bare mirrors, worktrees, branches, copy-back path tiers, the CI-suite method and the GitHub pull-request adapter are factory code behind kernel ports. The control plane commits with hooks disabled from private clones and is the only place that pushes, with a GitHub App installation token. Each delivery posts one verification status the ruleset requires. The provider returns extra checks and permission requests with the subject.
- **ADR-40.** The mode is observed from the rules in force on the target branch at setup and before every delivery. In unenforced mode Grindstone merges with the verified head SHA and reports outside merges.
- **ADR-41.** The implementer and the test reviewer run Claude Code on different configured models by default. Reviewer independence beyond make and prove is SPEC-18's to enforce.
- **ADR-12 and I-15.** The test reviewer is a required prover. The implementer's tests prove nothing until the check station runs them and the reviewer passes them.
- **I-08.** No SDLC capability holds GitHub credentials. Only the adapter, in the control plane, uses the App key.
- **I-09 and QS-06.** No git hook, filter or repository configuration runs in the control plane.
- **I-14.** `.grindstone/` and CI configuration are protected paths at copy-back.

Delivers:
- **M1-01**, the factory clauses and the live run → AC-0910-1, AC-0912-1, AC-0920-1: "matched by need to `sdlc.implementer`"; "in its own worktree; the SDLC workspace provider copies the work back into the mirror and commits with hooks disabled; after a `delivery` decision the `sdlc.github_pr` adapter pushes and opens the pull request".
- **M1-02**, the GitHub clauses → AC-0915-1, AC-0916-1, AC-0917-1, AC-0921-1:
  - tagged tests mapped to criteria;
  - the status posted from the port's verification state;
  - "on the test repository, whose ruleset is enforced, the ruleset blocks merge until it succeeds";
  - the mode probe and the merge with the verified SHA.
- **M1-05**, these clauses → AC-0912-2, AC-0913-1:
  - "a hook written in a workspace never runs in `grindstone`";
  - "copy-back refuses protected paths and holds reviewed-tier paths for their reviewer".
- **M1-07**, the SDLC clause → AC-0907-1, AC-0907-2: "the test reviewer must pass before the status can succeed". With SPEC-03 and SPEC-08, the implementer's plan cannot name itself as prover.
- **M1-08** → AC-0922-1: "a Grindstone ticket for M2 is executed, verified and merged through Grindstone".

Depends on SDK 0.1.0 only (SPEC-03), with the port signatures from SPEC-06 (`WorkspaceProvider`, `CollectOutcome`) and SPEC-08 (`SubjectResolver`, `CheckMethod`, `DeliveryAdapter`).

Scenarios: S1, through the pull request opening with its status. The merge, and REQ-0101 moving to `verified`, are after M1's scope (section 2).

## 4. Requirements

REQ-0901: The factory registers only names in `sdlc`, imports nothing from `grindstone` but `grindstone.sdk`, and loads with no refusal.
REQ-0902: A criterion's `verifies` edge to its requirement has impact `review` and belongs to the criterion's check dependencies, so a semantic change to the requirement stales the criterion's evidence.
REQ-0903: An applied requirement enters `approved` and an applied ticket enters `ready`; no M1 code path writes another SDLC lifecycle state.
REQ-0904: `/implement <ticket>` creates one task with need `sdlc.implement`, whose inputs are the ticket, the requirements it implements and every criterion verifying them, pinned at their current revisions.
REQ-0905: The task's check plan requires `sdlc.ci_suite` on the check station for every input criterion with method `test`, and a `review` by need `sdlc.review.tests` for every input criterion.
REQ-0906: The implementer's workspace is writable and may make; the test reviewer's is read-only, it offers only `check` mode, and it may perform only `review` on `git_commit` subjects.
REQ-0907: The status of a delivery cannot be `success` until the test reviewer's check has a fresh pass for every criterion and every reviewed-tier path it was asked to acknowledge.
REQ-0908: The CI suite runs the project's declared gate commands and test command on the check station from a fresh materialization of the subject, and fails every target if a gate fails.
REQ-0909: The CI suite maps JUnit test outcomes to criteria through `@verifies <criterion ID>` annotations in the subject's test files; a target criterion passes only if it has at least one annotated test and every annotated test passed, and fails otherwise, naming why.
REQ-0910: `prepare` builds a workspace archive of the target branch's head, fetched into the project's bare mirror, and records that commit as the run's base.
REQ-0911: The control plane runs git only on repositories it created under `repos`, with a configuration it wrote: no system or global configuration, hooks pointed at an empty directory, no filter, fsmonitor or external diff, and the token only as an HTTP header in the environment.
REQ-0912: `collect` never runs git or any other program in the workspace: it reads the workspace's files (ignoring `.git`), refuses device files, sockets and FIFOs, writes the changes into a private clone at the base commit, and commits them with hooks disabled on branch `gs/<ticket>/<run>`, once per run.
REQ-0913: `collect` classifies each changed path. Paths within the ticket's declared paths are free. Tests, fixtures and docs, and any other path outside the declared paths, are reviewed. CI configuration, `.grindstone/`, lockfiles changed without their manifest, and project-protected globs are protected. It returns a permission request for each protected path, and an acknowledgement on the test reviewer's check for each reviewed path.
REQ-0914: The `git_commit` resolver materializes a commit from the mirror with `git archive`, read-only, and reads a file with `git cat-file`, never with a text conversion.
REQ-0915: The adapter authenticates as the GitHub App with a JWT signed by the granted key, uses installation tokens only in the control plane, and finds every pull request it may have created by its head branch, in every state, before creating one.
REQ-0916: The adapter posts the verification status with context `grindstone/verification`, a description of at most 140 characters, at the head the port names, and skips a post whose state the App already posted there.
REQ-0917: `observe_mode` reports enforced only when the target branch's rules in force require `grindstone/verification` from the App's integration ID with strict status checks, and unenforced for any other answer, including 403.
REQ-0918: `merge` passes the verified head SHA and the configured merge method, and reports a refusal because of a moved head as a failure, never retrying with another SHA.
REQ-0919: `observe` reports the pull request's head, merge (with whether the App merged it), closure, and, from the branch's activity, pushes and merges to the target branch by anyone but the App, using ETags so that an unchanged pull request costs no rate limit.
REQ-0920: Live run: on the testbed, the imported fixture ticket runs through `/implement` with Claude Code, and its pull request opens with a successful verification status that the ruleset requires.
REQ-0921: Live run: on the testbed, merge is blocked until the status succeeds; with the testbed private, the probe reports unenforced, Grindstone merges with the verified SHA, and a merge made in the UI is reported as a `delivery_bypass` finding.
REQ-0922: Live run: a Grindstone ticket for M2, run by the stable instance on Grindstone's own repository, is executed, verified and merged through Grindstone.

## 5. Design

**Package.** `factories/sdlc/src/grindstone_sdlc/`:
- `manifest.yaml`;
- `capabilities/*.yaml`, `prompts/*.md`, `schemas/*.json`;
- `config.schema.json`;
- code only for the adapter, the provider, the resolver and the check method: `git.py`, `github.py`, `ci_suite.py`, `adapters.py` (`ADAPTERS`).

Python dependencies, each the latest on PyPI on 17 October 2026: `pyjwt==2.15.1` and `cryptography==50.0.2` (the App's RS256 JWT, as SPK-4 used them). HTTP uses the standard library's `urllib.request`, as in SPK-4. The SDK version range is `>=0.1.0,<0.2.0`.

**Git hygiene (REQ-0911).** Every git invocation gets a fixed environment:
- `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null`;
- `HOME` set to an empty directory;
- `GIT_TERMINAL_PROMPT=0`;
- through `GIT_CONFIG_COUNT`:
  - `core.hooksPath=<empty dir>`, `core.fsmonitor=false`, `core.symlinks=true`;
  - `protocol.allow=never`, with `protocol.https.allow=always`;
  - `http.extraHeader=Authorization: Basic …` (the installation token as `x-access-token`) only for fetch and push.

The repositories are ones the factory created under `storage.dir(ctx)` (SPEC-03), whose `.git/config` it wrote: no filter, diff or merge driver is defined, so `.gitattributes` in repository content cannot run anything. SPK-4, experiment 8, showed that hooks set this way stay off through `receive-pack` too.

**Workspaces (REQ-0910, REQ-0912).**
- **Mirror:** `repos/<factory dir>/mirror.git`, bare, fetched from `https://github.com/<repository>` before each `prepare`.
- **Prepare:**
  1. Pin `base` = the target branch head.
  2. `git archive base` into a staging directory.
  3. Add a fresh `.git` from a one-commit clone of `base`, so the agent can `git diff`. It is never read back.
  4. Tar both into the archive SPEC-06's host extracts.
- **Collect** (key: the run):
  1. If branch `gs/<ticket>/<run>` exists in the mirror, return its commit.
  2. Otherwise walk the workspace with `os.scandir`, without following symlinks and skipping `.git`.
  3. Compare against `git ls-tree -r base` to find added, modified and deleted paths.
  4. Read each changed file and write it into a private worktree `work/<run>` checked out at `base`.
  5. `git add -A` and commit as the App's bot identity with the message `<ticket>: <title> (run <run>)`, then set the branch.

  An unreadable file fails the run with the file named, because an agent can only hide its own work.
- **Discard:** removes `work/<run>`. The host removes the workspace (SPEC-06).

**Tiers and the collect outcome (REQ-0913).**

| Tier | Paths (defaults, extended by `[factories.sdlc.paths]`) | Outcome |
| --- | --- | --- |
| Free | The ticket's `declared_paths` (globs) | Committed |
| Reviewed | Outside the declared paths: `tests/**`, `test/**`, `fixtures/**`, `docs/**`, and any other source path | Committed; added to the test review check's `acknowledge` list |
| Protected | `.github/**`, `.grindstone/**`, `**/uv.lock` without its `pyproject.toml`, `**/pnpm-lock.yaml` without its `package.json`, `**/package-lock.json` without its `package.json`, and `paths.protected` | Committed only if its `permission` decision answers allow; otherwise the run fails `checks_failed` with the list (SPEC-06) |

A protected path is in the commit while its permission is pending, and the kernel does not let the task verify until every decision is answered allow (SPEC-06). So the commit is never verified or delivered with a refused path.

**Resolver (REQ-0914).** `materialize`: `git archive <sha> | tar -x` into `dest`, then `chmod -R a-w`. `read_file`: `git cat-file blob <sha>:<path>`.

**CI suite (REQ-0908, REQ-0909).** Shape `test`, environment-relevant.
- `build_job`: the steps are each of `commands.gates` with names, then `commands.test`, with the declared environment.
- `environment(subject)`: `{runtime, package_manager, lockfile_sha256}`. The lockfile hash is read through the resolver at the subject, so a changed lockfile stales test evidence (Factories, "Environment fingerprint").
- `interpret`:
  1. List the subject's files matching `tests.glob` and read each.
  2. Find each `@verifies (AC-\d{4}-\d+)`, and attach it to the nearest preceding line matching `tests.def_pattern`, giving a `(file, test name)` pair.
  3. Match each JUnit outcome to a pair by test name, and by file or by the module path in `classname`. An ambiguous match is a failure, with its reason.
  4. Per target criterion: `pass` if it has at least one annotated test and all passed; `fail` with "no test annotated @verifies AC-…" if it has none; `fail` naming the failing or missing tests otherwise.
  5. A failed gate fails every target, citing the gate's log.

**Capabilities.**

| | `sdlc.implementer` | `sdlc.test_reviewer` |
| --- | --- | --- |
| Offers | `sdlc.implement` · `delegate`; accepts `sdlc.ticket` | `sdlc.review.tests` · `check` |
| Agent | preset `claude`, model slot `primary`, high effort | preset `claude`, model slot `secondary` |
| Workspace | `write`, provider `sdlc.git` | `read_only` |
| Permissions | `read`, `write`, `shell`; otherwise `deny` (no web tools) | `read`, `shell`; otherwise `deny` |
| Produces | Report `implementation_report.json`: `summary`, `criteria` (IDs addressed), `tests` (paths added or changed), `notes`; no kinds in M1 | Report `test_review.json`: SPEC-08's `ReviewVerdict`, with per-test notes |
| May check | — | `review` on `git_commit` |
| Tier | T1 | T0 |

Permission categories are agent-neutral. SPEC-06's preset options translate them for Claude Code.

The model slots `primary` and `secondary` name models in instance configuration (SPEC-06). Their values are the operator's to choose before M1-01's live run, as status.md records, and differ by default. Prompt content:
- **The implementer's:** implement the ticket within its declared paths; annotate each test with `@verifies <criterion>`; run the tests (as working notes); call `report` once.
- **The test reviewer's:** for each criterion, judge whether its annotated tests verify it, and were not weakened or deleted against the base; pass each listed path explicitly or fail it with a reason (QS-01).

**Template `sdlc.implement`** (command `/implement`, argument `ticket`):

```yaml
steps:
  - task: implement
    need: sdlc.implement
    mode: work
    inputs: {from: args.ticket, follow: [sdlc.implements, ~sdlc.verifies]}
    output: {report: implementation_report.json}
    checks:
      - {method: sdlc.ci_suite, by: station, required: true,
         targets: {kinds: [sdlc.criterion], where: {method: test}}}
      - {method: review, by: sdlc.review.tests, required: true,
         targets: {kinds: [sdlc.criterion]}}
  - deliver: open_pr
    adapter: sdlc.github_pr
    from: implement
```

It loads under SPEC-03's make-and-prove rule, because `sdlc.review.tests` is offered only by the read-only test reviewer.

**Adapter `sdlc.github_pr`.**
- **Authentication:** an RS256 JWT from the `sdlc.github_app_key` secret (granted per project) and `app_id`, then an installation token for `installation_id`, cached until five minutes before it expires.
- **Calls:** every call carries `X-GitHub-Api-Version`, and every response is parsed by a contract with size bounds. The calls, as SPK-4 settled them:

| Port call | GitHub |
| --- | --- |
| `observe_mode` | `GET /repos/{r}/rules/branches/{branch}`: enforced only for `required_status_checks` with `strict_required_status_checks_policy: true` and `{context: "grindstone/verification", integration_id: app_id}`; anything else, 403 included, is unenforced |
| `prepare` | Key `sdlc:<project>:<ticket>:<sha>`; title `<ticket>: <title>`; body from the port's summary: ticket, requirements and criteria with their hashes, evidence with freshness, the mode |
| `deliver` | Push `gs/<ticket>/<run>` from the mirror (a remote ref already at the SHA is success); `GET /pulls?head=<owner>:<branch>&state=all`, else `POST /pulls` |
| `publish_status` | `GET /commits/{sha}/statuses` for the App's latest on the context; if it differs, `POST /statuses/{sha}` |
| `merge` | `PUT /pulls/{n}/merge` with `sha` and `merge_method` (default `squash`); a 409 is `failed`, cause `head_moved` |
| `observe` | `pulls/{n}`, and `activity?ref=refs/heads/<target>`, with ETags; merges by `<app>[bot]` are the port's; other `pr_merge` and `push` entries touching `published_paths` are bypasses |

**Project configuration** (`[factories.sdlc]`, validated by `config.schema.json`):
- `repository`, `target_branch`, `app_id`, `installation_id`, `merge_method`;
- `commands.gates` (argv lists), `commands.test` (argv, writing JUnit under `$GRINDSTONE_OUT`);
- `tests.glob`, `tests.def_pattern` (default `^\s*def (test_\w+)\(`);
- `toolchain` (`runtime`, `package_manager`, `lockfile`);
- `paths.protected`, `paths.reviewed`;
- `published_paths` (default `[".grindstone/**"]`).

The project grants the secret `sdlc.github_app_key`.

**Testbed.**
- `intent/` gains `TKT-0001.bundle.yaml` holding REQ-0101, AC-0101-1 (method `test`) and TKT-0001, in SPEC-04's bundle format; the Markdown files stay as documentation.
- The fixture toolchain image adds `pytest==9.1.1` so `commands.test` can write JUnit. That is M0-04's runner image plus one pinned package. M0-04's `make fixture` keeps running the unittest API.
- `deploy/projects/testbed.toml` is the testbed's project configuration.

The testbed's IDs belong to its own ledger, so its REQ-0101 is not this repository's.

**State and ownership.** Factory storage on `repos` (mirrors, private worktrees). The factory owns no tables: the kernel records deliveries, evidence and runs.

**Security.**
- B3: fetched repository content is untrusted. It is archived, read and committed as data; nothing from it is executed in the control plane (REQ-0911, REQ-0912).
- B1: the agent gets a copy without credentials (SPEC-05).
- The App key is read only through the SDK's granted secret. Tokens never appear in URLs, argv or logs.
- Status descriptions and pull-request bodies are generated from ledger data, not from agent text. The body quotes item titles, and GitHub renders it as Markdown.

**Make and prove.**

| Subject | Maker | Provers |
| --- | --- | --- |
| The ticket's commit (`git_commit`) | `sdlc.implementer` | The check station (`sdlc.ci_suite`) and `sdlc.test_reviewer` (`review`), both required |
| The pull request | The delivery port through `sdlc.github_pr` | Not a subject; gated by the evidence above and a `delivery` decision |

**Fitness functions.**
- FF-01 for the factory's imports.
- FF-10 for the adapter's and provider's external steps (fetch, collect commit, push, pull request, status, merge, observe), with crash-and-resume tests against a fake GitHub.
- The conformance kit arrives with SPEC-13. Until then SPEC-03's loader rules and this specification's tests stand in for it.

## 5F. Factory manifest

**Item kinds.**

| Kind | ID pattern (examples) | Fields (semantic unless marked) | References (edge, impact, check dependency) | Lifecycle (initial in M1) |
| --- | --- | --- | --- | --- |
| `sdlc.requirement` | `^REQ-[0-9]{4}$` (`REQ-0101`) | `statement` (text), `priority` (`must`, `should`, `could`), `rationale` (text) | — | `approved` → `implemented` (task) → `verified` (evidence); `approved`, `implemented` or `verified` → `retired` (changeset). A requirement is a draft only as a revision in an unapproved ChangeDraft (SPEC-04) |
| `sdlc.criterion` | `^AC-[0-9]{4}-[0-9]+$` (`AC-0101-1`) | `condition` (text), `method` (`test`, `review`, `manual`, `command`), `required` (bool, default true) | `verifies` → requirement (`sdlc.verifies`, review, yes) | None |
| `sdlc.ticket` | `^TKT-[0-9]{4}$` (`TKT-0001`) | `goal` (text), `declared_paths` (list of globs), `estimate` (`small`, `medium`, `large`; presentation) | `implements` → requirements (`sdlc.implements`, review, no); `after` → tickets (`sdlc.after`, review, no) | `ready` → `in_progress` (task) → `in_review` (task) → `done` (delivery); `blocked` and `cancelled` from any state but `done` (task) |

**Capabilities.** `sdlc.implementer` and `sdlc.test_reviewer` as in section 5.

**Templates.** `sdlc.implement` as in section 5. It is linear, with no edges, so `max_rounds` does not arise.

**Check methods.** `sdlc.ci_suite`, shape `test`, environment-relevant.

**Subjects and workspace providers.** No subject kinds of its own. The provider `sdlc.git` (writing workspaces). The resolver for the kernel kind `git_commit`, in projects that enable `sdlc`.

**Delivery adapters.** `sdlc.github_pr`.

**Interface shapes.** None in M1.

**Decision kinds and eligibility classes.** No factory kinds in M1. The kernel kinds keep their seed classes (SPEC-04). The Factories tab's SDLC policy table applies from SPEC-15 and SPEC-25.

**Conformance kit.** Not yet available (SPEC-13). The loader's rules (SPEC-03) pass: namespaced names, valid lifecycles, make and prove at load, shapes. The adapter's replay tests run against a fake GitHub.

## 6. Decisions

DEC-0901: Collect copies files out of the workspace into a private clone instead of committing in the workspace · Any git command run in an agent-written `.git` can execute agent-written configuration (hooks, `core.fsmonitor`, filters); reading files as data cannot · Rejected: committing in the worktree with hooks off (a hook is only one of several ways repository configuration runs code); a worktree whose `.git` points into `repos` (the agent station would need `repos`, which FF-05 forbids).
DEC-0902: The CI suite's results are JUnit files the test command writes under `$GRINDSTONE_OUT`, mapped to criteria by annotations read from the subject in the control plane · Annotations are read as data from the verified commit, so a test cannot claim a criterion by printing its ID · Rejected: annotations reported by the test run itself (code under test could forge them).
DEC-0903: Paths outside the declared ones that are not protected are reviewed, not refused · Implementers legitimately touch nearby files; the test reviewer must acknowledge each explicitly, which holds them without blocking work · Rejected: refusing every path outside the declared ones (drives the operator around the system, which the Risks table warns of).
DEC-0904: In enforced mode the pull request is merged by a person on GitHub; Grindstone merges only in unenforced mode · ADR-40 has Grindstone merge only where the remote cannot enforce the gate, and auto-merge is R2 · Rejected: Grindstone merging in both modes (merging is L3 behaviour, deferred).

## 7. Tickets and acceptance criteria

TKT-0901: Manifest: kinds, edges, lifecycles, capabilities, prompts, report schemas, template, configuration schema · implements REQ-0901 to REQ-0907 · depends on TKT-0302 · paths `factories/sdlc/src/grindstone_sdlc/`, `factories/sdlc/tests/`.
TKT-0902: Git workspaces: mirror, prepare, collect with tiers, resolver · implements REQ-0910 to REQ-0914 · depends on TKT-0901, TKT-0603 · paths `factories/sdlc/src/grindstone_sdlc/git.py`, `factories/sdlc/tests/`.
TKT-0903: CI suite method · implements REQ-0908, REQ-0909 · depends on TKT-0902, TKT-0802 · paths `factories/sdlc/src/grindstone_sdlc/ci_suite.py`, `factories/sdlc/tests/`.
TKT-0904: GitHub adapter and a fake GitHub for tests · implements REQ-0915 to REQ-0919 · depends on TKT-0804 · paths `factories/sdlc/src/grindstone_sdlc/github.py`, `factories/sdlc/tests/fake_github.py`, `factories/sdlc/pyproject.toml`.
TKT-0905: Testbed bundle, toolchain image with pytest, testbed project configuration · implements REQ-0904, REQ-0920 · depends on TKT-0901 · paths `deploy/projects/`, `docker/runner.Dockerfile`; testbed `intent/`.
TKT-0906: Live runs M1-01, M1-02 (both modes) and M1-08 on the operator's machine · implements REQ-0920 to REQ-0922 · depends on TKT-0902 to TKT-0905 and SPEC-10's tickets · paths `docs/live/`.

AC-0901-1: The factory loads with SDK 0.1.0, every name starts with `sdlc.`, and FF-01 finds no import from `grindstone` but `grindstone.sdk` · verifies REQ-0901 · unit · `test_sdlc_manifest_loads`.
AC-0902-1: After a ChangeSet changes REQ-0101's statement, the evidence for AC-0101-1 is stale, naming REQ-0101 · verifies REQ-0902 · integration · `test_requirement_change_stales_criterion_evidence`.
AC-0903-1: Applying the testbed bundle leaves REQ-0101 `approved` and TKT-0001 `ready` · verifies REQ-0903 · integration · `test_initial_sdlc_states`.
AC-0904-1: `/implement TKT-0001` on the testbed bundle creates one task with need `sdlc.implement` pinning TKT-0001, REQ-0101 and AC-0101-1 at their current hashes · verifies REQ-0904 · integration · `test_implement_pins_ticket_closure`.
AC-0905-1: That task's plan has a required `sdlc.ci_suite` check targeting AC-0101-1 and a required review by `sdlc.review.tests` targeting it, resolved to `sdlc.test_reviewer` · verifies REQ-0905 · integration · `test_implement_check_plan`.
AC-0906-1: The test reviewer's capability is read-only, offers only `check`, and may check only `review` on `git_commit`; a variant manifest giving the implementer `sdlc.review.tests` is refused at load · verifies REQ-0906 · unit · `test_reviewer_capability_shape`.
AC-0907-1: Scripted: with the CI suite passing and the scripted test reviewer failing AC-0101-1 as a weakened test, the gate fails and the posted state is never `success` · verifies REQ-0907 · scripted agent · `test_test_reviewer_gates_status`.
AC-0907-2: Scripted: with a reviewed-tier path collected and the reviewer passing every criterion but not acknowledging the path, its report is refused; acknowledging it lets the gate pass · verifies REQ-0907 · scripted agent · `test_reviewed_paths_need_acknowledgement`.
AC-0908-1: In the runner image, a failing gate command fails AC-0101-1 with the gate's log cited, even though the tests pass · verifies REQ-0908 · integration · `test_ci_suite_gates_fail_targets`.
AC-0909-1: With JUnit outcomes and annotated test sources, a criterion with no annotated test fails "no test annotated", one whose annotated test failed fails naming it, one whose tests all passed passes, and a test printing `@verifies AC-0101-1` without the annotation in its source claims nothing · verifies REQ-0909 · unit · `test_ci_suite_maps_annotations`.
AC-0910-1: `prepare` fetches the mirror, pins the target head as base, and produces an archive whose tree equals `git archive base`, plus a `.git` · verifies REQ-0910 · integration · `test_prepare_archive_at_base`.
AC-0911-1: With every hostile configuration in the testbed fixture (a hook in the mirror and the clone, `core.fsmonitor`, a filter in `.gitattributes`) planted, fetch, commit and push run none of them, and the token appears in no argv or URL (checked through `/proc` during the push) · verifies REQ-0911 · security · `test_git_runs_with_hygiene`.
AC-0912-1: `collect` after a scripted session commits exactly the changed files on `gs/TKT-0001/<run>` at base, and a second `collect` for the run returns the same commit · verifies REQ-0912 · crash-and-resume · `test_collect_commits_once`.
AC-0912-2: A workspace whose `.git/hooks/pre-commit`, `.git/config` `core.fsmonitor` and `core.hooksPath` would write a marker file leaves no marker after `collect`; a FIFO in the workspace fails the run naming it · verifies REQ-0912 · security · `test_collect_never_runs_workspace_git`.
AC-0913-1: A collect touching a declared path, a test outside them and `.github/workflows/ci.yml` returns the test as an acknowledgement on the review check and a permission request for the workflow file; denying it fails the run `checks_failed` listing it, and allowing it lets the task verify · verifies REQ-0913 · integration · `test_copy_back_tiers`.
AC-0914-1: `materialize` produces a read-only tree equal to the commit, and `read_file` on a path with a textconv attribute returns the raw blob · verifies REQ-0914 · unit · `test_git_commit_resolver`.
AC-0915-1: Against a fake GitHub: killed after the push, and again after creating the pull request, `deliver` on restart pushes nothing new and finds the existing pull request by head branch, so one pull request exists · verifies REQ-0915 · crash-and-resume · `test_github_deliver_once`.
AC-0916-1: Against the fake: a status is posted with the right context and a description of at most 140 characters, and repeating the post finds the App's existing status and sends nothing · verifies REQ-0916 · integration · `test_github_status_idempotent`.
AC-0917-1: Against the fake: the probe reports enforced for the exact rule, and unenforced for a 403, a missing rule, a wrong integration ID and non-strict checks · verifies REQ-0917 · unit · `test_mode_probe`.
AC-0918-1: Against the fake: `merge` passes the verified SHA; a 409 after a concurrent push reports `head_moved` and is not retried · verifies REQ-0918 · integration · `test_merge_with_verified_sha`.
AC-0919-1: Against the fake: an unchanged pull request returns 304s that the adapter treats as nothing new; a merge by a user and a push to the target branch are reported as not by the App · verifies REQ-0919 · integration · `test_observe_reports_head_merges_and_pushes`.
AC-0920-1: Live run: the testbed's TKT-0001, imported and approved, runs through `/implement` with Claude Code on the operator's subscription; the CI suite and test reviewer pass; after the `delivery` decision the pull request opens with `grindstone/verification` successful · verifies REQ-0920 · live run · `live_m1_01_ticket_to_pull_request`.
AC-0921-1: Live run, on the operator's machine as the App: on the testbed, merge is refused while the status is pending and accepted when it succeeds; after a criterion edit, the status returns to pending; with the testbed private, the probe reports unenforced, Grindstone merges with the verified SHA, and a merge made in the UI becomes a `delivery_bypass` finding · verifies REQ-0921 · live run · `live_m1_02_enforced_and_unenforced`.
AC-0922-1: Live run: the stable instance executes a Grindstone ticket for M2 on `ex1tium/grindstone`, the pull request carries a successful `grindstone/verification` status that the ruleset requires, and it is merged · verifies REQ-0922 · live run · `live_m1_08_self_hosted_ticket`.

## 8. Test plan

- **Unit:** AC-0901-1, AC-0906-1, AC-0909-1, AC-0914-1, AC-0917-1.
- **Integration**, the kernel with the factory, the runner image and a fake GitHub: AC-0902-1, AC-0903-1, AC-0904-1, AC-0905-1, AC-0908-1, AC-0910-1, AC-0913-1, AC-0916-1, AC-0918-1, AC-0919-1.
- **Crash-and-resume:** AC-0912-1, AC-0915-1.
- **Security:** AC-0911-1, AC-0912-2.
- **Scripted agent**, full `/implement` with the scripted preset for both capabilities: AC-0907-1, AC-0907-2.
- **Live runs**, at the M1 close, kept with their logs: AC-0920-1, AC-0921-1, AC-0922-1. They run on the operator's machine, because a cloud session cannot act as the App (SPK-4).

## 9. Open items and risks

OQ-0901: Which Grindstone ticket for M2 is M1-08's? · Default: a small M2 ticket whose criteria have unit tests that run without Postgres or Docker, so the CI suite runs `uv sync --frozen` and `pytest -m "not integration"` in Grindstone's own toolchain image · Resolved at the M1 review, when M2's specifications exist.
OQ-0902: Before M1-08, is the GitHub App installed on `ex1tium/grindstone`, with `grindstone/verification` required from it in that repository's ruleset? · Default: the operator installs it and adds the check to `.github/rulesets/grindstone-main.json` before the run · Resolved by the operator at the M1 close.
OQ-0903: Should a behind pull request be updated and re-verified automatically? · Default: no in M1; it waits with its status as posted (Q-7 confirmed that auto-merge waits too) · Resolved by SPEC-12 and SPEC-24.

Risks mitigated: repository-borne execution in the control plane (hygiene, copy-out collect, tests with hostile fixtures); forged test claims (annotations read from the commit; reviewer acknowledgement); duplicate pushes, pull requests and statuses (lookups by head branch and existing statuses); unseen bypass in unenforced mode (activity and merge observation).
Risk added: the annotation scanner is language-specific. Mitigation: its patterns are project configuration, with Python's as the default; other languages set their own.

## 10. Rollout

SDLC factory version 0.1.0, with SDK range `>=0.1.0,<0.2.0`. The testbed gains its bundle and project configuration; its Markdown intent stays as documentation. The fixture toolchain image adds pytest. The operator installs the App on `ex1tium/grindstone` before M1-08 (OQ-0902). No stored data exists before M1.
