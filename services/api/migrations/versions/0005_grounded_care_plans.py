"""Reviewed care directives and owner-only immutable plan versions; no seed data."""
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
      CREATE TABLE public.plant_care_guidance (
        id text PRIMARY KEY,
        profile_id text NOT NULL REFERENCES public.plant_profile(id),
        topic text NOT NULL CHECK (topic IN ('soil_preparation','watering','nutrition','monitoring')),
        week_start integer NOT NULL CHECK (week_start BETWEEN 0 AND 12),
        week_end integer NOT NULL CHECK (week_end BETWEEN week_start AND 12),
        instruction_bn text NOT NULL CHECK (length(trim(instruction_bn)) BETWEEN 1 AND 800),
        instruction_en text NOT NULL CHECK (length(trim(instruction_en)) BETWEEN 1 AND 800),
        source_id text NOT NULL REFERENCES public.catalog_source(id),
        source_locator text NOT NULL CHECK (length(trim(source_locator)) BETWEEN 1 AND 1000),
        interpretation_note text NOT NULL CHECK (length(trim(interpretation_note)) BETWEEN 1 AND 1000),
        review_status text NOT NULL CHECK (review_status IN ('draft','reviewed')),
        reviewed_by text, reviewed_at date, valid_until date,
        CHECK ((topic='soil_preparation' AND week_start=0 AND week_end=0) OR
               (topic<>'soil_preparation' AND week_start>=1)),
        CHECK (review_status<>'reviewed' OR (length(trim(reviewed_by))>0 AND
               reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND valid_until IS NOT NULL)),
        CHECK (valid_until IS NULL OR (reviewed_at IS NOT NULL AND valid_until>reviewed_at))
      );
      CREATE INDEX plant_care_guidance_profile_idx ON public.plant_care_guidance(profile_id,id);
      CREATE INDEX plant_care_guidance_source_idx ON public.plant_care_guidance(source_id);
      CREATE TABLE public.care_plan (
        id uuid PRIMARY KEY,
        owner_id uuid NOT NULL REFERENCES public.grower_account(id) ON DELETE CASCADE,
        request_id uuid NOT NULL,
        request_hash text NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
        save_notice_version text NOT NULL CHECK (save_notice_version='care-plan-2026-10-04'),
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (owner_id,request_id), UNIQUE (id,owner_id)
      );
      CREATE INDEX care_plan_owner_idx ON public.care_plan(owner_id,id);
      CREATE TABLE public.care_plan_version (
        plan_id uuid NOT NULL, owner_id uuid NOT NULL,
        version integer NOT NULL CHECK (version>0),
        profile_id text NOT NULL REFERENCES public.plant_profile(id),
        fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
        conditions jsonb NOT NULL CHECK (jsonb_typeof(conditions)='object'),
        snapshot jsonb NOT NULL CHECK (jsonb_typeof(snapshot)='object' AND octet_length(snapshot::text)<=1048576),
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (plan_id,version),
        FOREIGN KEY (plan_id,owner_id) REFERENCES public.care_plan(id,owner_id) ON DELETE CASCADE
      );
      CREATE INDEX care_plan_version_owner_idx ON public.care_plan_version(owner_id,plan_id,version);
      CREATE INDEX care_plan_version_profile_idx ON public.care_plan_version(profile_id);
      CREATE FUNCTION public.prevent_care_version_update() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Care plan versions are immutable; append a version'; END; $$;
      CREATE TRIGGER care_version_immutable BEFORE UPDATE ON public.care_plan_version
        FOR EACH ROW EXECUTE FUNCTION public.prevent_care_version_update();
    ''')


def downgrade():
    raise RuntimeError('Care-plan rollback would delete private records and reviewed guidance; use a forward fix')
