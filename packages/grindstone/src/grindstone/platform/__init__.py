"""Platform layer. Extension registries and configuration: kinds, edges,
methods, capabilities, templates, subjects, adapters, decision kinds and
rules; the manifest loader; project configuration; `grindstone check`.
"""

from grindstone.platform.core import core_registries
from grindstone.platform.registries import (
    CORE,
    CORE_ORIGIN,
    SDK_VERSION,
    Category,
    Entry,
    Origin,
    Registries,
    RegistryError,
    loading,
    register_error_code,
)

__all__ = [
    "CORE",
    "CORE_ORIGIN",
    "SDK_VERSION",
    "Category",
    "Entry",
    "Origin",
    "Registries",
    "RegistryError",
    "core_registries",
    "loading",
    "register_error_code",
]
