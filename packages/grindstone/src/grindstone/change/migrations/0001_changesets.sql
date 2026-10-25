-- The change schema: drafts, ChangeSets, walk rounds and verdicts (SPEC-04,
-- REQ-0409 to REQ-0415). Drafts, rounds and verdicts are insert-only, and the
-- database refuses any update or delete of them. A ChangeSet's `state` and
-- `decision` are written only by its transition function (FF-08). The
-- decision lives in schema `decisions`, so it carries no foreign key (FF-07).
-- TKT-0404 replaces the state check with a generated enum.
CREATE SCHEMA change;

CREATE FUNCTION change.refuse_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'change.% is insert-only', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TABLE change.drafts (
    id uuid PRIMARY KEY,
    project uuid NOT NULL,
    source text NOT NULL
        CHECK (source IN ('operator', 'task_output', 'delegation_result', 'intake', 'revert')),
    trust text NOT NULL CHECK (trust IN ('trusted', 'untrusted')),
    revisions jsonb NOT NULL,
    provenance jsonb NOT NULL,
    client_key text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (source <> 'intake' OR trust = 'untrusted')
);

-- A repeated request finds its draft by client key (REQ-0410).
CREATE UNIQUE INDEX drafts_client_key ON change.drafts (project, client_key)
    WHERE client_key IS NOT NULL;

CREATE TABLE change.changesets (
    id uuid PRIMARY KEY,
    project uuid NOT NULL,
    draft uuid NOT NULL UNIQUE REFERENCES change.drafts (id),
    state text NOT NULL DEFAULT 'drafted'
        CHECK (state IN ('drafted', 'walked', 'awaiting_approval', 'applied', 'rejected')),
    decision uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((state = 'awaiting_approval') <= (decision IS NOT NULL))
);

CREATE INDEX changesets_open ON change.changesets (project)
    WHERE state IN ('drafted', 'walked', 'awaiting_approval');

CREATE TABLE change.walk_rounds (
    changeset uuid NOT NULL REFERENCES change.changesets (id),
    round integer NOT NULL CHECK (round >= 1),
    bases jsonb NOT NULL,
    changed jsonb NOT NULL,
    reached jsonb NOT NULL,
    informed jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (changeset, round)
);

CREATE TABLE change.verdicts (
    changeset uuid NOT NULL,
    round integer NOT NULL,
    item text NOT NULL,
    verdict text NOT NULL CHECK (verdict = 'unaffected'),
    reason text NOT NULL CHECK (reason <> ''),
    decision uuid NOT NULL,
    PRIMARY KEY (changeset, round, item),
    FOREIGN KEY (changeset, round) REFERENCES change.walk_rounds (changeset, round)
);

CREATE TRIGGER drafts_insert_only BEFORE UPDATE OR DELETE ON change.drafts
    FOR EACH ROW EXECUTE FUNCTION change.refuse_change();
CREATE TRIGGER walk_rounds_insert_only BEFORE UPDATE OR DELETE ON change.walk_rounds
    FOR EACH ROW EXECUTE FUNCTION change.refuse_change();
CREATE TRIGGER verdicts_insert_only BEFORE UPDATE OR DELETE ON change.verdicts
    FOR EACH ROW EXECUTE FUNCTION change.refuse_change();
