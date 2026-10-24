"""FF-03: schema compatibility of the contract bundle (ADR-05, REQ-0114).

Diffs the committed bundle `packages/contracts-ts/schemas/contracts.schema.json`
against the base branch's, model by model, and classifies every change:

- compatible: a new model, a new optional or defaulted field, a new enum member
  (or a new member of a union or discriminator mapping: a new kind);
- breaking: a field removed or renamed, a type narrowed or changed, a field made
  required, an enum member removed, a semantic field's default changed, a field
  moved between semantic and presentation, a versioned model removed.

A breaking change passes only if the model's `schema_version` literal rose and
`docs/upgrades.md` has an entry `## <Model> v<N>` for the new version (`## <Model>
removed` for a removed model). A change that alters what hashes mean (a semantic
default, or a move between semantic and presentation) also needs a
`**Stored hashes.**` paragraph in that entry. A breaking change inside a model
without `schema_version` (an enum, a nested record) is charged to every versioned
model that references it.

The base is `--base REF` if given, else `origin/$GITHUB_BASE_REF` (set on pull
requests in CI), else `origin/main`. A model absent from the base, or a base
without a bundle, is new and compatible.

Usage: python -m scripts.ff.schema_compat [--base REF] [ROOT]
"""

import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import cast

BUNDLE = "packages/contracts-ts/schemas/contracts.schema.json"
UPGRADES = "docs/upgrades.md"
VERSION_FIELD = "schema_version"
HASH_NOTE = "**Stored hashes.**"
# Keywords that describe a schema without constraining its values.
ANNOTATIONS = frozenset({"description", "title", "examples", "$comment", "deprecated", "default"})
# Model-level keys compared field by field rather than as a whole.
MODEL_FIELDS = frozenset({"properties", "required"})
ENTRY = re.compile(r"^##\s+(\w+)\s+(?:v(\d+)|(removed))\s*$", re.M)
REF = re.compile(r"^#/\$defs/(.+)$")

type Schema = Mapping[str, object]


class Verdict(IntEnum):
    SAME = 0
    COMPATIBLE = 1
    BREAKING = 2


@dataclass(frozen=True)
class Change:
    model: str
    what: str
    affects_hashes: bool = False


def _schema(value: object) -> Schema:
    return cast(Schema, value) if isinstance(value, Mapping) else {}


def _defs(bundle: Schema | None) -> dict[str, Schema]:
    if bundle is None:
        return {}
    return {name: _schema(d) for name, d in _schema(bundle.get("$defs")).items()}


def _properties(model: Schema) -> dict[str, Schema]:
    return {name: _schema(p) for name, p in _schema(model.get("properties")).items()}


def _required(model: Schema) -> set[str]:
    value = model.get("required")
    return {str(r) for r in cast(Sequence[object], value)} if isinstance(value, list) else set()


def _version(model: Schema) -> int | None:
    prop = _properties(model).get(VERSION_FIELD)
    if prop is None:
        return None
    value = prop.get("const", prop.get("default"))
    return value if isinstance(value, int) else None


def _is_presentation(prop: Schema) -> bool:
    """Whether a field is presentation, so outside the semantic hash.

    No field carries a mark yet: `Presentation` arrives with TKT-0103, and the
    marker it writes into the generated schema is read here once it exists.
    Until then every field is semantic, as an unmarked field is.
    """
    del prop
    return False


def _strip(value: object) -> object:
    """A schema without annotations, for equality; property names are kept."""
    if isinstance(value, Mapping):
        items = cast(Schema, value)
        return {
            k: ({n: _strip(p) for n, p in _schema(v).items()} if k == "properties" else _strip(v))
            for k, v in items.items()
            if k not in ANNOTATIONS
        }
    if isinstance(value, list):
        return [_strip(v) for v in cast(list[object], value)]
    return value


def _grows(base: Sequence[object], head: Sequence[object]) -> Verdict:
    """SAME if equal, COMPATIBLE if head only adds members, else BREAKING."""
    if list(base) == list(head):
        return Verdict.SAME
    return Verdict.COMPATIBLE if all(b in head for b in base) else Verdict.BREAKING


