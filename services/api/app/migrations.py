"""Guarded, transactional Alembic commands for Groot's public schema."""
import argparse
from contextlib import contextmanager
from functools import lru_cache
import os
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from app.legacy_schema import validate_legacy

# Same database-wide lock for upgrades, baseline adoption, downgrade and demo seed.
LOCK_KEY = 719284601


def config():
    return Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))


@lru_cache(maxsize=1)
def head_revision():
    return ScriptDirectory.from_config(config()).get_current_head()


def postgres_url(value):
    try:
        url = make_url(value)
    except sa.exc.ArgumentError:
        raise ValueError("A PostgreSQL DATABASE_URL is required") from None
    if url.drivername not in ("postgresql", "postgresql+psycopg") or not url.database:
        raise ValueError("A PostgreSQL DATABASE_URL is required")
    return url.set(drivername="postgresql+psycopg")


@contextmanager
def migration_connection(database_url):
    engine = sa.create_engine(
        postgres_url(database_url), poolclass=sa.pool.NullPool, hide_parameters=True,
        connect_args={"connect_timeout": 5, "application_name": "groot-migrations"},
    )
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL search_path TO public")
            connection.exec_driver_sql("SET LOCAL lock_timeout TO '5s'")
            connection.exec_driver_sql("SET LOCAL statement_timeout TO '60s'")
            if not connection.execute(sa.text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": LOCK_KEY}).scalar_one():
                raise RuntimeError("Another Groot migration/seed command is running; retry later")
            yield connection
    finally:
        engine.dispose()


def current_revisions(connection):
    if not sa.inspect(connection).has_table("alembic_version", schema="public"):
        return ()
    return tuple(connection.exec_driver_sql("SELECT version_num FROM public.alembic_version ORDER BY version_num").scalars())


def require_head(connection):
    if current_revisions(connection) != (head_revision(),):
        raise RuntimeError("Database is not at migration head; run the documented upgrade procedure")


def run(action, database_url, target=None, *, confirm=False):
    if action in ("baseline", "downgrade") and not confirm:
        raise RuntimeError("Explicit --confirm is required; back up and review the procedure first")
    with migration_connection(database_url) as connection:
        cfg = config()
        cfg.attributes["connection"] = connection
        revisions = current_revisions(connection)
        if action == "baseline":
            if revisions:
                raise RuntimeError("Baseline refused: database already has migration history")
            validate_legacy(connection)
            command.stamp(cfg, "0001")
        elif action == "upgrade":
            tables = set(sa.inspect(connection).get_table_names(schema="public")) - {"alembic_version"}
            if not revisions and tables:
                raise RuntimeError("Unversioned database: back up, then run baseline --confirm")
            command.upgrade(cfg, target or "head")
        elif action == "downgrade":
            if not target:
                raise RuntimeError("An explicit downgrade revision is required")
            command.downgrade(cfg, target)
        elif action == "check":
            require_head(connection)
        elif action != "current":
            raise ValueError("Unknown migration action")
        return current_revisions(connection)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("upgrade", "current", "check", "baseline", "downgrade"))
    parser.add_argument("target", nargs="?")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    if args.target and args.action not in ("upgrade", "downgrade"):
        parser.error("Only upgrade/downgrade accepts a target")
    try:
        revisions = run(args.action, os.environ.get("DATABASE_URL", ""), args.target, confirm=args.confirm)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # Do not expose connection URLs, passwords, SQL parameters or row contents.
        print(f"Migration failed ({type(exc).__name__}); transaction rolled back. Inspect database/tool logs.", file=sys.stderr)
        return 1
    print("Database revision: " + (", ".join(revisions) or "unversioned"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
