"""Add self-reported survival rewards and moderated community records."""
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
      ALTER TABLE public.grower_account
        ADD COLUMN is_moderator boolean NOT NULL DEFAULT false;

      CREATE TABLE public.community_profile (
        account_id uuid PRIMARY KEY REFERENCES public.grower_account(id) ON DELETE CASCADE,
        district text NOT NULL CHECK(district IN ('dhaka','chattogram','rajshahi','khulna','sylhet','rangpur','barishal','mymensingh')),
        public_alias text NOT NULL CHECK(length(trim(public_alias)) BETWEEN 3 AND 40),
        notice_version text NOT NULL CHECK(notice_version='community-2026-10-06'),
        updated_at timestamptz NOT NULL DEFAULT now()
      );

      CREATE TABLE public.community_post (
        id uuid PRIMARY KEY,
        owner_id uuid NOT NULL REFERENCES public.grower_account(id) ON DELETE CASCADE,
        district text CHECK(district IS NULL OR district IN ('dhaka','chattogram','rajshahi','khulna','sylhet','rangpur','barishal','mymensingh')),
        topic text NOT NULL CHECK(topic IN ('milestone','care','question','general')),
        body text NOT NULL CHECK(length(trim(body)) BETWEEN 1 AND 1000),
        status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','hidden')),
        created_at timestamptz NOT NULL DEFAULT now(),
        moderated_at timestamptz,
        moderated_by uuid REFERENCES public.grower_account(id) ON DELETE SET NULL
      );
      CREATE INDEX community_post_feed_idx ON public.community_post(status,created_at DESC,id DESC);
      CREATE INDEX community_post_owner_idx ON public.community_post(owner_id,created_at DESC,id DESC);
      CREATE INDEX community_post_district_idx ON public.community_post(district,status,created_at DESC);

      CREATE TABLE public.community_report (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        post_id uuid NOT NULL REFERENCES public.community_post(id) ON DELETE CASCADE,
        reporter_id uuid NOT NULL REFERENCES public.grower_account(id) ON DELETE CASCADE,
        reason text NOT NULL CHECK(reason IN ('harassment','unsafe_advice','privacy','spam','other')),
        details text NOT NULL DEFAULT '' CHECK(length(details)<=500),
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(post_id,reporter_id)
      );
      CREATE INDEX community_report_post_idx ON public.community_report(post_id,created_at);
    ''')


def downgrade():
    raise RuntimeError('Rewards/community rollback would delete posts, reports and moderation state')
