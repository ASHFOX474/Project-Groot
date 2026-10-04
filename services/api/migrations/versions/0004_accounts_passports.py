"""Private accounts, explicit optional choices and owner-bound plant records."""
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
        CREATE TABLE public.grower_account (
          id uuid PRIMARY KEY,
          handle text NOT NULL UNIQUE CHECK (handle ~ '^[a-z0-9_]{3,32}$'),
          password_hash text NOT NULL,
          location_opt_in boolean NOT NULL DEFAULT false,
          community_opt_in boolean NOT NULL DEFAULT false,
          impact_opt_in boolean NOT NULL DEFAULT false,
          notice_version text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE public.account_session (
          token_hash text PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
          account_id uuid NOT NULL REFERENCES public.grower_account(id) ON DELETE CASCADE,
          expires_at timestamptz NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CHECK (expires_at > created_at)
        );
        CREATE INDEX account_session_owner_idx ON public.account_session(account_id);
        CREATE TABLE public.consent_event (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          account_id uuid NOT NULL REFERENCES public.grower_account(id) ON DELETE CASCADE,
          choices jsonb NOT NULL CHECK (jsonb_typeof(choices)='object'),
          notice_version text NOT NULL,
          recorded_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX consent_event_owner_idx ON public.consent_event(account_id,id);
        CREATE TABLE public.plant_passport (
          id uuid PRIMARY KEY,
          owner_id uuid NOT NULL REFERENCES public.grower_account(id) ON DELETE CASCADE,
          nickname text NOT NULL CHECK (length(trim(nickname)) BETWEEN 1 AND 80),
          species_name text NOT NULL CHECK (length(trim(species_name)) BETWEEN 1 AND 160),
          species_id text REFERENCES public.species(id),
          planted_on date NOT NULL,
          conditions jsonb NOT NULL CHECK (jsonb_typeof(conditions)='object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id,owner_id)
        );
        CREATE INDEX plant_passport_owner_idx ON public.plant_passport(owner_id,id);
        CREATE INDEX plant_passport_species_idx ON public.plant_passport(species_id);
        CREATE TABLE public.plant_care_event (
          id uuid PRIMARY KEY,
          passport_id uuid NOT NULL,
          owner_id uuid NOT NULL,
          kind text NOT NULL CHECK (kind IN ('watering','feeding','pruning','repotting','observation')),
          occurred_on date NOT NULL,
          note text NOT NULL CHECK (length(note)<=1000),
          recorded_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (passport_id,owner_id)
            REFERENCES public.plant_passport(id,owner_id) ON DELETE CASCADE
        );
        CREATE INDEX plant_care_timeline_idx ON public.plant_care_event(passport_id,owner_id,occurred_on,id);
        CREATE TABLE public.auth_rate_bucket (
          key_hash text PRIMARY KEY CHECK (key_hash ~ '^[0-9a-f]{64}$'),
          attempts integer NOT NULL CHECK (attempts>0),
          expires_at timestamptz NOT NULL
        );
        CREATE INDEX auth_rate_expiry_idx ON public.auth_rate_bucket(expires_at);
    ''')


def downgrade():
    raise RuntimeError('Account rollback would delete private records; use a forward fix')
