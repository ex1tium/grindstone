"""FF-13: traceability over the documentation (Planning playbook).

Fails when
- a document cites a foundation identifier that is not defined,
- an exit criterion of M1-M5 is delivered by no specification in the spec map,
- a specification, or the spec map's Cites column, cites a superseded decision record,
- a specification marked `implemented` has an acceptance criterion no test names.

Foundation identifiers are defined only in `docs/foundation/`; specifications
in `docs/specs/` define their own REQ/AC/DEC/TKT items, which are checked
for duplicates.

Usage: python -m scripts.ff.traceability [ROOT]
"""

import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

DEFINITIONS = [
    re.compile(r"^\| (I-\d{2}) \|", re.M),
    re.compile(r"^\| (QG-\d) \|", re.M),
    re.compile(r"^\| (QS-\d{2}) \|", re.M),
    re.compile(r"^\| (FF-\d{2}) \|", re.M),
    re.compile(r"^#### (ADR-\d{2}) —", re.M),
    re.compile(r"^### (M\d) —", re.M),
    re.compile(r"^- \[[ x]\] (M\d-\d{2}):", re.M),
    re.compile(r"^\| (SPK-\d) ", re.M),
    re.compile(r"^\| (Q-\d{1,2}) \|", re.M),
    re.compile(r"^\| (SPEC-\d{2}) \|", re.M),
    re.compile(r"^### ([KS]\d) —", re.M),
    re.compile(r"^\| (R\d) —", re.M),
]

# Longest alternatives first so `M1-04` is not read as `M1`.
REFERENCE = re.compile(
    r"(?<![\w-])(QG-\d|QS-\d{2}|FF-\d{2}|ADR-\d{2}|SPK-\d|SPEC-\d{2}|M\d-\d{2}|I-\d{2}|Q-\d{1,2}|M\d|[KSR]\d)(?![\w-])"
)
SUPERSEDED = re.compile(r"^#### (ADR-\d{2}) —[^\n]*\n\n\*\*Status\.\*\* Superseded by", re.M)
SPEC_STATUS = re.compile(r"^Status:\s*(\w[\w ]*?)\s*(?:·|$)", re.M)
SPEC_AC = re.compile(r"^(AC-\d{4}-\d+):", re.M)
TEST_DIRS = ("tests", "packages", "factories", "runner", "agent-host")
TEST_SUFFIXES = {".py", ".ts"}


@dataclass
class Foundation:
    defined: set[str] = field(default_factory=set[str])
    superseded: set[str] = field(default_factory=set[str])
    exit_criteria: set[str] = field(default_factory=set[str])
    delivered: set[str] = field(default_factory=set[str])
    spec_map_cites: dict[str, set[str]] = field(default_factory=dict[str, set[str]])


def _strip_code(text: str) -> str:
    """Drop fenced code blocks: templates there use placeholder IDs."""
    return re.sub(r"^```.*?^```", "", text, flags=re.M | re.S)


def read_foundation(root: Path) -> Foundation:
    f = Foundation()
    for path in sorted((root / "docs" / "foundation").glob("*.md")):
        text = path.read_text()
        for pattern in DEFINITIONS:
            f.defined.update(pattern.findall(text))
        f.superseded.update(m.group(1) for m in SUPERSEDED.finditer(text))
        f.exit_criteria.update(re.findall(r"^- \[[ x]\] (M[1-5]-\d{2}):", text, re.M))
        for row in re.finditer(r"^\| (SPEC-\d{2}) \|(.*)$", text, re.M):
            cells = [c.strip() for c in row.group(2).split("|")]
            # Columns after the ID: Title | Kind | Owns | Delivers | Cites
            if len(cells) >= 5:
                f.delivered.update(re.findall(r"M\d-\d{2}", cells[3]))
                f.spec_map_cites[row.group(1)] = set(re.findall(r"ADR-\d{2}", cells[4]))
    return f


def _documents(root: Path) -> Iterator[Path]:
    readme = root / "README.md"
    if readme.exists():
        yield readme
    docs = root / "docs"
    if docs.is_dir():
        yield from sorted(docs.rglob("*.md"))


def _tests_text(root: Path) -> str:
    chunks: list[str] = []
    for d in TEST_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            parts = path.relative_to(root).parts
            if "node_modules" in parts or ".venv" in parts:
                continue
            if path.suffix in TEST_SUFFIXES and "test" in path.name:
                chunks.append(path.read_text(errors="replace"))
    return "\n".join(chunks)


def _undefined_references(root: Path, f: Foundation) -> Iterator[str]:
    for path in _documents(root):
        rel = path.relative_to(root)
        for lineno, line in enumerate(_strip_code(path.read_text()).splitlines(), 1):
            for ref in REFERENCE.findall(line):
                if ref not in f.defined:
                    yield f"{rel}:{lineno}: cites undefined identifier {ref}"


def _spec_map_gaps(f: Foundation) -> Iterator[str]:
    for criterion in sorted(f.exit_criteria - f.delivered):
        yield f"spec map: exit criterion {criterion} is delivered by no specification"
    for spec, cites in sorted(f.spec_map_cites.items()):
        for adr in sorted(cites & f.superseded):
            yield f"spec map: {spec} cites superseded {adr}"


def _specification_gaps(root: Path, f: Foundation) -> Iterator[str]:
    specs_dir = root / "docs" / "specs"
    if not specs_dir.is_dir():
        return
    seen_items: dict[str, Path] = {}
    tests: str | None = None
    for path in sorted(specs_dir.glob("SPEC-*.md")):
        rel = path.relative_to(root)
        text = _strip_code(path.read_text())
        for adr in sorted(set(re.findall(r"ADR-\d{2}", text)) & f.superseded):
            yield f"{rel}: cites superseded {adr}"
        for item in re.findall(r"^((?:REQ|AC|DEC|TKT|SCN|NG|OQ)-[\d-]+):", text, re.M):
            if item in seen_items:
                yield f"{rel}: {item} already defined in {seen_items[item]}"
            seen_items[item] = rel
        status = SPEC_STATUS.search(text)
        if status and status.group(1).strip() == "implemented":
            tests = _tests_text(root) if tests is None else tests
            for ac in SPEC_AC.findall(text):
                if ac not in tests:
                    yield f"{rel}: {ac} has no test naming it"


def violations(root: Path) -> list[str]:
    f = read_foundation(root)
    if not f.defined:
        return ["no foundation identifiers found under docs/foundation/"]
    return [
        *_undefined_references(root, f),
        *_spec_map_gaps(f),
        *_specification_gaps(root, f),
    ]


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    found = violations(root)
    for v in found:
        print(f"FF-13 {v}")
    print(f"FF-13 traceability: {len(found)} violation(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
