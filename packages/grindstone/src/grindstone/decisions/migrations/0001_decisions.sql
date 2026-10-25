-- The decisions schema: decision records, their answers and continuations
-- (SPEC-04, REQ-0416 to REQ-0419). A decision's `state` and `superseded_by`
-- are written only by its transition function (FF-08); answers and
-- continuations are insert-only, and the database refuses any update or
-- delete of them. TKT-0404 replaces the state check with a generated enum.
CREATE SCHEMA decisions;

CREATE FUNCTION decisions.refuse_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'decisions.% is insert-only', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TABLE decisions.decisions (
    id uuid PRIMARY KEY,
    project uuid NOT NULL,
    kind text NOT NULL,
    flags jsonb NOT NULL DEFAULT '[]',
    scope jsonb NOT NULL,
    context_hash text NOT NULL CHECK (context_hash ~ '^sha256:[0-9a-f]{64}$'),
    title text NOT NULL,
    payload jsonb NOT NULL,
    recommendation jsonb NOT NULL,
    state text NOT NULL DEFAULT 'open'
        CHECK (state IN ('open', 'answered', 'superseded', 'expired')),
    raised_by text NOT NULL,
    raised_at timestamptz NOT NULL DEFAULT now(),
    superseded_by uuid REFERENCES decisions.decisions (id),
    CHECK ((state = 'superseded') = (superseded_by IS NOT NULL))
);

CREATE INDEX decisions_open ON decisions.decisions (project, raised_at) WHERE state = 'open';

CREATE TABLE decisions.answers (
    decision uuid PRIMARY KEY REFERENCES decisions.decisions (id),
    answer jsonb NOT NULL,
    answered_by text NOT NULL,
    channel text NOT NULL CHECK (channel IN ('ui', 'api', 'vscode', 'plugin')),
    context_hash_seen text NOT NULL,
    client_key text NOT NULL,
    at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE decisions.continuations (
    decision uuid PRIMARY KEY REFERENCES decisions.decisions (id),
    name text NOT NULL,
    payload jsonb NOT NULL
);

CREATE TRIGGER answers_insert_only BEFORE UPDATE OR DELETE ON decisions.answers
    FOR EACH ROW EXECUTE FUNCTION decisions.refuse_change();
CREATE TRIGGER continuations_insert_only BEFORE UPDATE OR DELETE ON decisions.continuations
    FOR EACH ROW EXECUTE FUNCTION decisions.refuse_change();
