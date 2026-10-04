"""Explicit, repeatable LOCAL demo seed; never part of schema migrations."""
import os
import sys

import sqlalchemy as sa

from app.migrations import migration_connection, require_head


def seed_demo(database_url):
    with migration_connection(database_url) as connection:
        require_head(connection)
        connection.execute(sa.text("""
            INSERT INTO public.catalog_source (id, title, review_status)
            VALUES ('starter-samples', 'Starter sample data (unverified)', 'demo')
            ON CONFLICT (id) DO NOTHING
        """))
        status = connection.execute(sa.text("SELECT review_status FROM public.catalog_source WHERE id='starter-samples'")).scalar_one()
        if status != "demo":
            raise RuntimeError("Demo seed refused: existing starter-samples source is not demo")
        connection.execute(sa.text("""
            INSERT INTO public.species (id, common_name_en, common_name_bn, category, source_id)
            VALUES ('demo-neem', 'Neem', 'নিম', 'tree', 'starter-samples'),
                   ('demo-okra', 'Okra', 'ঢেঁড়স', 'crop', 'starter-samples')
            ON CONFLICT (id) DO NOTHING
        """))


def main():
    try:
        seed_demo(os.environ.get("DATABASE_URL", ""))
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Demo seed failed ({type(exc).__name__}); transaction rolled back.", file=sys.stderr)
        return 1
    print("Demo seed completed; existing rows were not overwritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
