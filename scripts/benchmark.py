"""Generate the benchmark project: 20,000 items in the fixture project's Markdown style (M0-04).

The capacity envelope (foundation, "Capacity envelope") is tested against this project from M2
(FF-14): the impact walk for a change touching about 500 items, and freshness reads. Items follow
the fixture project's files: a `# <ID> — <title>` heading, `Key: value · Key: value` metadata lines
naming related IDs, and `## AC-…` sections for criteria inside their requirement.

The output is deterministic for a seed. `manifest.json` records the counts per kind, the relation
counts, a SHA-256 over every file, the number of dangling references (always 0) and an impact probe:
the item whose change reaches closest to 500 items, for the FF-14 budget.

Usage: python -m scripts.benchmark OUT_DIR [--seed N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

TOTAL = 20_000
IMPACT_TARGET = 500
PROBE_KINDS = ("sdlc.feature", "sdlc.milestone", "sdlc.spec", "core.principle", "core.interface")
SPECS = 80
REQS_PER_SPEC = 40
ID_PATTERN = re.compile(
    r"\b(?:PRD|FEAT-\d+|M\d+(?:-\d+)?|SPEC-\d+|REQ-\d+|AC-\d+-\d+|DEC-\d+|TKT-\d+|ADR-\d+|P-\d+|IF-\d+|FND-\d+|LRN-\d+)\b"
)

WORDS = (  # noqa: SIM905 - a word list reads better as prose
    "account archive audit batch billing cache catalog channel checkout cohort config consent "
    "dashboard digest export feed filter forecast import index invoice journal ledger limit locale "
    "mailbox metric notice order payment pipeline plan profile quota queue rate receipt refund "
    "report retention review schedule search session settlement signal snapshot stream summary "
    "tenant ticket timeline token transfer upload usage vault webhook window workflow"
).split()


@dataclass
class Item:
    id: str
    kind: str
    title: str
    lines: list[str] = field(default_factory=lambda: [])
    refs: dict[str, list[str]] = field(default_factory=lambda: {})
    sections: list[tuple[str, str]] = field(default_factory=lambda: [])  # (criterion ID, body)


def _title(rng: random.Random, n: int = 3) -> str:
    return " ".join(rng.sample(WORDS, n)).capitalize()


def _criterion(rng: random.Random) -> str:
    method = rng.choice(["test", "test", "review", "measure"])
    given, when, then = (_title(rng, 2).lower() for _ in range(3))
    return f"Method: {method} · Required: yes\n\nGiven {given}, when {when}, then {then}."


def generate(seed: int = 20_000) -> dict[str, Item]:
    """Build the item graph in memory. Criteria live inside their requirement but count as items."""
    rng = random.Random(seed)  # noqa: S311 - test data, reproducible by design
    items: dict[str, Item] = {}

    def add(item: Item) -> Item:
        items[item.id] = item
        return item

    add(
        Item(
            "PRD",
            "sdlc.product",
            "Benchmark product",
            ["Goal: a project large enough to hold the capacity envelope."],
        )
    )
    principles = [add(Item(f"P-{i:02d}", "core.principle", _title(rng))).id for i in range(1, 31)]
    milestones = [add(Item(f"M{i}", "sdlc.milestone", _title(rng))).id for i in range(1, 7)]
    exits = [
        add(Item(f"{m}-{k:02d}", "sdlc.exit_criterion", _title(rng), refs={"Of": [m]})).id
        for m in milestones
        for k in range(1, 7)
    ]
    features = [
        add(
            Item(
                f"FEAT-{i}",
                "sdlc.feature",
                _title(rng),
                refs={"Derives from": ["PRD"], "Milestone": [rng.choice(milestones)]},
            )
        ).id
        for i in range(1, 41)
    ]
    interfaces = [add(Item(f"IF-{i}", "core.interface", _title(rng))).id for i in range(1, 201)]
    adrs: list[str] = []
    for i in range(1, 51):
        refs = {"Supersedes": [adrs[-1]]} if adrs and rng.random() < 0.2 else {}
        adrs.append(add(Item(f"ADR-{i:02d}", "sdlc.adr", _title(rng), refs=refs)).id)

    requirements: dict[int, list[str]] = {}
    for s in range(1, SPECS + 1):
        add(
            Item(f"SPEC-{s:02d}", "sdlc.spec", _title(rng), refs={"Delivers": rng.sample(exits, 2)})
        )
        feature = features[(s - 1) % len(features)]
        requirements[s] = []
        for x in range(1, REQS_PER_SPEC + 1):
            rid = f"REQ-{s:02d}{x:02d}"
            refs = {"Spec": [f"SPEC-{s:02d}"], "Derives from": [feature]}
            if rng.random() < 0.3:
                refs["Constrained by"] = [rng.choice(principles)]
            if rng.random() < 0.2:
                refs["Uses"] = [rng.choice(interfaces)]
            req = add(
                Item(
                    rid,
                    "sdlc.requirement",
                    _title(rng, 4),
                    [f"Priority: {rng.choice(['must', 'should', 'could'])}"],
                    refs,
                )
            )
            for k in range(1, rng.choice((2, 2, 3, 3, 3)) + 1):
                cid = f"AC-{s:02d}{x:02d}-{k}"
                req.sections.append(
                    (
                        cid,
                        _criterion(rng),
                    )
                )
                items[cid] = Item(
                    cid, "sdlc.criterion", f"Criterion {k} of {rid}", refs={"Verifies": [rid]}
                )
            requirements[s].append(rid)
        for d in range(1, 11):
            add(
                Item(
                    f"DEC-{s:02d}{d:02d}",
                    "sdlc.design_decision",
                    _title(rng),
                    refs={"Decides for": rng.sample(requirements[s], 2)},
                )
            )

    tickets: list[str] = []
    for n in range(1, 6001):
        s = rng.randint(1, SPECS)
        refs = {"Implements": rng.sample(requirements[s], rng.choice((1, 1, 2, 3)))}
        if tickets and rng.random() < 0.6:
            refs["After"] = rng.sample(
                tickets[-50:], min(len(tickets[-50:]), rng.choice((1, 1, 2)))
            )
        tickets.append(
            add(
                Item(
                    f"TKT-{n:04d}",
                    "sdlc.ticket",
                    _title(rng),
                    [f"Estimate: {rng.choice(['small', 'medium', 'large'])}"],
                    refs,
                )
            ).id
        )

    every = list(items)
    for n in range(1, 1001):
        add(
            Item(
                f"FND-{n}",
                "core.finding",
                _title(rng),
                [f"Severity: {rng.choice(['low', 'medium', 'high'])}"],
                {"Mentions": rng.sample(every, 2)},
            )
        )
    remaining = TOTAL - len(items)
    for n in range(1, remaining + 1):
        add(Item(f"LRN-{n}", "core.learning", _title(rng), refs={"About": [rng.choice(every)]}))
    return items


def render(item: Item) -> str:
    out = [f"# {item.id} — {item.title}", ""]
    meta = [f"{key}: {', '.join(ids)}" for key, ids in item.refs.items()] + item.lines
    if meta:
        out += [" · ".join(meta), ""]
    for cid, body in item.sections:
        out += [f"## {cid}", body, ""]
    return "\n".join(out)


def impact(items: dict[str, Item]) -> dict[str, int]:
    """For each probe candidate, how many items its change reaches through references."""
    referenced_by: dict[str, set[str]] = defaultdict(set)
    for item in items.values():
        for ids in item.refs.values():
            for target in ids:
                referenced_by[target].add(item.id)
    reach: dict[str, int] = {}
    for fid in (i.id for i in items.values() if i.kind in PROBE_KINDS):
        seen, queue = {fid}, deque([fid])
        while queue:
            for nxt in referenced_by[queue.popleft()] - seen:
                if items[nxt].kind not in (
                    "core.finding",
                    "core.learning",
                ):  # mentions do not propagate
                    seen.add(nxt)
                    queue.append(nxt)
        reach[fid] = len(seen) - 1
    return reach


def write(items: dict[str, Item], out: Path, seed: int) -> dict[str, object]:
    files: dict[str, str] = {}
    for item in items.values():
        if item.kind == "sdlc.criterion":
            continue  # rendered inside its requirement
        folder = item.kind.split(".")[1]
        files[f"{folder}/{item.id}.md"] = render(item)
    digest = hashlib.sha256()
    for path in sorted(files):
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(files[path], encoding="utf-8")
        digest.update(path.encode() + b"\0" + files[path].encode() + b"\0")
    mentioned = {m for text in files.values() for m in ID_PATTERN.findall(text)}
    reach = impact(items)
    probe = min(reach, key=lambda f: (abs(reach[f] - IMPACT_TARGET), f))
    kinds: dict[str, int] = defaultdict(int)
    relations: dict[str, int] = defaultdict(int)
    for item in items.values():
        kinds[item.kind] += 1
        for key, ids in item.refs.items():
            relations[key] += len(ids)
    manifest: dict[str, object] = {
        "seed": seed,
        "items": len(items),
        "files": len(files),
        "kinds": dict(sorted(kinds.items())),
        "relations": dict(sorted(relations.items())),
        "dangling_references": len(mentioned - set(items)),
        "impact_probe": {"item": probe, "reaches": reach[probe], "target": IMPACT_TARGET},
        "sha256": digest.hexdigest(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.benchmark", description=(__doc__ or "").splitlines()[0]
    )
    parser.add_argument("out", type=Path)
    parser.add_argument("--seed", type=int, default=20_000)
    args = parser.parse_args(argv)
    out: Path = args.out
    seed: int = args.seed
    manifest = write(generate(seed), out, seed)
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["dangling_references"] == 0 and manifest["items"] == TOTAL else 1


if __name__ == "__main__":
    raise SystemExit(main())
