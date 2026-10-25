"""ChangeSet contracts (SPEC-04).

`Verdict` arrives first, with the decision records, because the `approval`
decision's answer carries verdicts. TKT-0403 adds the rest of this module:
drafts, walk results and the draft request.
"""

from typing import Literal

from grindstone.contracts.base import Contract
from grindstone.contracts.ids import ItemId


class Verdict(Contract):
    """A reviewer's verdict on an item the walk reached; M1 accepts only `unaffected` (DEC-0402).

    An empty reason is a valid verdict here; applying the approval refuses it
    with `verdict_missing` (REQ-0413).
    """

    item: ItemId
    verdict: Literal["unaffected"] = "unaffected"
    reason: str
