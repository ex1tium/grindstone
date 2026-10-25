"""The kinds `intent` knows: every registered kind's declaration and compiled contract.

Built from the frozen registries at start-up, so `core` kinds and every
loaded factory's kinds validate, hash and derive edges the same way (SPEC-03,
REQ-0305). Unknown kinds are refused with `kind_not_enabled`.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import cast

from grindstone.contracts.base import Contract
from grindstone.contracts.platform import FieldDecl, FieldType, KindDecl
from grindstone.intent.errors import IntentError
from grindstone.platform import Category, Registries
from grindstone.platform.kinds import compile_kind


@dataclass(frozen=True, slots=True)
class KindCatalog:
    """Kind declarations and their compiled contracts, by kind name."""

    decls: Mapping[str, KindDecl]
    models: Mapping[str, type[Contract]]

    @classmethod
    def from_decls(cls, decls: Mapping[str, KindDecl]) -> KindCatalog:
        patterns = {name: d.id.pattern for name, d in decls.items()}
        return cls(dict(decls), {name: compile_kind(d, patterns) for name, d in decls.items()})

    @classmethod
    def from_registries(cls, registries: Registries) -> KindCatalog:
        names = registries.names(Category.KIND)
        return cls.from_decls(
            {n: cast(KindDecl, registries.require(Category.KIND, n).value) for n in names}
        )

    def decl(self, kind: str) -> KindDecl:
        found = self.decls.get(kind)
        if found is None:
            raise IntentError("kind_not_enabled", f"{kind!r} is not a registered kind", kind=kind)
        return found

    def model(self, kind: str) -> type[Contract]:
        self.decl(kind)
        return self.models[kind]

    def ref_fields(self, kind: str) -> Iterator[tuple[str, FieldDecl]]:
        """Each field holding references, with the declaration that names its edge."""
        for name, field in self.decl(kind).fields.items():
            if field.type is FieldType.REF:
                yield name, field
            elif (
                field.type is FieldType.LIST
                and field.of is not None
                and field.of.type is FieldType.REF
            ):
                yield name, field.of
