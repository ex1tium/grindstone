"""The `core` names the kernel registers before any factory loads (SPEC-03, REQ-0301).

The five kernel kinds follow SPEC-04's table ("The `core` kinds, first form"),
which SPEC-04 owns; their meaning at revision time is `intent`'s. The needs,
check shapes, subject kinds and decision kinds are the kernel's own, and every
kernel error code is copied in, so the registry answers for all of them.
"""

from grindstone.contracts.errors import KERNEL_ERROR_CODES
from grindstone.contracts.platform import (
    Cardinality,
    CheckShape,
    EdgeDecl,
    FieldDecl,
    FieldType,
    IdDecl,
    Impact,
    KindDecl,
)
from grindstone.platform.registries import CORE_ORIGIN, Category, Registries

_TEXT = FieldDecl(type=FieldType.TEXT)
_STRING = FieldDecl(type=FieldType.STRING)
_STRINGS = FieldDecl(type=FieldType.LIST, of=_STRING, required=False, default=[])


def _enum(*values: str) -> FieldDecl:
    return FieldDecl(type=FieldType.ENUM, values=values)


def _ref(edge: str, cardinality: Cardinality) -> FieldDecl:
    return FieldDecl(type=FieldType.REF, edge=edge, cardinality=cardinality)


def _id(prefix: str, *, allocated: bool = False) -> IdDecl:
    return IdDecl(
        pattern=f"^{prefix}-[0-9]+$",
        examples=(f"{prefix}-1",),
        allocate=f"{prefix}-{{n}}" if allocated else None,
    )


CORE_KINDS: tuple[KindDecl, ...] = (
    KindDecl(name="core.principle", id=_id("P"), fields={"statement": _TEXT}),
    KindDecl(name="core.learning", id=_id("LRN"), fields={"lesson": _TEXT, "tags": _STRINGS}),
    KindDecl(
        name="core.finding",
        id=_id("FND", allocated=True),
        fields={
            "type": _enum(
                "ambiguity", "gap", "conflict", "discovery", "failure", "drift", "delivery_bypass"
            ),
            "severity": _enum("low", "medium", "high"),
            "trust": _enum("trusted", "untrusted"),
            "description": _TEXT,
            "about": _ref("core.about", Cardinality.MANY),
        },
    ),
    KindDecl(
        name="core.observation",
        id=_id("OBS", allocated=True),
        fields={"source": _STRING, "content": _TEXT, "inputs": _STRINGS},
    ),
    KindDecl(
        name="core.interface",
        id=_id("IF"),
        fields={
            "shape": _STRING,
            "contract": _TEXT,
            "provider": _ref("core.provider", Cardinality.ONE),
            "consumers": _ref("core.consumer", Cardinality.MANY),
        },
    ),
)
"""SPEC-04's table. An empty `kinds` on a reference means it may target any kind."""

CORE_EDGES: tuple[EdgeDecl, ...] = (
    EdgeDecl(name="core.about", inverse="core.about_of", impact=Impact.NOTIFY),
    # SPEC-04 gives the interface's provider and consumers no edge names; these are
    # proposed with `review` impact (ADR-25: "interface items carry review edges").
    EdgeDecl(name="core.provider", inverse="core.provider_of", impact=Impact.REVIEW),
    EdgeDecl(name="core.consumer", inverse="core.consumer_of", impact=Impact.REVIEW),
)

CORE_NEEDS: tuple[str, ...] = ("core.review.impact", "core.advise", "operator")
CORE_SUBJECT_KINDS: tuple[str, ...] = ("git_commit", "blob", "blob_set", "item_revision")
CORE_DECISION_KINDS: tuple[str, ...] = (
    "approval",
    "question",
    "permission",
    "delivery",
    "escalation",
)


def core_registries() -> Registries:
    """New registries holding the `core` names, not yet frozen, ready for factories."""
    registries = Registries()

    def add(category: Category, name: str, value: object = None) -> None:
        registries.register(category, name, value, CORE_ORIGIN)

    for kind in CORE_KINDS:
        add(Category.KIND, kind.name, kind)
    for edge in CORE_EDGES:
        add(Category.EDGE, edge.name, edge)
    for need in CORE_NEEDS:
        add(Category.NEED, need)
    for shape in CheckShape:
        add(Category.CHECK_SHAPE, shape.value, shape)
    for subject in CORE_SUBJECT_KINDS:
        add(Category.SUBJECT_KIND, subject)
    for decision in CORE_DECISION_KINDS:
        add(Category.DECISION_KIND, decision)
    for error_class, codes in KERNEL_ERROR_CODES.items():
        for code in sorted(codes):
            add(Category.ERROR_CODE, code, error_class)
    return registries
