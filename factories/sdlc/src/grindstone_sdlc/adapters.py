"""The code the `sdlc` manifest names, by name (`ADAPTERS`, SPEC-03).

The loader imports this module only after the manifest passes, and checks
that every workspace provider, delivery adapter and mechanical check method
the manifest declares is here. Their code arrives with their own tickets:
the git workspace provider with TKT-0902, the CI suite with TKT-0903, the
GitHub pull-request adapter with TKT-0904. Until then each name holds a
placeholder that says so, and that no port can call.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pending:
    """A declared name whose implementation a later ticket supplies."""

    name: str
    ticket: str


ADAPTERS: dict[str, object] = {
    "sdlc.git": Pending("sdlc.git", "TKT-0902"),
    "sdlc.ci_suite": Pending("sdlc.ci_suite", "TKT-0903"),
    "sdlc.github_pr": Pending("sdlc.github_pr", "TKT-0904"),
}
