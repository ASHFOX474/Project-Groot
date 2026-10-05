"""Private bounded photo check-ins and independent feature consent."""
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
      CREATE TABLE public.photo_consent (
        passport_id uuid PRIMARY KEY, owner_id uuid NOT NULL,
        storage boolean NOT NULL DEFAULT false,
        health boolean NOT NULL DEFAULT false CHECK (NOT health OR storage),
        notice_version text NOT NULL, generation bigint NOT NULL DEFAULT 1,
        updated_at timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY(passport_id,owner_id) REFERENCES public.plant_passport(id,owner_id) ON DELETE CASCADE
      );
      CREATE INDEX photo_consent_owner_idx ON public.photo_consent(owner_id,passport_id);
      CREATE TABLE public.photo_consent_event (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        passport_id uuid NOT NULL, owner_id uuid NOT NULL,
        storage boolean NOT NULL, health boolean NOT NULL CHECK (NOT health OR storage),
        notice_version text NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY(passport_id,owner_id) REFERENCES public.plant_passport(id,owner_id) ON DELETE CASCADE
      );
      CREATE INDEX photo_consent_event_owner_idx ON public.photo_consent_event(owner_id,passport_id,id);
      CREATE TABLE public.plant_photo (
        id uuid PRIMARY KEY, passport_id uuid NOT NULL, owner_id uuid NOT NULL,
        request_id uuid NOT NULL, fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
        observed_on date NOT NULL, uploaded_at timestamptz NOT NULL DEFAULT now(),
        caption text NOT NULL CHECK(length(caption)<=500),
        symptoms jsonb NOT NULL CHECK(jsonb_typeof(symptoms)='array'),
        jpeg bytea NOT NULL CHECK(octet_length(jpeg) BETWEEN 1 AND 524288),
        width integer NOT NULL CHECK(width BETWEEN 1 AND 1280),
        height integer NOT NULL CHECK(height BETWEEN 1 AND 1280),
        assistance jsonb CHECK(assistance IS NULL OR jsonb_typeof(assistance)='object'),
        UNIQUE(owner_id,request_id),
        FOREIGN KEY(passport_id,owner_id) REFERENCES public.plant_passport(id,owner_id) ON DELETE CASCADE
      );
      CREATE INDEX plant_photo_timeline_idx ON public.plant_photo(owner_id,passport_id,observed_on DESC,id DESC);
    ''')


def downgrade():
    raise RuntimeError('Photo rollback would delete private photos/consent; use a forward fix')
