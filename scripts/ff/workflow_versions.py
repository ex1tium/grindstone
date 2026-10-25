"""Workflow-version check: a changed workflow needs a new version or an upgrade note.

DBOS replays a recovered workflow against its recorded steps, so a change to
a workflow's code can break the workflows already in flight. SPEC-02 keeps one
explicit `WORKFLOW_VERSION` (DEC-0204, REQ-0208); this check makes it rise
when it must.

It reads the source, without importing it: every function decorated
`@workflow("<name>")` or `@store.workflow("<name>")` under the kernel's and the
factories' `src/` is a registered workflow. Its fingerprint is a SHA-256 over
its syntax tree (docstrings, comments and layout ignored) and over the trees
of the functions it calls by name, defined in the same module or imported
from another scanned one: the steps it runs. The fingerprints and the version
are recorded in `packages/grindstone/workflow-versions.json`.

The check fails when
- the record is not what the source gives (run with `--write` and commit it);
- against the base branch's record, a workflow's fingerprint changed, or a
  workflow was removed, while `WORKFLOW_VERSION` did not rise, unless
  `docs/upgrades.md` has an entry saying the change is replay-compatible:
  `## Workflow <name> <first 12 hex digits of the new fingerprint>`, or
  `## Workflow <name> removed`;
- `WORKFLOW_VERSION` went down.

Compatible means steps were only added after every existing step, none removed
or reordered. Anything else raises the version, and the operator drains or
forks the workflows in flight.

The base is `--base REF` if given, else `origin/$GITHUB_BASE_REF`, else
`origin/main`, as for FF-03. A base without a record has no workflows.

Usage: python -m scripts.ff.workflow_versions [--base REF] [--write] [ROOT]
"""

import ast
import copy
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from scripts.ff.schema_compat import default_base

RECORD = "packages/grindstone/workflow-versions.json"
UPGRADES = "docs/upgrades.md"
VERSION_SOURCE = "packages/grindstone/src/grindstone/store/runtime.py"
VERSION_NAME = "WORKFLOW_VERSION"
SOURCE_ROOTS = ("packages/grindstone/src", "factories/*/src")
ENTRY = re.compile(r"^##\s+Workflow\s+(\S+)\s+([0-9a-f]{12}|removed)\s*$", re.M)
PREFIX = 12

type FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class Record:
    """The workflow version and each registered workflow's fingerprint."""

    version: str
    workflows: Mapping[str, str] = field(default_factory=dict[str, str])

    def to_json(self) -> str:
        data = {"workflow_version": self.version, "workflows": dict(sorted(self.workflows.items()))}
        return json.dumps(data, indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Record:
        data = cast(dict[str, object], json.loads(text))
        workflows = cast(dict[str, str], data.get("workflows", {}))
        return cls(version=str(data["workflow_version"]), workflows=workflows)


@dataclass
class _Module:
    name: str
    tree: ast.Module
    functions: dict[str, FunctionNode]
    imports: dict[str, tuple[str, str]]  # local name -> (module, name)


def _modules(root: Path) -> dict[str, _Module]:
    found: dict[str, _Module] = {}
    for pattern in SOURCE_ROOTS:
        for src in sorted(root.glob(pattern)):
            for path in sorted(src.rglob("*.py")):
                parts = path.relative_to(src).with_suffix("").parts
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                name = ".".join(parts)
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                package = name if path.name == "__init__.py" else name.rpartition(".")[0]
                found[name] = _Module(
                    name=name,
                    tree=tree,
                    functions={
                        n.name: n
                        for n in tree.body
                        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
                    },
                    imports=dict(_imports(tree, package)),
                )
    return found


def _imports(tree: ast.Module, package: str) -> Iterator[tuple[str, tuple[str, str]]]:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        base = node.module or ""
        if node.level:
            anchor = package.split(".")[: len(package.split(".")) - node.level + 1]
            base = ".".join([*anchor, *([base] if base else [])])
        for alias in node.names:
            yield alias.asname or alias.name, (base, alias.name)


def _registered_name(func: FunctionNode) -> str | None:
    """The name in `@workflow("<name>")` or `@<x>.workflow("<name>")`, not `@DBOS.workflow`."""
    for deco in func.decorator_list:
        if not isinstance(deco, ast.Call) or not deco.args:
            continue
        target, first = deco.func, deco.args[0]
        named = (isinstance(target, ast.Name) and target.id == "workflow") or (
            isinstance(target, ast.Attribute)
            and target.attr == "workflow"
            and not (isinstance(target.value, ast.Name) and target.value.id == "DBOS")
        )
        if named and isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return None


def _normalized(func: FunctionNode) -> str:
    """The function's syntax tree without its own name or docstring."""
    node = copy.deepcopy(func)
    node.name = ""
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        node.body = body[1:] or [ast.Pass()]
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def _callees(func: FunctionNode, module: _Module, modules: Mapping[str, _Module]) -> dict[str, str]:
    called = {
        n.func.id
        for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    trees: dict[str, str] = {}
    for name in sorted(called):
        target: FunctionNode | None = module.functions.get(name)
        if target is None and name in module.imports:
            source, original = module.imports[name]
            other = modules.get(source)
            target = other.functions.get(original) if other else None
        if target is not None and target is not func:
            trees[name] = _normalized(target)
    return trees


def fingerprint(func: FunctionNode, module: _Module, modules: Mapping[str, _Module]) -> str:
    digest = hashlib.sha256(_normalized(func).encode())
    for name, tree in _callees(func, module, modules).items():
        digest.update(f"\0{name}\0{tree}".encode())
    return digest.hexdigest()


def read_version(root: Path) -> str:
    tree = ast.parse((root / VERSION_SOURCE).read_text(encoding="utf-8"))
    for node in tree.body:
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, ast.AnnAssign)
            else []
        )
        value = getattr(node, "value", None)
        for t in targets:
            if (
                isinstance(t, ast.Name)
                and t.id == VERSION_NAME
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                return value.value
    raise LookupError(f"{VERSION_SOURCE} defines no string {VERSION_NAME}")


def scan(root: Path) -> Record:
    """The record the source under `root` gives."""
    modules = _modules(root)
    workflows: dict[str, str] = {}
    for module in modules.values():
        for func in module.functions.values():
            name = _registered_name(func)
            if name is None:
                continue
            if name in workflows:
                raise ValueError(f"workflow {name!r} is registered twice")
            workflows[name] = fingerprint(func, module, modules)
    return Record(version=read_version(root), workflows=workflows)


def _rose(old: str, new: str) -> bool | None:
    """True if the version rose, False if it fell, None if unchanged."""
    if old == new:
        return None
    if old.isdigit() and new.isdigit():
        return int(new) > int(old)
    return True


def violations(base: Record | None, head: Record, upgrades: str) -> list[str]:
    if base is None:
        return []
    rose = _rose(base.version, head.version)
    if rose is False:
        return [f"{VERSION_NAME} went down from {base.version} to {head.version}; it only rises"]
    if rose:
        return []
    entries = {(m.group(1), m.group(2)) for m in ENTRY.finditer(upgrades)}
    found: list[str] = []
    for name, old in sorted(base.workflows.items()):
        new = head.workflows.get(name)
        if new == old:
            continue
        mark = "removed" if new is None else new[:PREFIX]
        if (name, mark) in entries:
            continue
        what = "removed" if new is None else "changed"
        found.append(
            f"workflow {name!r} {what} while {VERSION_NAME} stayed {head.version}: raise it, "
            f"or add `## Workflow {name} {mark}` to {UPGRADES} if the change is replay-compatible"
        )
    return found


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )


def base_record(root: Path, ref: str) -> Record | None:
    """The record where HEAD forked from `ref`, or None when that commit has none."""
    if _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
        raise LookupError(f"base ref {ref!r} not found: fetch it or pass --base")
    fork = _git(root, "merge-base", "HEAD", ref)
    commit = fork.stdout.strip() if fork.returncode == 0 else ref
    shown = _git(root, "show", f"{commit}:{RECORD}")
    return Record.from_json(shown.stdout) if shown.returncode == 0 else None


def main(argv: list[str]) -> int:
    args = argv[1:]
    ref = default_base()
    write = "--write" in args
    args = [a for a in args if a != "--write"]
    if len(args) >= 2 and args[0] == "--base":
        ref, args = args[1], args[2:]
    root = Path(args[0]).resolve() if args else Path.cwd()
    head = scan(root)
    record_path = root / RECORD
    if write:
        record_path.write_text(head.to_json(), encoding="utf-8", newline="\n")
        print(f"wrote {RECORD}: {len(head.workflows)} workflow(s), version {head.version}")
        return 0
    found: list[str] = []
    committed = record_path.read_text(encoding="utf-8") if record_path.exists() else ""
    if committed != head.to_json():
        found.append(
            f"{RECORD} is not what the source gives: "
            "run `python -m scripts.ff.workflow_versions --write` and commit it"
        )
    try:
        base = base_record(root, ref)
    except LookupError as e:
        found.append(str(e))
        base = None
    upgrades_path = root / UPGRADES
    upgrades = upgrades_path.read_text(encoding="utf-8") if upgrades_path.exists() else ""
    found += violations(base, head, upgrades)
    for v in found:
        print(f"workflow versions: {v}")
    print(f"workflow versions against {ref}: {len(found)} violation(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
