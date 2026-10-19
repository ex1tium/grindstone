"""FF-04: every dependency, tool, image and action is pinned exactly (ADR-01).

Fails when a Python requirement is not `==`, a Node dependency is a range or a
tag, an image has no digest, a GitHub Action is not pinned to a full commit
SHA, a runtime version file is not an exact version, or a lockfile is
missing. Lockfile freshness is checked separately by `uv lock --check` and
`pnpm install --frozen-lockfile`.

Usage: python -m scripts.ff.pins [ROOT]
"""

import json
import re
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "node_modules", "fixtures", "dist", "build", ".svelte-kit"}

EXACT_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
PY_PIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9,._-]+\])?==[0-9][0-9A-Za-z.+!-]*$")
NODE_PIN = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
ACTION_SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
PNPM_PIN = re.compile(r"^pnpm@\d+\.\d+\.\d+\+sha512\.[0-9a-f]+$")


def _rel(path: Path, root: Path) -> str:
    """A repository-relative path written with forward slashes on every platform."""
    return path.relative_to(root).as_posix()


def _files(root: Path, pattern: str) -> Iterator[Path]:
    for path in sorted(root.rglob(pattern)):
        if not SKIP_DIRS.intersection(path.relative_to(root).parts):
            yield path


def _workspace_members(root: Path) -> set[str]:
    """Names declared as uv workspace sources may be bare (they are not downloaded)."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return set()
    sources = (
        tomllib.loads(pyproject.read_text(encoding="utf-8"))
        .get("tool", {})
        .get("uv", {})
        .get("sources", {})
    )
    return {name for name, src in sources.items() if src.get("workspace") is True}


def check_python(root: Path) -> Iterator[str]:
    members = _workspace_members(root)
    for path in _files(root, "pyproject.toml"):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        reqs: list[str] = list(data.get("project", {}).get("dependencies", []))
        for group in data.get("dependency-groups", {}).values():
            reqs.extend(r for r in group if isinstance(r, str))
        for extra in data.get("project", {}).get("optional-dependencies", {}).values():
            reqs.extend(extra)
        reqs.extend(data.get("build-system", {}).get("requires", []))
        for req in reqs:
            spec = req.replace(" ", "")
            if spec in members or PY_PIN.match(spec):
                continue
            yield f"{_rel(path, root)}: Python requirement not pinned with ==: {req!r}"


def check_node(root: Path) -> Iterator[str]:
    for path in _files(root, "package.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        rel = _rel(path, root)
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            for name, version in data.get(section, {}).items():
                if version == "workspace:*" or NODE_PIN.match(version):
                    continue
                yield f"{rel}: {section}.{name} is not an exact version: {version!r}"
        for name, version in data.get("peerDependencies", {}).items():
            yield f"{rel}: peerDependencies.{name} ({version!r}) is not allowed in an application"
        manager = data.get("packageManager")
        if manager is not None and not re.match(
            r"^pnpm@\d+\.\d+\.\d+\+sha512\.[0-9a-f]+$", manager
        ):
            yield f"{rel}: packageManager must be pnpm@X.Y.Z+sha512.<hash>: {manager!r}"
        node = data.get("engines", {}).get("node")
        if node is not None and not EXACT_VERSION.match(node):
            yield f"{rel}: engines.node must be an exact version: {node!r}"


def _dockerfile_violations(root: Path, path: Path) -> Iterator[str]:
    stages: set[str] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        words = line.split()
        if not words:
            continue
        rel = f"{_rel(path, root)}:{lineno}"
        instruction = words[0].upper()
        if instruction == "FROM":
            args = [w for w in words[1:] if not w.startswith("--")]
            image = args[0]
            if len(args) >= 3 and args[1].upper() == "AS":
                stages.add(args[2].lower())
            if image.lower() not in stages and image != "scratch" and not DIGEST.search(image):
                yield f"{rel}: base image not pinned by digest: {image}"
        elif instruction == "COPY":
            for word in words[1:]:
                source = word.removeprefix("--from=")
                if source != word and source.lower() not in stages and not DIGEST.search(source):
                    yield f"{rel}: COPY --from image not pinned by digest: {source}"


def check_images(root: Path) -> Iterator[str]:
    for path in [*_files(root, "Dockerfile"), *_files(root, "*.Dockerfile")]:
        yield from _dockerfile_violations(root, path)
    for path in [*_files(root, "compose*.yaml"), *_files(root, "compose*.yml")]:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"^\s*image:\s*['\"]?([^'\"\s#]+)", line)
            if match and not DIGEST.search(match.group(1)):
                yield f"{_rel(path, root)}:{lineno}: image not pinned by digest: {match[1]}"


def check_actions(root: Path) -> Iterator[str]:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return
    for path in sorted([*workflows.glob("*.yml"), *workflows.glob("*.yaml")]):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"^\s*(?:-\s*)?uses:\s*['\"]?([^'\"\s#]+)", line)
            if not match:
                continue
            ref = match.group(1)
            if ref.startswith("./") or (ref.startswith("docker://") and DIGEST.search(ref)):
                continue
            if not ACTION_SHA.match(ref):
                yield f"{_rel(path, root)}:{lineno}: action not pinned to a commit SHA: {ref}"


def check_runtimes(root: Path) -> Iterator[str]:
    for name in (".python-version", ".nvmrc"):
        path = root / name
        if path.exists() and not EXACT_VERSION.match(path.read_text(encoding="utf-8").strip()):
            yield f"{name}: must hold an exact X.Y.Z version"
    if (root / "pyproject.toml").exists() and not (root / "uv.lock").exists():
        yield "uv.lock is missing"
    if (root / "package.json").exists() and not (root / "pnpm-lock.yaml").exists():
        yield "pnpm-lock.yaml is missing"


def violations(root: Path) -> list[str]:
    checks = (check_python, check_node, check_images, check_actions, check_runtimes)
    return [v for check in checks for v in check(root)]


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    found = violations(root)
    for v in found:
        print(f"FF-04 {v}")
    print(f"FF-04 pins: {len(found)} violation(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
