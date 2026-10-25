-- The platform's schema and its history of factory loads: one row per factory
-- per start, loaded or refused, with its version, manifest hash and report
-- (SPEC-03, DEC-0304). Insert-only; the registries are rebuilt from the
-- packages at every start, so this table is history, never a source.
CREATE SCHEMA platform;

CREATE TABLE platform.factories (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    version text,
    manifest_hash text,
    status text NOT NULL CHECK (status IN ('loaded', 'refused')),
    report jsonb NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    CHECK (status = 'refused' OR (version IS NOT NULL AND manifest_hash IS NOT NULL))
);
