"""The store's contracts: its settings and the root that keeps a blob alive (SPEC-02).

A blob is never without a root from the moment it is written (ADR-04): a
root names the project it counts against and the record that holds it. A
lease root belongs to the run or job that produced the blob and is released
when that record is archived; other roots belong to the records that
reference the blob, and commit with the reference.
"""

from typing import Literal

from pydantic import Field

from grindstone.contracts.base import Contract
from grindstone.contracts.ids import ProjectId
from grindstone.contracts.refs import BlobRef

GIB = 1024**3


class StoreSettings(Contract):
    """`[store]` in `grindstone.toml`, with the seeds SPEC-02 states.

    SPEC-02 also places the database settings here; they are read from
    `GRINDSTONE_DB_*` until the database moves into the instance file, and
    join this contract then.
    """

    schema_version: Literal[1] = 1
    blobs_dir: str = "/var/lib/grindstone/blobs"
    max_blob_bytes: int = Field(default=2 * GIB, ge=1)
    max_project_bytes: int = Field(default=20 * GIB, ge=1)


class BlobRoot(Contract):
    """One record's hold on a blob, counted against one project."""

    schema_version: Literal[1] = 1
    blob: BlobRef
    project: ProjectId
    owner_module: str = Field(min_length=1)
    owner_kind: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    lease: bool
