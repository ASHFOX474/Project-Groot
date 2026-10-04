from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import psycopg
import pytest
import sqlalchemy as sa

from app.database import CatalogRepository
from app.main import create_app
from app import migrations
from app.migrations import LOCK_KEY, config, run
from app.seed_demo import seed_demo

pytestmark = pytest.mark.integration


def query(url, statement):
    with psycopg.connect(url) as connection:
        return connection.execute(statement).fetchall()


def snapshot(url):
    # Compare all original values across additive schema changes, not tuple width.
    return query(url, 'SELECT id,title,source_url,checked_at,review_status,created_at FROM catalog_source ORDER BY id'), query(url, 'SELECT id,common_name_en,common_name_bn,category,source_id,is_active,created_at FROM species ORDER BY id')


def test_fresh_upgrade_idempotency_and_explicit_demo_seed(database_url):
    assert run('current', database_url) == ()
    with pytest.raises(RuntimeError, match='not at migration head'):
        run('check', database_url)
    assert run('upgrade', database_url) == ('0005',)
    assert query(database_url, 'SELECT count(*) FROM species') == [(0,)]
    seed_demo(database_url)
    before = snapshot(database_url)
    run('upgrade', database_url)
    seed_demo(database_url)
    assert snapshot(database_url) == before
    assert run('check', database_url) == ('0005',)
    assert query(database_url, "SELECT indexname FROM pg_indexes WHERE indexname='species_source_id_idx'")
    with pytest.raises(RuntimeError, match='would delete private records'):
        run('downgrade', database_url, 'base', confirm=True)
    assert run('current', database_url) == ('0005',)
    assert query(database_url, "SELECT indexname FROM pg_indexes WHERE indexname='species_source_id_idx'")
    assert snapshot(database_url) == before


def test_legacy_adoption_upgrade_rollback_preserves_all_rows(legacy_database):
    url = legacy_database
    before = snapshot(url)
    with pytest.raises(RuntimeError, match='Unversioned'):
        run('upgrade', url)
    with pytest.raises(RuntimeError, match='--confirm'):
        run('baseline', url)
    assert run('baseline', url, confirm=True) == ('0001',)
    with pytest.raises(RuntimeError, match='already has migration history'):
        run('baseline', url, confirm=True)
    assert snapshot(url) == before
    run('upgrade', url, '0002')
    assert snapshot(url) == before
    with pytest.raises(RuntimeError, match='--confirm'):
        run('downgrade', url, '0001')
    assert run('downgrade', url, '0001', confirm=True) == ('0001',)
    assert not query(url, "SELECT indexname FROM pg_indexes WHERE indexname='species_source_id_idx'")
    assert snapshot(url) == before
    with pytest.raises(RuntimeError, match='would delete catalog data'):
        run('downgrade', url, 'base', confirm=True)
    assert run('current', url) == ('0001',)
    run('upgrade', url, '0002')
    assert snapshot(url) == before
    run('upgrade', url)
    seed_demo(url)
    assert snapshot(url) == before


