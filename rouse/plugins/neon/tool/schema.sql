-- One table, because there is one kind of thing in a rouse tree: a file
-- with a header. A belief and a task differ in what their header means
-- and in what sweeps them, not in what they are made of — and a schema
-- that split them into seven tables would have to be migrated every time
-- the ladder grew a level.
--
-- Everything here is IF NOT EXISTS. `rouse neon init` is run again by
-- everyone who forgets whether they ran it.

CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.memory (
    -- the path inside the tree, and it is the identity: one tree per
    -- agent, one row per file, and a file that moves is a different row
    -- (the old one is deleted by the same sync that adds the new one)
    path      text PRIMARY KEY,
    kind      text NOT NULL,          -- note, belief, intention, task, …
    slug      text NOT NULL,
    -- the nearest enclosing record, as a path. Copied off the tree walk
    -- rather than re-derived here: containment is the filesystem, and a
    -- second answer to it is a second thing that can be wrong.
    parent    text,
    status    text,
    keywords  text[] NOT NULL DEFAULT '{}',
    -- the whole header, so a query can ask about a field this schema
    -- never heard of. New fields arrive with new levels; a migration per
    -- field would make the ladder expensive to change.
    head      jsonb  NOT NULL DEFAULT '{}',
    body      text   NOT NULL DEFAULT '',
    mtime     timestamptz NOT NULL,
    -- the file's bytes. An unchanged file is not rewritten, so `synced_at`
    -- means "this row was last different", which is what you want when
    -- you are looking for what actually moved.
    sha       text NOT NULL,
    synced_at timestamptz NOT NULL DEFAULT now(),
    -- generated, not maintained: a tsvector column something has to
    -- remember to update is a search index that is quietly wrong.
    --
    -- The keywords come out of `head` rather than out of the array beside
    -- it, and that is not a style choice: `array_to_string` is stable,
    -- not immutable, so postgres refuses it in a generated column. `->>`
    -- is immutable, the header is already the source both columns are
    -- derived from, and the array stays for the filters that want it.
    tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('english',
                    coalesce(body, '') || ' ' ||
                    coalesce(head ->> 'keywords', '') || ' ' ||
                    replace(path, '/', ' '))) STORED
);

-- when the index was last built, which is not the same question as when
-- a row last changed. An unchanged file is not rewritten, so `synced_at`
-- on a quiet week says "seven days ago" about a sync that ran a minute
-- ago — and the one thing a person asks this table is whether it is
-- current. One row, forever.
CREATE TABLE IF NOT EXISTS {schema}.sync (
    only_row boolean PRIMARY KEY DEFAULT true CHECK (only_row),
    ran_at   timestamptz NOT NULL DEFAULT now(),
    files    integer NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS memory_tsv ON {schema}.memory USING gin (tsv);
CREATE INDEX IF NOT EXISTS memory_keywords
    ON {schema}.memory USING gin (keywords);
CREATE INDEX IF NOT EXISTS memory_kind ON {schema}.memory (kind);
CREATE INDEX IF NOT EXISTS memory_open ON {schema}.memory (status)
    WHERE status IS NOT NULL;
