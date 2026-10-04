"""${message}"""
from alembic import op
import sqlalchemy as sa

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "raise NotImplementedError('Review and implement this migration')"}


def downgrade():
    ${downgrades if downgrades else "raise RuntimeError('No data-safe downgrade; use a forward fix')"}
