"""Strict PostgreSQL 16 snapshot of the immutable db/init/001_schema.sql schema.

Do not loosen this check to make adoption pass. Investigate drift and migrate it
explicitly. Data values are intentionally not compared or rewritten.
"""
import sqlalchemy as sa

# name: (PostgreSQL type, nullable, default)
_COLUMNS = {
    "catalog_source": {
        "id": ("TEXT", False, None),
        "title": ("TEXT", False, None),
        "source_url": ("TEXT", True, None),
        "checked_at": ("DATE", True, None),
        "review_status": ("TEXT", False, None),
        "created_at": ("TIMESTAMP WITH TIME ZONE", False, "now()"),
    },
    "species": {
        "id": ("TEXT", False, None),
        "common_name_en": ("TEXT", False, None),
        "common_name_bn": ("TEXT", False, None),
        "category": ("TEXT", False, None),
        "source_id": ("TEXT", False, None),
        "is_active": ("BOOLEAN", False, "true"),
        "created_at": ("TIMESTAMP WITH TIME ZONE", False, "now()"),
    },
}
_CONSTRAINTS = {
    ("catalog_source", "catalog_source_pkey"): "PRIMARY KEY (id)",
    ("catalog_source", "catalog_source_review_status_check"):
        "CHECK ((review_status = ANY (ARRAY['demo'::text, 'reviewed'::text])))",
    ("catalog_source", "reviewed_source_has_reference"):
        "CHECK (((review_status <> 'reviewed'::text) OR ((source_url IS NOT NULL) AND (checked_at IS NOT NULL))))",
    ("species", "species_pkey"): "PRIMARY KEY (id)",
    ("species", "species_category_check"):
        "CHECK ((category = ANY (ARRAY['crop'::text, 'tree'::text])))",
    ("species", "species_source_id_fkey"):
        "FOREIGN KEY (source_id) REFERENCES catalog_source(id)",
}
_INDEXES = {
    "catalog_source_pkey": "CREATE UNIQUE INDEX catalog_source_pkey ON public.catalog_source USING btree (id)",
    "species_pkey": "CREATE UNIQUE INDEX species_pkey ON public.species USING btree (id)",
    "species_active_name_idx": "CREATE INDEX species_active_name_idx ON public.species USING btree (common_name_en, id) WHERE is_active",
}


def validate_legacy(connection):
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names(schema="public")) - {"alembic_version"}
    if tables != set(_COLUMNS) or inspector.get_view_names(schema="public"):
        raise RuntimeError("Legacy baseline refused: unexpected or missing public tables/views")
    for table, expected in _COLUMNS.items():
        actual = {
            c["name"]: (str(c["type"].compile(dialect=connection.dialect)), c["nullable"], c["default"])
            for c in inspector.get_columns(table, schema="public")
        }
        if actual != expected:
            raise RuntimeError(f"Legacy baseline refused: column drift in {table}")
    constraints = connection.execute(sa.text("""
        SELECT t.relname, c.conname, pg_get_constraintdef(c.oid) AS definition,
               c.convalidated, c.condeferrable, c.condeferred
        FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public' AND t.relname IN ('species', 'catalog_source')
    """)).all()
    actual = {(r[0], r[1]): r[2] for r in constraints}
    if actual != _CONSTRAINTS or any(tuple(r[3:]) != (True, False, False) for r in constraints):
        raise RuntimeError("Legacy baseline refused: constraint drift")
    indexes = dict(connection.execute(sa.text("""
        SELECT indexname, indexdef FROM pg_indexes
        WHERE schemaname = 'public' AND tablename IN ('species', 'catalog_source')
    """)).all())
    if indexes != _INDEXES:
        raise RuntimeError("Legacy baseline refused: index drift")
    custom = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_trigger g JOIN pg_class t ON t.oid = g.tgrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public' AND NOT g.tgisinternal
        ) OR EXISTS (
            SELECT 1 FROM pg_class t JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public' AND (t.relrowsecurity OR t.relforcerowsecurity)
        )
    """)).scalar_one()
    if custom:
        raise RuntimeError("Legacy baseline refused: custom triggers or row security")
