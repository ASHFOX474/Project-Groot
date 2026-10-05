"""Add owner/version-scoped task completion and bounded regional forecast cache."""
from alembic import op

revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('''
      CREATE TABLE public.quest_completion (
        plan_id uuid NOT NULL, owner_id uuid NOT NULL, version integer NOT NULL,
        quest_key text NOT NULL CHECK (quest_key ~ '^[a-z0-9:.-]{1,100}$'),
        completed_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY(plan_id,version,quest_key),
        FOREIGN KEY(plan_id,version) REFERENCES public.care_plan_version(plan_id,version) ON DELETE CASCADE,
        FOREIGN KEY(plan_id,owner_id) REFERENCES public.care_plan(id,owner_id) ON DELETE CASCADE
      );
      CREATE INDEX quest_completion_owner_idx ON public.quest_completion(owner_id,plan_id,version);
      CREATE TABLE public.plan_weather_preference (
        plan_id uuid NOT NULL, owner_id uuid NOT NULL, version integer NOT NULL,
        enabled boolean NOT NULL DEFAULT false,
        notice_version text NOT NULL CHECK(notice_version='weather-2026-10-05'),
        updated_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY(plan_id,version),
        FOREIGN KEY(plan_id,version) REFERENCES public.care_plan_version(plan_id,version) ON DELETE CASCADE,
        FOREIGN KEY(plan_id,owner_id) REFERENCES public.care_plan(id,owner_id) ON DELETE CASCADE
      );
      CREATE INDEX plan_weather_owner_idx ON public.plan_weather_preference(owner_id,plan_id,version);
      CREATE TABLE public.regional_forecast (
        district text PRIMARY KEY CHECK(district IN ('dhaka','chattogram','rajshahi','khulna','sylhet','rangpur','barishal','mymensingh')),
        attempted_at timestamptz NOT NULL,
        forecast jsonb CHECK(forecast IS NULL OR (jsonb_typeof(forecast)='object' AND octet_length(forecast::text)<=65536))
      );
    ''')


def downgrade():
    raise RuntimeError('Quest rollback would delete private records; use a forward fix')
