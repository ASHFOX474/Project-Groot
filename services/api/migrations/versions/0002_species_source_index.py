"""Index the source foreign key without changing any catalog rows."""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("species_source_id_idx", "species", ["source_id"], schema="public")


def downgrade():
    op.drop_index("species_source_id_idx", table_name="species", schema="public")