@pytest.mark.parametrize('statement', [
    'ALTER TABLE species ALTER COLUMN common_name_bn DROP NOT NULL',
    'ALTER TABLE species ALTER COLUMN is_active SET DEFAULT false',
    'ALTER TABLE species DROP CONSTRAINT species_source_id_fkey',
    'ALTER TABLE species DROP CONSTRAINT species_category_check',
    'ALTER TABLE catalog_source DROP CONSTRAINT reviewed_source_has_reference',
    'DROP INDEX species_active_name_idx',
    'DROP INDEX species_active_name_idx; CREATE INDEX species_active_name_idx ON species (id)',
    'ALTER TABLE species DROP CONSTRAINT species_source_id_fkey; ALTER TABLE species ADD CONSTRAINT species_source_id_fkey FOREIGN KEY (source_id) REFERENCES catalog_source(id) ON DELETE CASCADE',
    'CREATE FUNCTION baseline_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$; CREATE TRIGGER custom BEFORE UPDATE ON species FOR EACH ROW EXECUTE FUNCTION baseline_trigger()',
    'ALTER TABLE species ENABLE ROW LEVEL SECURITY',
    'CREATE TABLE unrelated (id integer)',
    'CREATE VIEW catalog_view AS SELECT id FROM species',
    'ALTER TABLE species ADD COLUMN unexpected text',
    "ALTER TABLE species DROP CONSTRAINT species_category_check; ALTER TABLE species ADD CONSTRAINT species_category_check CHECK (category IN ('crop','tree')) NOT VALID",
])
def test_legacy_drift_refused_without_stamping_or_rewriting(legacy_database, statement):
    with psycopg.connect(legacy_database) as connection:
        connection.execute(statement)
    before = snapshot(legacy_database)
    with pytest.raises(RuntimeError, match='Legacy baseline refused'):
        run('baseline', legacy_database, confirm=True)
    assert run('current', legacy_database) == ()
    assert snapshot(legacy_database) == before
    assert query(legacy_database, "SELECT to_regclass('public.alembic_version')") == [(None,)]


def test_partial_legacy_schema_refused(database_url):
    with psycopg.connect(database_url) as connection:
        connection.execute('CREATE TABLE species (id text PRIMARY KEY)')
    with pytest.raises(RuntimeError, match='Legacy baseline refused'):
        run('baseline', database_url, confirm=True)


def test_failed_migration_rolls_back_schema_and_version(database_url, tmp_path, monkeypatch):
    run('upgrade', database_url)
    seed_demo(database_url)
    before = snapshot(database_url)
    source = Path(config().get_main_option('script_location'))
    destination = tmp_path / 'migrations'
    shutil.copytree(source, destination)
    (destination / 'versions' / '0006_failure.py').write_text('''
from alembic import op
revision = "0006"
down_revision = "0005"
def upgrade():
    op.execute("CREATE TABLE public.should_not_survive (id integer)")
    op.execute("UPDATE public.species SET common_name_bn='changed'")
    op.execute("SELECT 1/0")
def downgrade():
    pass
''')
    cfg = Config()
    cfg.set_main_option('script_location', str(destination))
    monkeypatch.setattr(migrations, 'config', lambda: cfg)
    with pytest.raises(sa.exc.DBAPIError):
        run('upgrade', database_url)
    assert run('current', database_url) == ('0005',)
    assert query(database_url, "SELECT to_regclass('public.should_not_survive')") == [(None,)]
    assert snapshot(database_url) == before


def test_concurrent_migration_is_refused(database_url):
    with psycopg.connect(database_url) as connection:
        connection.execute('SELECT pg_advisory_xact_lock(%s)', (LOCK_KEY,))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(run, 'upgrade', database_url)
            with pytest.raises(RuntimeError, match='Another Groot migration'):
                future.result(timeout=10)
    assert run('upgrade', database_url) == ('0005',)


@pytest.mark.parametrize('statement,error', [
    ("INSERT INTO species (id,common_name_en,common_name_bn,category,source_id) VALUES ('x','X','এক্স','tree','missing')", psycopg.errors.ForeignKeyViolation),
    ("UPDATE species SET category='invalid'", psycopg.errors.CheckViolation),
    ("UPDATE species SET common_name_bn=NULL", psycopg.errors.NotNullViolation),
    ("UPDATE catalog_source SET review_status='reviewed'", psycopg.errors.CheckViolation),
    ("DELETE FROM catalog_source", psycopg.errors.ForeignKeyViolation),
    ("INSERT INTO catalog_source (id,title,review_status) VALUES ('starter-samples','dup','demo')", psycopg.errors.UniqueViolation),
])
def test_catalog_constraints_enforced(database_url, statement, error):
    run('upgrade', database_url)
    seed_demo(database_url)
    before = snapshot(database_url)
    with pytest.raises(error), psycopg.connect(database_url) as connection:
        connection.execute(statement)
    assert snapshot(database_url) == before


