"""M0-04: the fixture project's tagged tests pass in the runner toolchain image, as a check job.

The subject is mounted read-only, the job directory is the only writable mount, and the container
has no network, no capabilities, a read-only root and no credentials. Every test tagged
`@verifies AC-…` must run and pass; the result is written to the job directory as the check
station will (SPEC-08).

Usage: python scripts/fixture_check.py FIXTURE_DIR [--image TAG] [--no-build]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TAG = re.compile(r"@verifies\s+(AC-\d+-\d+)")
# Runs in the container: run the tests, print one JSON line of outcomes by test name.
RUN_TESTS = """
import json, sys, unittest
suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
outcomes = {}
class Result(unittest.TextTestResult):
    def addSuccess(self, t): super().addSuccess(t); outcomes[t._testMethodName] = "ok"
    def addFailure(self, t, e): super().addFailure(t, e); outcomes[t._testMethodName] = "fail"
    def addError(self, t, e): super().addError(t, e); outcomes[t._testMethodName] = "error"
    def addSkip(self, t, r): super().addSkip(t, r); outcomes[t._testMethodName] = "skipped"
ok = unittest.TextTestRunner(resultclass=Result, verbosity=0).run(suite).wasSuccessful()
print(json.dumps(outcomes))
sys.exit(0 if ok else 1)
"""
JOB = "/var/lib/grindstone/runs/job"
WHOAMI = "import os, sys; print(os.getuid(), sys.version.split()[0]); print(*sorted(os.environ))"
WRITE = "import sys; open(sys.argv[1], 'w').write(sys.argv[2])"
SECRET_HINTS = ("TOKEN", "SECRET", "PASSWORD", "KEY", "GRINDSTONE_GITHUB", "ANTHROPIC", "CLAUDE")


def tagged_tests(fixture: Path) -> dict[str, list[str]]:
    """Criterion ID -> test functions whose docstring carries `@verifies <ID>`."""
    found: dict[str, list[str]] = {}
    for path in sorted((fixture / "tests").rglob("test_*.py")):
        current = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if m := re.match(r"\s*def (test_\w+)\(", line):
                current = m.group(1)
            for criterion in TAG.findall(line):
                found.setdefault(criterion, []).append(current)
    return found


def run_in_runner(
    image: str, fixture: Path, job: Path, command: list[str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp",  # noqa: S108 - the container's own /tmp
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--mount", f"type=bind,source={fixture},target=/subject,readonly",
            "--mount", f"type=bind,source={job},target={JOB}",
            "--workdir", "/subject", image, *command,
        ],
        capture_output=True,
        text=True,
        check=False,
    )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--image", default="grindstone-runner:fixture-check")
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args(argv)
    fixture: Path = args.fixture.resolve()
    image: str = args.image
    if not args.no_build:
        build = ["docker", "build", "-q", "-f", "docker/runner.Dockerfile", "-t", image, "."]
        subprocess.run(build, cwd=REPO, check=True, stdout=subprocess.DEVNULL)

    tags = tagged_tests(fixture)
    with tempfile.TemporaryDirectory(prefix="grindstone-job-") as tmp:
        job = Path(tmp)
        job.chmod(0o777)  # the container's gs-runner user writes the result here
        who = run_in_runner(image, fixture, job, ["python", "-c", WHOAMI])
        uid, python, *env = who.stdout.split()
        leaked = [name for name in env if any(h in name for h in SECRET_HINTS)]
        tests = run_in_runner(image, fixture, job, ["python", "-c", RUN_TESTS])
        outcomes: dict[str, str] = (
            json.loads(tests.stdout.strip().splitlines()[-1]) if tests.stdout.strip() else {}
        )
        criteria = {c: {t: outcomes.get(t, "not run") for t in ts} for c, ts in tags.items()}
        all_ok = all(o == "ok" for ts in criteria.values() for o in ts.values())
        result = {
            "image": image, "uid": int(uid), "python": python, "network": "none",
            "leaked_env": leaked, "tests_exit": tests.returncode, "tests": outcomes,
            "criteria": criteria,
            "pass": tests.returncode == 0 and not leaked and int(uid) != 0 and bool(tags)
            and all_ok,
        }  # fmt: skip
        write = run_in_runner(
            image, fixture, job, ["python", "-c", WRITE, f"{JOB}/result.json", json.dumps(result)]
        )
        result["job_dir_writable"] = write.returncode == 0 and (job / "result.json").is_file()
        subject_write = run_in_runner(
            image, fixture, job, ["python", "-c", "open('/subject/x', 'w')"]
        )
        result["subject_read_only"] = subject_write.returncode != 0
        result["pass"] = (
            bool(result["pass"]) and result["job_dir_writable"] and result["subject_read_only"]
        )
    print(json.dumps(result, indent=2))
    if tests.returncode != 0:
        print(tests.stderr[-3000:], file=sys.stderr)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
