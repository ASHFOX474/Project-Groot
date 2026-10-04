"""Original catalog schema. Legacy adoption must validate before stamping this revision."""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE public.catalog_source (
            id text PRIMARY KEY,
            title text NOT NULL,
            source_url text,
            checked_at date,
            review_status text NOT NULL CHECK (review_status IN ('demo', 'reviewed')),
            CONSTRAINT reviewed_source_has_reference CHECK (
                review_status <> 'reviewed' OR (source_url IS NOT NULL AND checked_at IS NOT NULL)
            ),
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE public.species (
            id text PRIMARY KEY,
            common_name_en text NOT NULL,
            common_name_bn text NOT NULL,
            category text NOT NULL CHECK (category IN ('crop', 'tree')),
            source_id text NOT NULL REFERENCES public.catalog_source(id),
            is_active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX species_active_name_idx ON public.species (common_name_en, id)
        WHERE is_active
    """)


def downgrade():
    raise RuntimeError("Baseline rollback would delete catalog data; use a forward fix")
