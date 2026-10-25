"""Generic Markdown rendering of a revision (SPEC-04, REQ-0408).

The rendering is generated and read-only: a header names the item and the
ledger as the source of truth, then the title, every semantic field, and every
reference as `[[ID]]`. Mentions, embeds and round-trip import are SPEC-11's.
"""

import json

from pydantic import JsonValue

from grindstone.contracts.intent import ItemRevision
from grindstone.contracts.platform import FieldType
from grindstone.intent.catalog import KindCatalog


def render(revision: ItemRevision, catalog: KindCatalog) -> str:
    """The revision as Markdown."""
    refs = dict(catalog.ref_fields(revision.kind))
    decl = catalog.decl(revision.kind)
    lines = [
        f"<!-- Grindstone item {revision.item} ({revision.kind}), revision {revision.hash}. "
        "Generated from the ledger, which is the source of truth; edits here are not read. -->",
        "",
        f"# {revision.item} — {revision.title}",
    ]
    for name, value in revision.semantic.items():
        if value is None:
            continue
        lines += ["", f"## {name}", ""]
        if name in refs:
            targets = value if isinstance(value, list) else [value]
            lines.append(" ".join(f"[[{t}]]" for t in targets))
        elif decl.fields[name].type is FieldType.LIST and isinstance(value, list):
            lines.extend(f"- {_text(v)}" for v in value)
        else:
            lines.append(_text(value))
    return "\n".join(lines) + "\n"


def _text(value: JsonValue) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
