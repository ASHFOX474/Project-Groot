-- Initial schema for a fresh LOCAL Docker volume only.
-- Add versioned migrations before shared or production-like data exists.
CREATE TABLE catalog_source (
    id text PRIMARY KEY,
    title text NOT NULL,
    source_url text,
    checked_at date,
    review_status text NOT NULL CHECK (review_status IN ('demo', 'reviewed')),
    CONSTRAINT reviewed_source_has_reference CHECK (
        review_status <> 'reviewed' OR (source_url IS NOT NULL AND checked_at IS NOT NULL)
    ),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE species (
    id text PRIMARY KEY,
    common_name_en text NOT NULL,
    common_name_bn text NOT NULL,
    category text NOT NULL CHECK (category IN ('crop', 'tree')),
    source_id text NOT NULL REFERENCES catalog_source(id),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX species_active_name_idx ON species (common_name_en, id) WHERE is_active;