def test_real_api_uses_database_filters_sorting_and_source_status(database_url, monkeypatch):
    run('upgrade', database_url)
    seed_demo(database_url)
    with psycopg.connect(database_url) as connection:
        connection.execute("UPDATE species SET is_active=false WHERE id='demo-okra'")
        connection.execute("INSERT INTO catalog_source (id,title,review_status,source_url,checked_at) VALUES ('reviewed','Reviewed test source','reviewed','https://example.test/source',CURRENT_DATE)")
        connection.execute("INSERT INTO species (id,common_name_en,common_name_bn,category,source_id) VALUES ('r','A Plant','গাছ','tree','reviewed')")
    monkeypatch.setenv('DATABASE_URL', database_url)
    with TestClient(create_app()) as client:
        assert client.get('/health/ready').status_code == 200
        response = client.get('/v1/catalog/species')
    assert response.status_code == 200
    assert [item['id'] for item in response.json()] == ['r', 'demo-neem']
    assert response.json()[0]['evidence_status'] == 'reviewed'
    assert response.json()[1]['common_name_bn'] == 'নিম'


def test_readiness_fails_for_missing_or_pending_migrations(database_url, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', database_url)
    client = TestClient(create_app())
    assert client.get('/health/live').status_code == 200
    assert client.get('/health/ready').status_code == 503
    assert client.get('/v1/catalog/species').status_code == 503
    run('upgrade', database_url, '0001')
    assert client.get('/health/ready').status_code == 503
    run('upgrade', database_url)
    assert client.get('/health/ready').status_code == 200
    assert client.get('/v1/catalog/species').json() == []


def test_catalog_limit_and_connection_configuration(database_url):
    with pytest.raises(RuntimeError, match='not configured'):
        CatalogRepository('').ping()
    run('upgrade', database_url)
    seed_demo(database_url)
    with psycopg.connect(database_url) as connection:
        connection.execute("""INSERT INTO species (id,common_name_en,common_name_bn,category,source_id)
            SELECT 'bulk-'||n, 'Bulk '||lpad(n::text,3,'0'), 'গাছ', 'tree', 'starter-samples'
            FROM generate_series(1,110) AS n""")
    assert len(CatalogRepository(database_url).list_species()) == 100


def test_demo_seed_requires_head_and_refuses_reviewed_collision(database_url):
    with pytest.raises(RuntimeError, match='not at migration head'):
        seed_demo(database_url)
    run('upgrade', database_url)
    with psycopg.connect(database_url) as connection:
        connection.execute("INSERT INTO catalog_source (id,title,review_status,source_url,checked_at) VALUES ('starter-samples','Real source','reviewed','https://example.test',CURRENT_DATE)")
    before = snapshot(database_url)
    with pytest.raises(RuntimeError, match='not demo'):
        seed_demo(database_url)
    assert snapshot(database_url) == before


def test_direct_alembic_execution_is_guarded(database_url):
    with pytest.raises(RuntimeError, match='direct Alembic execution is unsafe'):
        command.upgrade(config(), 'head')


def test_cli_status_errors_and_confirmation(database_url, monkeypatch, capsys):
    monkeypatch.setenv('DATABASE_URL', database_url)
    assert migrations.main(['current']) == 0
    assert 'unversioned' in capsys.readouterr().out
    assert migrations.main(['check']) == 1
    assert 'not at migration head' in capsys.readouterr().err
    assert migrations.main(['upgrade']) == 0
    assert migrations.main(['downgrade', '0001']) == 1
    assert migrations.main(['downgrade', '0001', '--confirm']) == 1
    assert migrations.main(['downgrade', '--confirm']) == 1
    assert migrations.main(['downgrade', 'base', '--confirm']) == 1
    with pytest.raises(ValueError, match='Unknown migration action'):
        run('invalid', database_url)
    with pytest.raises(SystemExit):
        migrations.main(['check', '0001'])
