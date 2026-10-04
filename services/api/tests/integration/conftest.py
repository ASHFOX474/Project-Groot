"""Create/drop only databases allocated by this fixture on the disposable server."""
import os
from pathlib import Path
import uuid

import psycopg
from psycopg import sql
import pytest
from sqlalchemy.engine import make_url


@pytest.fixture
def database_url():
    value = os.environ.get("TEST_DATABASE_URL", "")
    if not value or make_url(value).database != "groot_tests":
        pytest.fail("Use sh scripts/check-db.sh; TEST_DATABASE_URL must select groot_tests")
    name = "groot_test_" + uuid.uuid4().hex
    with psycopg.connect(value, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
    try:
        yield make_url(value).set(database=name).render_as_string(hide_password=False)
    finally:
        with psycopg.connect(value, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def legacy_database(database_url):
    root = Path(__file__).resolve().parents[1] / "fixtures"
    if not root.exists():
        root = Path(__file__).resolve().parents[4] / "db" / "init"
    with psycopg.connect(database_url) as connection:
        for name in ("001_schema.sql", "002_demo_seed.sql"):
            connection.execute((root / name).read_text(encoding="utf-8"))
        connection.execute("UPDATE species SET common_name_en='User Neem', is_active=false WHERE id='demo-neem'")
        connection.execute("INSERT INTO species (id,common_name_en,common_name_bn,category,source_id) VALUES ('user-plant','User Plant','নিজের গাছ','tree','starter-samples')")
    return database_url
