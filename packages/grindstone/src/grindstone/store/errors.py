"""The store's typed failures.

Each carries one of the kernel error codes SPEC-02 declares. SPEC-01's error
envelope (TKT-0102) maps them onto `ErrorEnvelope`; until it lands the code is
a plain string on the exception.
"""

from typing import Literal

type StoreErrorCode = Literal["database_unavailable", "migration_failed"]


class StoreError(Exception):
    """A store operation failed for a reason the caller may need to act on.

    `database_unavailable` is transient (retry later); `migration_failed` is
    internal and stops start-up. Messages name the failing object and the
    exception class only, never connection details.
    """

    def __init__(self, code: StoreErrorCode, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code: StoreErrorCode = code