def _compare(base: object, head: object) -> Verdict:
    """Compare two schemas for the values they admit, ignoring annotations."""
    if isinstance(base, Mapping) and isinstance(head, Mapping):
        b = {k: v for k, v in cast(Schema, base).items() if k not in ANNOTATIONS}
        h = {k: v for k, v in cast(Schema, head).items() if k not in ANNOTATIONS}
        if b.keys() != h.keys():
            return Verdict.BREAKING
        return max((_compare_key(k, v, h[k]) for k, v in b.items()), default=Verdict.SAME)
    if isinstance(base, list) and isinstance(head, list):
        bl, hl = cast(list[object], base), cast(list[object], head)
        if len(bl) != len(hl):
            return Verdict.BREAKING
        return max((_compare(x, y) for x, y in zip(bl, hl, strict=True)), default=Verdict.SAME)
    return Verdict.SAME if base == head else Verdict.BREAKING


def _compare_key(key: str, base: object, head: object) -> Verdict:
    """Compare one keyword's values; membership keywords may grow compatibly."""
    lists = _as_list(base), _as_list(head)
    match key, lists:
        case "enum", (list() as b, list() as h):
            return _grows(b, h)
        case "anyOf" | "oneOf", (list() as b, list() as h):
            return _union(b, h)
        case "mapping", _:
            return _grows(sorted(_schema(base).items()), sorted(_schema(head).items()))
        case "properties", _:
            return _compare_named(_schema(base), _schema(head))
        case _:
            return _compare(base, head)


def _as_list(value: object) -> list[object] | None:
    return cast(list[object], value) if isinstance(value, list) else None


def _compare_named(base: Schema, head: Schema) -> Verdict:
    if base.keys() != head.keys():
        return Verdict.BREAKING
    return max((_compare(v, head[k]) for k, v in base.items()), default=Verdict.SAME)


def _union(base: list[object], head: list[object]) -> Verdict:
    if len(base) == len(head):
        return max((_compare(x, y) for x, y in zip(base, head, strict=True)), default=Verdict.SAME)
    return _grows([_strip(b) for b in base], [_strip(h) for h in head])


def _field_changes(model: str, base: Schema, head: Schema) -> Iterator[Change]:
    base_props, head_props = _properties(base), _properties(head)
    base_req, head_req = _required(base), _required(head)
    for name in sorted(base_props.keys() - head_props.keys()):
        yield Change(model, f"field `{name}` removed")
    for name in sorted(head_props.keys() - base_props.keys()):
        if name in head_req and "default" not in head_props[name]:
            yield Change(model, f"required field `{name}` added")
    for name in sorted(base_props.keys() & head_props.keys()):
        if name == VERSION_FIELD:
            continue
        bp, hp = base_props[name], head_props[name]
        if _compare(bp, hp) is Verdict.BREAKING:
            yield Change(model, f"field `{name}` type changed")
        if _is_presentation(bp) != _is_presentation(hp):
            yield Change(
                model,
                f"field `{name}` moved between semantic and presentation",
                affects_hashes=True,
            )
            continue
        semantic = not _is_presentation(hp)
        base_optional = "default" in bp or name not in base_req
        head_optional = "default" in hp or name not in head_req
        if base_optional and not head_optional:
            yield Change(
                model, f"field `{name}` made required", affects_hashes=semantic and "default" in bp
            )
        elif (
            semantic and "default" in hp and ("default" not in bp or bp["default"] != hp["default"])
        ):
            yield Change(model, f"semantic field `{name}` default changed", affects_hashes=True)


def _model_changes(model: str, base: Schema, head: Schema) -> Iterator[Change]:
    if "properties" in base or "properties" in head:
        outer_base = {k: v for k, v in base.items() if k not in MODEL_FIELDS}
        outer_head = {k: v for k, v in head.items() if k not in MODEL_FIELDS}
        if _compare(outer_base, outer_head) is Verdict.BREAKING:
            yield Change(model, "model shape changed")
        yield from _field_changes(model, base, head)
    elif _compare(base, head) is Verdict.BREAKING:
        yield Change(model, "definition changed (an enum member removed or a type changed)")


def _references(schema: object) -> Iterator[str]:
    if isinstance(schema, Mapping):
        for key, value in cast(Schema, schema).items():
            if key == "$ref" and isinstance(value, str) and (m := REF.match(value)):
                yield m.group(1)
            else:
                yield from _references(value)
    elif isinstance(schema, list):
        for value in cast(list[object], schema):
            yield from _references(value)


