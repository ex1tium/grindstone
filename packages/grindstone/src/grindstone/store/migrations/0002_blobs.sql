-- The blob store's metadata (SPEC-02, REQ-0209 to REQ-0212). The bytes live
-- on the `blobs` volume under their hash; these tables say which blobs exist
-- and which records hold them. Blob rows are insert-only. A root is inserted,
-- and later released once by setting `released_at`; nothing else changes.
-- A blob row must have a root when its transaction commits (REQ-0210), which
-- a deferred constraint trigger checks. Project totals are a view, never
-- stored (REQ-0216).
CREATE FUNCTION store.refuse_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'store.% is insert-only', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TABLE store.blobs (
    sha256 text PRIMARY KEY CHECK (sha256 ~ '^sha256:[0-9a-f]{64}$'),
    size bigint NOT NULL CHECK (size >= 0),
    media_type text NOT NULL,
    first_seen timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE store.blob_roots (
    id uuid PRIMARY KEY,
    blob text NOT NULL REFERENCES store.blobs (sha256),
    project uuid NOT NULL,
    owner_module text NOT NULL CHECK (owner_module <> ''),
    owner_kind text NOT NULL CHECK (owner_kind <> ''),
    owner_id text NOT NULL CHECK (owner_id <> ''),
    lease boolean NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    released_at timestamptz
);

-- An owner holds a blob in a project at most once at a time, so a put or a
-- root repeated by the same owner finds its existing root.
CREATE UNIQUE INDEX blob_roots_held ON store.blob_roots
    (blob, project, owner_module, owner_kind, owner_id, lease) WHERE released_at IS NULL;
CREATE INDEX blob_roots_owner ON store.blob_roots (owner_kind, owner_id) WHERE released_at IS NULL;
CREATE INDEX blob_roots_project ON store.blob_roots (project) WHERE released_at IS NULL;

CREATE TRIGGER blobs_insert_only BEFORE UPDATE OR DELETE ON store.blobs
    FOR EACH ROW EXECUTE FUNCTION store.refuse_change();
CREATE TRIGGER blob_roots_no_delete BEFORE DELETE ON store.blob_roots
    FOR EACH ROW EXECUTE FUNCTION store.refuse_change();

CREATE FUNCTION store.release_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.released_at IS NOT NULL OR NEW.released_at IS NULL
        OR (NEW.id, NEW.blob, NEW.project, NEW.owner_module, NEW.owner_kind, NEW.owner_id,
            NEW.lease, NEW.created_at)
           IS DISTINCT FROM
           (OLD.id, OLD.blob, OLD.project, OLD.owner_module, OLD.owner_kind, OLD.owner_id,
            OLD.lease, OLD.created_at)
    THEN
        RAISE EXCEPTION 'store.blob_roots: a root is only released, once'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER blob_roots_release_only BEFORE UPDATE ON store.blob_roots
    FOR EACH ROW EXECUTE FUNCTION store.release_only();

CREATE FUNCTION store.blob_has_root() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM store.blob_roots WHERE blob = NEW.sha256) THEN
        RAISE EXCEPTION 'store.blobs: % committed without a root', NEW.sha256
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER blobs_rooted AFTER INSERT ON store.blobs
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION store.blob_has_root();

-- Bytes each project holds: every distinct blob with an unreleased root
-- there, counted once however many roots it has.
CREATE VIEW store.project_blob_bytes AS
SELECT held.project, sum(b.size)::bigint AS bytes
FROM (SELECT DISTINCT project, blob FROM store.blob_roots WHERE released_at IS NULL) AS held
JOIN store.blobs AS b ON b.sha256 = held.blob
GROUP BY held.project;
