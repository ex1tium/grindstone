-- The store's schema and its migration ledger: one row per applied migration
-- file, keyed by module and number, with the hash of the file as applied
-- (SPEC-02, REQ-0202). Applied files are append-only; a changed hash stops
-- start-up with migration_failed.
CREATE SCHEMA store;

CREATE TABLE store.migrations (
    module text NOT NULL,
    number integer NOT NULL,
    sha256 text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (module, number)
);
