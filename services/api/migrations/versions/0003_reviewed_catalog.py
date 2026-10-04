"""Add provenance/rights and scoped requirements; never rewrite legacy catalog rows."""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.catalog_source
          ADD COLUMN publisher text,
          ADD COLUMN access_status text NOT NULL DEFAULT 'unverified'
            CHECK (access_status IN ('public','login_required','unavailable','unverified')),
          ADD COLUMN reuse_status text NOT NULL DEFAULT 'permission_pending'
            CHECK (reuse_status IN ('open_license','permission_granted','permission_pending','restricted')),
          ADD COLUMN license_name text,
          ADD COLUMN license_url text,
          ADD COLUMN rights_note text,
          ADD COLUMN attribution text,
          ADD COLUMN reviewed_by text,
          ADD COLUMN valid_until date,
          ADD CONSTRAINT cleared_reuse_has_evidence CHECK (
            reuse_status NOT IN ('open_license','permission_granted') OR
            (publisher IS NOT NULL AND license_name IS NOT NULL AND license_url IS NOT NULL
             AND rights_note IS NOT NULL AND attribution IS NOT NULL AND reviewed_by IS NOT NULL
             AND checked_at IS NOT NULL AND valid_until IS NOT NULL AND valid_until > checked_at))
    """)
    op.execute("ALTER TABLE public.species ADD COLUMN scientific_name text")
    op.execute("""
        CREATE TABLE public.catalog_import (
            sha256 text PRIMARY KEY CHECK (sha256 ~ '^[0-9a-f]{64}$'),
            bundle_id text NOT NULL UNIQUE,
            imported_at timestamptz NOT NULL DEFAULT now(),
            manifest jsonb NOT NULL CHECK (jsonb_typeof(manifest)='object')
        )
    """)
    op.execute("""
        CREATE TABLE public.plant_profile (
            id text PRIMARY KEY,
            species_id text NOT NULL REFERENCES public.species(id),
            import_sha256 text NOT NULL REFERENCES public.catalog_import(sha256),
            country_code text NOT NULL CHECK (country_code='BD'),
            locality text NOT NULL,
            growing_context text NOT NULL CHECK (growing_context IN ('open_ground','container','forestry')),
            variety text NOT NULL,
            review_status text NOT NULL CHECK (review_status IN ('draft','reviewed')),
            reviewed_by text,
            reviewed_at date,
            valid_until date,
            limitations text NOT NULL,
            CONSTRAINT reviewed_profile_has_evidence CHECK (
              review_status <> 'reviewed' OR
              (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND valid_until IS NOT NULL AND valid_until > reviewed_at))
        )
    """)
    op.execute("""
        CREATE TABLE public.plant_requirement (
            profile_id text NOT NULL REFERENCES public.plant_profile(id),
            key text NOT NULL CHECK (key IN ('soil_ph','soil_texture','drainage','sunlight','spacing_cm','temperature_c','sowing_windows')),
            value jsonb NOT NULL,
            source_id text NOT NULL REFERENCES public.catalog_source(id),
            source_locator text NOT NULL CHECK (length(trim(source_locator))>0),
            interpretation_note text NOT NULL CHECK (length(trim(interpretation_note))>0),
            PRIMARY KEY (profile_id,key)
        )
    """)
    op.execute('CREATE INDEX plant_profile_species_idx ON public.plant_profile(species_id)')
    op.execute('CREATE INDEX plant_profile_import_idx ON public.plant_profile(import_sha256)')
    op.execute('CREATE INDEX plant_requirement_source_idx ON public.plant_requirement(source_id)')
    op.execute("""
        CREATE VIEW public.recommendation_profile AS
        SELECT p.* FROM public.plant_profile p
        JOIN public.species s ON s.id=p.species_id
        JOIN public.catalog_source origin ON origin.id=s.source_id
        WHERE s.is_active AND s.id NOT LIKE 'demo-%' AND origin.id <> 'starter-samples'
          AND p.review_status='reviewed'
          AND p.reviewed_at <= (now() AT TIME ZONE 'Asia/Dhaka')::date
          AND p.valid_until >= (now() AT TIME ZONE 'Asia/Dhaka')::date
          AND origin.review_status='reviewed' AND origin.access_status='public'
          AND origin.reuse_status IN ('open_license','permission_granted')
          AND origin.checked_at <= (now() AT TIME ZONE 'Asia/Dhaka')::date
          AND origin.valid_until >= (now() AT TIME ZONE 'Asia/Dhaka')::date
          AND EXISTS (SELECT 1 FROM public.plant_requirement r WHERE r.profile_id=p.id)
          AND NOT EXISTS (
            SELECT 1 FROM public.plant_requirement r
            JOIN public.catalog_source evidence ON evidence.id=r.source_id
            WHERE r.profile_id=p.id AND (
              evidence.id = 'starter-samples'
              OR evidence.review_status <> 'reviewed' OR evidence.access_status <> 'public'
              OR evidence.reuse_status NOT IN ('open_license','permission_granted')
              OR evidence.checked_at IS NULL OR evidence.valid_until IS NULL
              OR evidence.checked_at > (now() AT TIME ZONE 'Asia/Dhaka')::date
              OR evidence.valid_until < (now() AT TIME ZONE 'Asia/Dhaka')::date
            )
          )
    """)


def downgrade():
    # Even empty tables may have source/species metadata written by an operator.
    raise RuntimeError('Reviewed catalog rollback would delete provenance; use a forward fix')
