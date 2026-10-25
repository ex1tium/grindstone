"""The M1 rules a draft must pass, at draft time and again before each approval (SPEC-04).

- every kind belongs to a factory enabled in the project, or to `core`;
- every ID matches its kind's pattern and no item of another kind holds it,
  and no item is proposed twice;
- every revision validates against its kind's contract;
- every revision of an existing item is based on its current hash, read
  from the effective bases (the latest walk round's, DEC-0407);
- every reference resolves in the project or the draft (REQ-0404).

Every problem is collected, per item, and the draft is refused with all of
them at once.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from grindstone.change.errors import ChangeError, Problem
from grindstone.contracts.change import ProposedRevision
from grindstone.contracts.ids import ItemId, ProjectId
from grindstone.contracts.refs import SemanticHash
from grindstone.intent import (
    IntentError,
    KindCatalog,
    Materialised,
    Proposal,
    check_id,
    current_hash,
    materialise,
    unresolved_references,
)
from grindstone.store import Uow

CORE_NAMESPACE = "core"

type EnabledFactories = Callable[[Uow, ProjectId], frozenset[str] | None]
"""The factory namespaces enabled in a project; None admits every loaded factory."""


def every_factory(uow: Uow, project: ProjectId) -> frozenset[str] | None:
    """An `EnabledFactories` that admits every loaded factory."""
    del uow, project
    return None


@dataclass(frozen=True, slots=True)
class Rules:
    """The M1 rules over the registered kinds and each project's enabled factories."""

    catalog: KindCatalog
    enabled: EnabledFactories = every_factory

    def check(
        self,
        uow: Uow,
        project: ProjectId,
        revisions: Sequence[ProposedRevision],
        bases: Mapping[ItemId, SemanticHash | None],
    ) -> list[Materialised]:
        """Each revision materialised against its kind, or `ChangeError` listing every problem."""
        return check_draft(uow, self, project, revisions, bases)


def check_draft(
    uow: Uow,
    rules: Rules,
    project: ProjectId,
    revisions: Sequence[ProposedRevision],
    bases: Mapping[ItemId, SemanticHash | None],
) -> list[Materialised]:
    """Each revision materialised against its kind, or `ChangeError` listing every problem."""
    catalog = rules.catalog
    problems: list[Problem] = []
    materialised: list[Materialised] = []
    allowed = rules.enabled(uow, project)
    seen: set[ItemId] = set()
    for revision in revisions:
        item = revision.item
        if item in seen:
            problems.append(Problem(item, "id_taken", f"{item} is proposed twice"))
            continue
        seen.add(item)
        namespace = revision.kind.split(".", 1)[0]
        if namespace != CORE_NAMESPACE and allowed is not None and namespace not in allowed:
            message = f"{item}: {revision.kind} belongs to {namespace}, not enabled in the project"
            problems.append(Problem(item, "kind_not_enabled", message))
            continue
        try:
            check_id(uow, catalog, project, revision.kind, item)
            m = materialise(catalog, Proposal(item, revision.kind, revision.title, revision.fields))
        except IntentError as exc:
            problems.append(Problem(item, exc.code, f"{item}: {exc}"))
            continue
        except ValidationError as exc:
            problems.extend(
                Problem(item, "report_invalid", f"{item}: {_loc(e['loc'])}{e['msg']}")
                for e in exc.errors()
            )
            continue
        current = current_hash(uow, project, item)
        base = bases.get(item)
        if base != current:
            problems.append(
                Problem(
                    item,
                    "context_changed",
                    f"{item} was drafted against {base or 'no revision'}, but its current"
                    f" revision is {current or 'none'}",
                )
            )
            continue
        materialised.append(m)
    # A reference to another proposed item resolves, even if that item is refused for
    # its own reasons: its problem is reported once, on it.
    for error in unresolved_references(
        materialised,
        lambda target: target in seen or current_hash(uow, project, target) is not None,
    ):
        item = str(error.envelope.detail.get("item"))
        problems.append(Problem(item, error.code, str(error)))
    if problems:
        raise ChangeError(problems)
    return materialised


def _loc(loc: tuple[int | str, ...]) -> str:
    where = ".".join(str(part) for part in loc)
    return f"{where}: " if where else ""
