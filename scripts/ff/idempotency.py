"""FF-10: idempotency coverage of external steps (SPEC-02, REQ-0204, REQ-0213).

It reads the source, without importing it. Every function decorated
`@external_step("<name>", ...)` or `@<x>.external_step("<name>", ...)` under
the kernel's and the factories' `src/` is a registered external step. The
check fails when a step
- has a name that is not a string literal, or one registered twice;
- has no idempotency key: its first parameter is not annotated
  `IdempotencyKey`, or its body never uses that parameter, so the key cannot
  reach the target;
- has no crash-and-resume test: no `crash_scenario("<name>", ...)` in the
  tests (`tests/`, `packages/*/tests/`, `factories/*/tests/`) names it. The
  crash matrix runs every such scenario at every kill point of its step.

Usage: python -m scripts.ff.idempotency [ROOT]
"""

import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

SOURCE_ROOTS = ("packages/grindstone/src", "factories/*/src")
TEST_ROOTS = ("tests", "packages/*/tests", "factories/*/tests")
DECORATOR = "external_step"
KEY_TYPE = "IdempotencyKey"
SCENARIO = "crash_scenario"

type FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class Step:
    """An external step as the source declares it."""

    name: str | None
    path: str
    line: int
    keyed: bool


def _python_files(root: Path, patterns: tuple[str, ...]) -> Iterator[Path]:
    seen: set[Path] = set()
    for pattern in patterns:
        for base in sorted(root.glob(pattern)):
            for path in sorted(base.rglob("*.py")):
                parts = path.relative_to(root).parts
                if path in seen or "fixtures" in parts or "node_modules" in parts:
                    continue
                seen.add(path)
                yield path


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _called_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _first_string(call: ast.Call, keyword: str) -> str | None:
    """The call's first positional argument, or its `keyword` argument, if a string literal."""
    values = [*call.args[:1], *(k.value for k in call.keywords if k.arg == keyword)]
    for value in values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
    return None


def _is_key_annotation(node: ast.expr | None) -> bool:
    if isinstance(node, ast.Constant):
        return node.value == KEY_TYPE
    return node is not None and _called_name(node) == KEY_TYPE


def _keyed(func: FunctionNode) -> bool:
    """Whether the first parameter is the key and the body uses it."""
    params = [*func.args.posonlyargs, *func.args.args]
    if not params or not _is_key_annotation(params[0].annotation):
        return False
    key = params[0].arg
    return any(
        isinstance(n, ast.Name) and n.id == key and isinstance(n.ctx, ast.Load)
        for statement in func.body
        for n in ast.walk(statement)
    )


def external_steps(root: Path) -> list[Step]:
    """Every external step the source under `root` registers."""
    found: list[Step] = []
    for path in _python_files(root, SOURCE_ROOTS):
        for func in ast.walk(_parse(path)):
            if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            found.extend(
                Step(
                    name=_first_string(deco, "name"),
                    path=path.relative_to(root).as_posix(),
                    line=func.lineno,
                    keyed=_keyed(func),
                )
                for deco in func.decorator_list
                if isinstance(deco, ast.Call) and _called_name(deco.func) == DECORATOR
            )
    return found


def crash_tested(root: Path) -> set[str]:
    """The steps a `crash_scenario("<name>", ...)` in the tests names."""
    named: set[str] = set()
    for path in _python_files(root, TEST_ROOTS):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Call) and _called_name(node.func) == SCENARIO:
                step = _first_string(node, "step")
                if step is not None:
                    named.add(step)
    return named


def violations(root: Path) -> list[str]:
    steps = external_steps(root)
    tested = crash_tested(root)
    found: list[str] = []
    seen: set[str] = set()
    for step in steps:
        where = f"{step.path}:{step.line}"
        if step.name is None:
            found.append(f"{where}: an external step's name is not a string literal")
            continue
        if step.name in seen:
            found.append(f"{where}: external step {step.name!r} is registered twice")
        seen.add(step.name)
        if not step.keyed:
            found.append(
                f"{where}: external step {step.name!r} has no idempotency key: its first "
                f"parameter must be an `{KEY_TYPE}` that the step hands to its target"
            )
        if step.name not in tested:
            found.append(
                f"{where}: external step {step.name!r} has no crash-and-resume test: "
                f'declare `{SCENARIO}("{step.name}", ...)` under tests/crash/scenarios/'
            )
    return found


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    found = violations(root)
    for v in found:
        print(f"FF-10 {v}")
    steps = len(external_steps(root))
    print(f"FF-10 idempotency coverage: {steps} step(s), {len(found)} violation(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
