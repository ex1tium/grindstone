# SPK-4: running the App experiments locally

The App experiments need a machine that reaches `api.github.com` directly (a cloud session's GitHub proxy acts as the operator's account, never as the App; see the report in `SPK-4-github-mechanics.md`). This guide is for the operator. One script, `spk4/run.py` on the testbed branch `claude/youthful-franklin-oq4j5j`, runs every remaining experiment as the App, pauses for the few steps that need you in the GitHub web UI, and writes its results to a folder you push back.

Time: about 30 minutes, most of it waiting on GitHub. It can be split into two sittings (step 5).

## 1. What you need

- `git`, and `uv` (or Python 3.12+ with `pip install pyjwt==2.15.1 cryptography==50.0.2`, then `python3` instead of `uv run`).
- The App's private key as a `.pem` file, its App ID and its installation ID (`secrets/github_app_*` in `operator-setup.md`, step 3).
- The `gh` CLI signed in as you, for experiment 2. The web UI works too.
- A browser signed in to GitHub as you.

## 2. Testbed settings, before running

On `https://github.com/ex1tium/grindstone-testbed/settings`:

- **Actions → General**: allow actions (they look disabled now; experiment 2 runs the `Forge verification status` workflow).
- **General → Pull Requests**: allow squash merging, and tick **Allow auto-merge** (experiment 5; the script stops and asks if it is off).

## 3. Get the script

```sh
git clone https://github.com/ex1tium/grindstone-testbed.git
cd grindstone-testbed
git checkout claude/youthful-franklin-oq4j5j
```

Commands below are for a POSIX shell; Windows PowerShell equivalents follow each block. Windows PowerShell 5.1 has no `&&`: run commands one per line or separate them with `;`.

## 4. Point it at the App

In the shell you run it from. A key file is simpler than the base64 form; nothing is printed or written to the results.

```sh
export GRINDSTONE_GITHUB_APP_ID=<app id>
export GRINDSTONE_GITHUB_APP_INSTALLATION_ID=<installation id>
export GRINDSTONE_GITHUB_APP_PRIVATE_KEY_FILE=~/path/to/github_app_private_key.pem
```

```powershell
$env:GRINDSTONE_GITHUB_APP_ID = "<app id>"
$env:GRINDSTONE_GITHUB_APP_INSTALLATION_ID = "<installation id>"
$env:GRINDSTONE_GITHUB_APP_PRIVATE_KEY_FILE = "C:\path\to\github_app_private_key.pem"
```

These last only for that PowerShell window. Install `uv` on Windows with `winget install --id=astral-sh.uv -e` and open a new window.

Check that the App can authenticate (opens nothing, changes nothing):

```sh
uv run spk4/run.py --only e0
```

It should print `Setup: ok` with the installation seeing only `ex1tium/grindstone-testbed`. A 401 means the App ID or key is wrong; a 404 on the token means the installation ID is wrong.

## 5. Run

All at once:

```sh
uv run spk4/run.py
```

Or in two sittings, keeping the testbed private for as short a time as possible: `uv run spk4/run.py --public-only`, then later `uv run spk4/run.py --only e9 e10 e11 restore`.

The script stops with `>>> OPERATOR STEP` five times. Do the step, then press Enter:

| When | What you do |
| --- | --- |
| Experiment 2 | Forge the status on the commit it names: `gh workflow run forge-status.yml -R ex1tium/grindstone-testbed -f sha=<sha>` and/or the `gh api .../statuses/<sha>` command it prints (a status from your own account). Wait for the workflow run to finish. |
| Experiment 5 | Only if auto-merge is off: turn it on (step 2). |
| Experiment 9 | Make the testbed **private** (Settings → Danger Zone → Change visibility). |
| Experiment 11 | Merge the named pull request in the web UI, then edit `README.md` on `main` in the web UI and commit directly to `main`. |
| Restore | Make the testbed **public** again. The script asks for this even if an earlier step crashed after it went private. |

**If experiment 2 prints `FAIL`**, a status that did not come from the App merged a pull request. Stop there and tell the session: that needs a decision record before the M1 specifications.

What the run changes on the testbed: about nine pull requests on branches `spk4/<run>-*` (five merged into `main`, adding small files under `spk4/`), commit statuses on those commits, one direct commit to `main` (yours, in experiment 11), and the temporary visibility change.

## 6. Send the results back

Results are in `spk4/results/<run>/`: `summary.md` (one line per experiment), `log.jsonl` (every API call's method, path, status and rate-limit headers, and every git command), and the raw JSON per experiment. They hold no token or key: API responses are reduced to states, logins and SHAs.

```sh
git add spk4/results
git commit -m "test: SPK-4 results"
git push origin claude/youthful-franklin-oq4j5j
```

The same three lines work in PowerShell.

Then tell the session; it reads them, completes the report in `SPK-4-github-mechanics.md` and updates `docs/m0/status.md`.

## What each experiment checks

| ID | Check | Pass |
| --- | --- | --- |
| e0 | The App's identity and permissions, the installation's repositories, the rules in force | Token minted; only the testbed visible |
| e1 | Pending, then success, set by the App; status length limits | `blocked` until success, then `clean`, merge accepted |
| e2 | A forged status from Actions or your account | Merge still refused |
| e3 | A new commit after success | Old status stops counting; merging with the old SHA refused |
| e4 | Base advanced, strict checks | `behind` until updated; new head needs a new status |
| e5 | Auto-merge on a behind pull request; disarming | Waits for the update and the new status, then merges |
| e6 | Lookup by head branch, open, closed and merged | All found; a missing branch returns nothing |
| e7 | One poll's REST calls, installation rate limit, ETags | Limit recorded; `304` responses cost nothing |
| e8 | Clone → bare mirror → GitHub with failing hooks planted, hooks disabled | Push lands; no hook runs |
| e9 | Rules in force, public against private | The probe says enforced only when public |
| e10 | Private: merge passing the verified SHA after a new push | Refused; `main` unchanged |
| e11 | Private: a merge in the UI and a direct push | Both visible to a poll (merged by, commits with no pull request, activity API) |
