"""A stand-in control plane for AC-0209-2, run as a subprocess from the repository root.

    python -m packages.grindstone.tests.store.blob_child <database_url> <blobs_dir> <project>

It opens the store and puts one blob for one owner. With
`GRINDSTONE_KILL_AT=after:store.put_blob.rename` it dies between the rename
into place and the commit of the blob's row, the first time.
"""

import sys
import uuid

from grindstone.contracts.ids import ProjectId
from grindstone.contracts.store import StoreSettings
from grindstone.store import BlobOwner, open_blob_store, open_database, put_blob

CONTENT = b"content that outlives a crash\n"
OWNER = BlobOwner(module="stations", kind="run", id="run-crash-1")


def main(database_url: str, blobs_dir: str, project: str) -> int:
    open_database(database_url)
    open_blob_store(StoreSettings(blobs_dir=blobs_dir))
    put_blob(CONTENT, media_type="text/plain", project=ProjectId(uuid.UUID(project)), owner=OWNER)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
