"""The impact walk, one round (SPEC-04, REQ-0411, DEC-0402).

The changed items are those whose proposed semantic hash differs from the
base they are walked against; creations count as changed. For each, every
current item outside the ChangeSet with an edge to it is listed: sources of
`review` edges are `reached` and need a verdict, sources of `notify` and
`render` edges are `informed` and need none (ADR-09). An edge type no loaded
factory declares is treated as `review`, the safe reading.

M1 accepts only `unaffected` verdicts, so no verdict amends the ChangeSet
and one round is a fixed point once every reached item has one with a
reason.
"""

from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass

from grindstone.contracts.change import ItemBase, Reached, Verdict, WalkResult
from grindstone.contracts.ids import ItemId, ProjectId
from grindstone.contracts.intent import Edge
from grindstone.contracts.platform import Impact
from grindstone.contracts.refs import SemanticHash
from grindstone.intent import Materialised, edges_to
from grindstone.store import Uow

type Impacts = Mapping[str, Impact]
"""Each registered edge type's impact."""


def reach(
    changed: Iterable[ItemId],
    edges_into: Callable[[ItemId], Iterable[Edge]],
    impacts: Impacts,
    in_changeset: Collection[ItemId],
) -> tuple[tuple[Reached, ...], tuple[Reached, ...]]:
    """The (reached, informed) sources of edges into the changed items, outside the ChangeSet."""
    reached: dict[tuple[str, str, str], Reached] = {}
    informed: dict[tuple[str, str, str], Reached] = {}
    for item in changed:
        for edge in edges_into(item):
            if edge.source in in_changeset:
                continue
            key = (edge.source, edge.type, item)
            entry = Reached(item=edge.source, via_edge=edge.type, to=item)
            if impacts.get(edge.type, Impact.REVIEW) is Impact.REVIEW:
                reached[key] = entry
            else:
                informed[key] = entry
    return (
        tuple(reached[k] for k in sorted(reached)),
        tuple(informed[k] for k in sorted(informed)),
    )


@dataclass(frozen=True, slots=True)
class RoundSpec:
    """What one walk round walks: its number, the materialised revisions and their bases."""

    number: int
    materialised: Sequence[Materialised]
    bases: Mapping[ItemId, SemanticHash | None]


def walk(uow: Uow, impacts: Impacts, project: ProjectId, spec: RoundSpec) -> WalkResult:
    """Walk one round of a ChangeSet against its bases, over the project's current edges."""
    materialised, bases = spec.materialised, spec.bases
    items = [m.proposal.item for m in materialised]
    changed = tuple(m.proposal.item for m in materialised if m.hash != bases.get(m.proposal.item))
    reached, informed = reach(
        changed, lambda item: edges_to(uow, project, item), impacts, frozenset(items)
    )
    return WalkResult(
        round=spec.number,
        bases=tuple(ItemBase(item=item, base=bases.get(item)) for item in items),
        changed=changed,
        reached=reached,
        informed=informed,
    )


def missing_verdicts(result: WalkResult, verdicts: Iterable[Verdict]) -> list[ItemId]:
    """Reached items without an `unaffected` verdict giving a reason; empty at the fixed point."""
    given = {v.item for v in verdicts if v.verdict == "unaffected" and v.reason.strip()}
    return sorted({r.item for r in result.reached} - given)