def _owners(name: str, defs: Mapping[str, Schema]) -> list[str]:
    """The versioned models that reference `name`, directly or through unversioned ones."""
    users: dict[str, set[str]] = {n: set() for n in defs}
    for user, schema in defs.items():
        for used in _references(schema):
            users.setdefault(used, set()).add(user)
    seen: set[str] = set()
    todo = [name]
    while todo:
        for user in users.get(todo.pop(), set()):
            if user not in seen:
                seen.add(user)
                if _version(defs[user]) is None:
                    todo.append(user)
    return sorted(u for u in seen if _version(defs[u]) is not None)


def _entries(upgrades: str) -> dict[tuple[str, str], str]:
    """Upgrade entries keyed by (model, version or "removed"), with their bodies."""
    found: dict[tuple[str, str], str] = {}
    matches = list(ENTRY.finditer(upgrades))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(upgrades)
        body = upgrades[m.end() : end].split("\n## ", 1)[0]
        found[m.group(1), m.group(2) or "removed"] = body
    return found


def classify(base: Schema | None, head: Schema) -> list[Change]:
    """Every breaking change, charged to the versioned model that must be raised."""
    base_defs, head_defs = _defs(base), _defs(head)
    changes = [
        Change(name, "model removed")
        for name in sorted(base_defs.keys() - head_defs.keys())
        if _version(base_defs[name]) is not None
    ]
    for name in sorted(base_defs.keys() & head_defs.keys()):
        found = list(_model_changes(name, base_defs[name], head_defs[name]))
        if not found or _version(head_defs[name]) is not None:
            changes.extend(found)
            continue
        users = _owners(name, head_defs)
        # A model new in this change has no stored data to keep readable.
        owners = [o for o in users if o in base_defs]
        if not users:
            changes.extend(Change(c.model, f"{c.what}; no versioned model uses it") for c in found)
        for owner in owners:
            changes.extend(Change(owner, f"`{name}`: {c.what}", c.affects_hashes) for c in found)
    return changes


def violations(base: Schema | None, head: Schema, upgrades: str) -> list[str]:
    base_defs, head_defs = _defs(base), _defs(head)
    entries = _entries(upgrades)
    found: list[str] = []
    for change in classify(base, head):
        model = change.model
        prefix = f"{model}: {change.what}"
        if model not in head_defs:
            if (model, "removed") not in entries:
                found.append(f"{prefix}; {UPGRADES} has no `## {model} removed` entry")
            continue
        if model not in base_defs or _version(head_defs[model]) is None:
            found.append(f"{prefix}; breaking, and there is no schema_version to raise")
            continue
        old, new = _version(base_defs[model]) or 0, _version(head_defs[model]) or 0
        if new <= old:
            found.append(f"{prefix}; breaking without raising schema_version (still {new})")
            continue
        body = entries.get((model, str(new)))
        if body is None:
            found.append(f"{prefix}; {UPGRADES} has no `## {model} v{new}` entry")
        elif change.affects_hashes and HASH_NOTE not in body:
            found.append(
                f"{prefix}; the `## {model} v{new}` entry must say how stored hashes are "
                f"treated (a {HASH_NOTE} paragraph)"
            )
    return found


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )


def base_bundle(root: Path, ref: str) -> Schema | None:
    """The bundle where HEAD forked from `ref`, or None when that commit has none."""
    if _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
        raise LookupError(f"base ref {ref!r} not found: fetch it or pass --base")
    # Diff against where this branch left the base, so later base commits are
    # not read as changes made here (in CI the checkout is already the merge).
    fork = _git(root, "merge-base", "HEAD", ref)
    commit = fork.stdout.strip() if fork.returncode == 0 else ref
    shown = _git(root, "show", f"{commit}:{BUNDLE}")
    if shown.returncode != 0:
        return None
    return _schema(json.loads(shown.stdout))


def default_base() -> str:
    target = os.environ.get("GITHUB_BASE_REF")
    return f"origin/{target}" if target else "origin/main"


def main(argv: list[str]) -> int:
    args = argv[1:]
    ref = default_base()
    if len(args) >= 2 and args[0] == "--base":
        ref, args = args[1], args[2:]
    root = Path(args[0]).resolve() if args else Path.cwd()
    try:
        base = base_bundle(root, ref)
    except LookupError as e:
        print(f"FF-03 {e}")
        return 1
    head = _schema(json.loads((root / BUNDLE).read_text(encoding="utf-8")))
    upgrades_path = root / UPGRADES
    upgrades = upgrades_path.read_text(encoding="utf-8") if upgrades_path.exists() else ""
    found = violations(base, head, upgrades)
    for v in found:
        print(f"FF-03 {v}")
    print(f"FF-03 schema compatibility against {ref}: {len(found)} violation(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
