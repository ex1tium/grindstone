-- Projects and their configuration (SPEC-03, REQ-0311). A project's
-- configuration is a TOML document kept as numbered versions with their hash
-- and provenance; the current version is the highest. Insert-only: a change
-- is a new version. Whether a project is paused is derived from its latest
-- version's validity and the factory load status, never stored (FF-09).
CREATE TABLE platform.projects (
    id uuid PRIMARY KEY,
    slug text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE platform.project_configs (
    project uuid NOT NULL REFERENCES platform.projects (id),
    version integer NOT NULL CHECK (version > 0),
    toml text NOT NULL,
    hash text NOT NULL,
    provenance jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project, version)
);
