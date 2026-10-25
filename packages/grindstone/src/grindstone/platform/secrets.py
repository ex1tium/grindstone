"""Secret grants: a factory reads a secret only by a name it declares and its project grants.

Kernel code builds a `Secrets` reader bound to one project and one factory and
hands it to that factory's adapter inside its context (SPEC-03, REQ-0315). The
adapter passes only a name, so it cannot speak for another factory or
project, and the SDK exports no way to build a reader. A refusal is
`secret_not_granted`, a configuration error: no decision is raised.

A value is returned to the caller and nowhere else: it is never logged,
emitted in an event, written to the database or put in an exception.
"""

import logging
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from pathlib import Path
from typing import NoReturn

from grindstone.contracts.errors import ErrorClass, ErrorEnvelope
from grindstone.contracts.ids import ProjectId

_log = logging.getLogger(__name__)


class SecretNotGrantedError(Exception):
    """A secret this factory may not read for this project, with its error envelope."""

    def __init__(self, name: str, *, factory: str, project: ProjectId, reason: str) -> None:
        message = f"{factory} may not read secret {name!r}: {reason}"
        super().__init__(message)
        self.envelope = ErrorEnvelope(
            code="secret_not_granted",
            error_class=ErrorClass.VALIDATION,
            message=message,
            detail={"name": name, "factory": factory, "project": str(project)},
            retryable=False,
        )


class Secrets:
    """The `SecretReader` for one factory in one project, bound by kernel code."""

    __slots__ = ("_declared", "_factory", "_files", "_granted", "_project")

    def __init__(
        self,
        *,
        project: ProjectId,
        factory: str,
        declared: AbstractSet[str],
        granted: AbstractSet[str],
        files: Mapping[str, str],
    ) -> None:
        self._project = project
        self._factory = factory
        self._declared = frozenset(declared)
        self._granted = frozenset(granted)
        self._files = dict(files)

    def read(self, name: str) -> str:
        """The secret's value, read from its file; else `SecretNotGrantedError`."""
        if name not in self._declared:
            self._refuse(name, f"the {self._factory} manifest does not declare it")
        if name not in self._granted:
            self._refuse(name, "the project does not grant it")
        path = self._files.get(name)
        if path is None:
            self._refuse(name, "the instance's [secrets] names no file for it")
        try:
            value = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            self._refuse(name, f"its file cannot be read ({type(exc).__name__})")
        _log.info("factory %s read secret %s for project %s", self._factory, name, self._project)
        return value.rstrip("\r\n")

    def _refuse(self, name: str, reason: str) -> NoReturn:
        _log.warning(
            "secret %s refused to factory %s for project %s: %s",
            name,
            self._factory,
            self._project,
            reason,
        )
        raise SecretNotGrantedError(
            name, factory=self._factory, project=self._project, reason=reason
        )
