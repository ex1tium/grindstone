"""Registries: every extension name, where it came from, frozen after start-up (SPEC-03).

The kernel registers its `core` names first; the loader (TKT-0302) then
registers each accepted factory's names in one step, and the registries are
frozen. A factory registers names only in its own namespace (I-18), never a
`core.*` name, and never a name already registered. Every entry keeps its
provenance: factory, factory version, manifest hash and, for a capability,
its hash (REQ-0317).
"""

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum

from grindstone.contracts.errors import ErrorClass, ErrorEnvelope, register_error_codes
from grindstone.contracts.refs import SemanticHash

CORE = "core"
"""The kernel's own namespace."""

SDK_VERSION = "0.1.0"
"""The kernel SDK version; also the version the `core` names are registered under."""


class Category(StrEnum):
    """What a registered name is."""

    KIND = "kind"
    EDGE = "edge"
    NEED = "need"
    CAPABILITY = "capability"
    TEMPLATE = "template"
    CHECK_METHOD = "check_method"
    CHECK_SHAPE = "check_shape"
    SUBJECT_KIND = "subject_kind"
    SUBJECT_RESOLVER = "subject_resolver"
    WORKSPACE_PROVIDER = "workspace_provider"
    DELIVERY_ADAPTER = "delivery_adapter"
    DECISION_KIND = "decision_kind"
    ERROR_CODE = "error_code"
    EVENT_TYPE = "event_type"


@dataclass(frozen=True, slots=True)
class Origin:
    """Who registers a name: the kernel or a factory at a version and manifest hash."""

    factory: str
    version: str
    manifest_hash: SemanticHash | None = None


CORE_ORIGIN = Origin(CORE, SDK_VERSION)


@dataclass(frozen=True, slots=True)
class Entry:
    """One registered name, its declaration and its provenance."""

    category: Category
    name: str
    origin: Origin
    value: object
    capability_hash: SemanticHash | None = None


class RegistryError(Exception):
    """A registration the rules refuse, carrying its error envelope."""

    def __init__(self, code: str, message: str, *, name: str, factory: str) -> None:
        super().__init__(message)
        self.envelope = ErrorEnvelope(
            code=code,
            error_class=ErrorClass.VALIDATION,
            message=message,
            detail={"name": name, "factory": factory},
            retryable=False,
        )


class Registries:
    """Every registered name, by category; read-only once frozen."""

    def __init__(self) -> None:
        self._entries: dict[tuple[Category, str], Entry] = {}
        self._frozen = False

    @property
    def frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        """No further registration; a factory version change takes effect only on restart."""
        self._frozen = True

    def register(
        self,
        category: Category,
        name: str,
        value: object,
        origin: Origin,
        *,
        capability_hash: SemanticHash | None = None,
    ) -> Entry:
        """Register one name, or refuse it with `manifest_invalid` or `name_conflict`."""
        if self._frozen:
            raise RegistryError(
                "manifest_invalid",
                f"{name}: the registries are frozen",
                name=name,
                factory=origin.factory,
            )
        if origin.factory != CORE:
            if name.startswith(f"{CORE}."):
                raise RegistryError(
                    "manifest_invalid",
                    f"{name}: only the kernel registers core names (I-18)",
                    name=name,
                    factory=origin.factory,
                )
            if not name.startswith(f"{origin.factory}."):
                raise RegistryError(
                    "manifest_invalid",
                    f"{name}: not in the {origin.factory} namespace (I-18)",
                    name=name,
                    factory=origin.factory,
                )
        key = (category, name)
        existing = self._entries.get(key)
        if existing is not None:
            raise RegistryError(
                "name_conflict",
                f"{name}: {category.value} already registered by {existing.origin.factory}",
                name=name,
                factory=origin.factory,
            )
        entry = Entry(category, name, origin, value, capability_hash)
        self._entries[key] = entry
        return entry

    def get(self, category: Category, name: str) -> Entry | None:
        return self._entries.get((category, name))

    def require(self, category: Category, name: str) -> Entry:
        """The entry for a name, or `KeyError` naming what is missing."""
        entry = self.get(category, name)
        if entry is None:
            raise KeyError(f"no {category.value} named {name!r}")
        return entry

    def names(self, category: Category) -> tuple[str, ...]:
        """Every name of a category, sorted."""
        return tuple(sorted(n for c, n in self._entries if c is category))

    def entries(self) -> Iterator[Entry]:
        yield from self._entries.values()


_loading: ContextVar[tuple[Registries, Origin] | None] = ContextVar("loading", default=None)


@contextmanager
def loading(registries: Registries, origin: Origin) -> Generator[None]:
    """While the loader imports a factory's code, registration helpers act for that factory."""
    token = _loading.set((registries, origin))
    try:
        yield
    finally:
        _loading.reset(token)


def register_error_code(code: str, error_class: ErrorClass) -> None:
    """Register a factory error code; callable only while the kernel loads that factory."""
    active = _loading.get()
    if active is None:
        raise RegistryError(
            "manifest_invalid",
            f"{code}: error codes are registered only while the kernel loads a factory",
            name=code,
            factory="unknown",
        )
    registries, origin = active
    registries.register(Category.ERROR_CODE, code, error_class, origin)
    register_error_codes(error_class, [code])
