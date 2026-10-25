-- The event outbox (SPEC-03, REQ-0313, REQ-0314). A module records an event in
-- the unit of work of the change it describes; `event_seq` hands out per-project
-- sequence numbers with no gaps, serialized with that change. The instance's own
-- stream uses the nil UUID as its project, so `project` has no foreign key.
-- Insert-only: an event is never changed or removed.
CREATE TABLE platform.events (
    project uuid NOT NULL,
    seq bigint NOT NULL CHECK (seq > 0),
    event_id uuid NOT NULL UNIQUE,
    type text NOT NULL,
    schema_version integer NOT NULL CHECK (schema_version > 0),
    payload jsonb NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project, seq)
);

CREATE TABLE platform.event_seq (
    project uuid PRIMARY KEY,
    last_seq bigint NOT NULL CHECK (last_seq > 0)
);

-- How far each consumer has dispatched each project's stream.
CREATE TABLE platform.event_cursors (
    consumer text NOT NULL,
    project uuid NOT NULL,
    seq bigint NOT NULL CHECK (seq > 0),
    PRIMARY KEY (consumer, project)
);

CREATE FUNCTION platform.refuse_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'platform.% is insert-only', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TRIGGER events_insert_only BEFORE UPDATE OR DELETE ON platform.events
    FOR EACH ROW EXECUTE FUNCTION platform.refuse_change();
