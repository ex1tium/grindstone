"""Workflow-version check (REQ-0208): a changed workflow needs a new version or a note."""

from pathlib import Path

from scripts.ff.workflow_versions import RECORD, Record, scan, violations

from tests.fitness.helpers import REPO

RUNTIME = """
WORKFLOW_VERSION = "{version}"
"""

STEPS = '''
from grindstone.store import transaction


@transaction
def record_effect(uow, what):
    """Writes one row."""
    uow.execute("INSERT INTO demo.effects (what) VALUES (:what)", {{"what": what}})
'''

WORKFLOWS = '''
from grindstone import store
from grindstone.demo.steps import record_effect


def _helper(record):
    return record.upper()


@store.workflow("demo.run")
def run(record):
    """The docstring is not part of the fingerprint."""
    record_effect(record)
    {extra}
    return _helper(record)
'''


def _tree(root: Path, *, version: str = "1", extra: str = "pass", step_sql: str = "INSERT") -> Path:
    store = root / "packages/grindstone/src/grindstone/store"
    demo = root / "packages/grindstone/src/grindstone/demo"
    store.mkdir(parents=True, exist_ok=True)
    demo.mkdir(parents=True, exist_ok=True)
    (store / "runtime.py").write_text(RUNTIME.format(version=version))
    (demo / "steps.py").write_text(STEPS.replace("INSERT", step_sql).format())
    (demo / "flows.py").write_text(WORKFLOWS.format(extra=extra))
    return root


def test_workflow_change_needs_version_or_note(tmp_path: Path) -> None:
    """AC-0208-1."""
    base = scan(_tree(tmp_path / "base"))
    assert set(base.workflows) == {"demo.run"}
    assert base.version == "1"

    # Layout, comments and docstrings are not changes.
    same = tmp_path / "same"
    _tree(same)
    flows = same / "packages/grindstone/src/grindstone/demo/flows.py"
    flows.write_text(flows.read_text().replace('"""The docstring', '"""Another docstring'))
    assert scan(same) == base

    changed = scan(_tree(tmp_path / "changed", extra="record_effect(record)"))
    new = changed.workflows["demo.run"][:12]
    assert violations(base, changed, "") == [
        "workflow 'demo.run' changed while WORKFLOW_VERSION stayed 1: raise it, or add "
        f"`## Workflow demo.run {new}` to docs/upgrades.md if the change is replay-compatible"
    ]
    note = f"# Upgrades\n\n## Workflow demo.run {new}\n\nOne step added after the others.\n"
    assert violations(base, changed, note) == []
    # A note for an earlier fingerprint does not cover a later change.
    stale = note.replace(new, base.workflows["demo.run"][:12])
    assert len(violations(base, changed, stale)) == 1

    # A step the workflow calls by name, imported from another module, counts too.
    step_changed = scan(_tree(tmp_path / "step", step_sql="UPSERT"))
    assert step_changed.workflows != base.workflows
    assert len(violations(base, step_changed, "")) == 1

    raised = scan(_tree(tmp_path / "raised", version="2", extra="record_effect(record)"))
    assert violations(base, raised, "") == []
    lowered = Record(version="0", workflows=changed.workflows)
    assert violations(base, lowered, "") == [
        "WORKFLOW_VERSION went down from 1 to 0; it only rises"
    ]

    removed = Record(version="1", workflows={})
    assert len(violations(base, removed, "")) == 1
    assert violations(base, removed, "## Workflow demo.run removed\n") == []
    assert violations(None, changed, "") == []


def test_repository_record_is_current() -> None:
    committed = Record.from_json((REPO / RECORD).read_text(encoding="utf-8"))
    assert scan(REPO) == committed
