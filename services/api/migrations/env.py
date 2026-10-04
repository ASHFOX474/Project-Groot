"""Use the connection/transaction/lock supplied by app.migrations, never a URL file."""
from alembic import context

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Use python -m app.migrations; direct Alembic execution is unsafe")

context.configure(connection=connection, version_table_schema="public")
with context.begin_transaction():
    context.run_migrations()
