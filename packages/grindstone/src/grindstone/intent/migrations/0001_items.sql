-- The intent schema: items, their immutable revisions, derived edges,
-- lifecycle transitions and ID counters (SPEC-04, REQ-0401 to REQ-0407).
-- Revisions, edges and transitions are insert-only, and the database refuses
-- any update or delete of them (I-02). An item's lifecycle state must be one
-- its kind declares: `lifecycle_states` is rewritten from the registries at
-- start-up (DEC-0405).
CREATE SCHEMA intent;

CREATE FUNCTION intent.refuse_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'intent.% is insert-only', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TABLE intent.lifecycle_states (
    kind text NOT NULL,
    state text NOT NULL,
    PRIMARY KEY (kind, state)
);

CREATE TABLE intent.item_revisions (
    id uuid PRIMARY KEY,
    project uuid NOT NULL,
    item text NOT NULL,
    kind text NOT NULL,
    title text NOT NULL,
    semantic jsonb NOT NULL,
    presentation jsonb NOT NULL,
    hash text NOT NULL CHECK (hash ~ '^sha256:[0-9a-f]{64}$'),
    parent uuid REFERENCES intent.item_revisions (id),
    provenance jsonb NOT NULL CHECK (
        provenance ? 'author_kind' AND provenance ? 'author' AND provenance ? 'reason'
        AND length(provenance ->> 'reason') > 0
    ),
    changeset uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX item_revisions_by_item ON intent.item_revisions (project, item);
CREATE INDEX item_revisions_by_hash ON intent.item_revisions (project, item, hash);

CREATE TABLE intent.items (
    project uuid NOT NULL,
    id text NOT NULL,
    kind text NOT NULL,
    current_revision uuid NOT NULL REFERENCES intent.item_revisions (id),
    lifecycle_state text,
    PRIMARY KEY (project, id),
    FOREIGN KEY (kind, lifecycle_state) REFERENCES intent.lifecycle_states (kind, state)
);

CREATE TABLE intent.edges (
    revision uuid NOT NULL REFERENCES intent.item_revisions (id),
    project uuid NOT NULL,
    source text NOT NULL,
    type text NOT NULL,
    target text NOT NULL,
    PRIMARY KEY (revision, type, target)
);
CREATE INDEX edges_by_target ON intent.edges (project, target);

CREATE TABLE intent.lifecycle_transitions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project uuid NOT NULL,
    item text NOT NULL,
    kind text NOT NULL,
    from_state text,
    to_state text NOT NULL,
    writer text NOT NULL CHECK (writer IN ('changeset', 'task', 'evidence', 'delivery')),
    cause text NOT NULL,
    at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE intent.id_counters (
    project uuid NOT NULL,
    prefix text NOT NULL,
    next bigint NOT NULL CHECK (next >= 1),
    PRIMARY KEY (project, prefix)
);

CREATE TRIGGER item_revisions_insert_only BEFORE UPDATE OR DELETE ON intent.item_revisions
    FOR EACH ROW EXECUTE FUNCTION intent.refuse_change();
CREATE TRIGGER edges_insert_only BEFORE UPDATE OR DELETE ON intent.edges
    FOR EACH ROW EXECUTE FUNCTION intent.refuse_change();
CREATE TRIGGER lifecycle_transitions_insert_only BEFORE UPDATE OR DELETE ON intent.lifecycle_transitions
    FOR EACH ROW EXECUTE FUNCTION intent.refuse_change();
