"""Add optional owner-scoped care retry identities, preserving legacy care."""
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE public.plant_care_event ADD COLUMN request_id uuid')
    op.execute('''CREATE UNIQUE INDEX plant_care_request_owner_idx
        ON public.plant_care_event(owner_id,request_id) WHERE request_id IS NOT NULL''')


def downgrade():
    raise RuntimeError('Removing care deduplication could duplicate synced records; use a forward fix')
