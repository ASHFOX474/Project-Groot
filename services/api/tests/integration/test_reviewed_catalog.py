import copy
from datetime import date, timedelta
import json
from pathlib import Path

from fastapi.testclient import TestClient
import psycopg
import pytest
import sqlalchemy as sa

from app.catalog_bundle import CatalogBundle, read_bundle
from app.catalog_import import import_bundle
from app.database import CatalogRepository
from app.main import create_app
from app.migrations import run
from app.seed_demo import seed_demo
from tests.test_catalog_bundle import valid_bundle

pytestmark = pytest.mark.integration


def query(url, sql):
    with psycopg.connect(url) as connection:
        return connection.execute(sql).fetchall()


def apply(url, value=None):
    return import_bundle(CatalogBundle.model_validate(value or valid_bundle()), url)


def test_reviewed_import_is_atomic_idempotent_and_traceable(database_url, monkeypatch):
    run('upgrade', database_url)
    seed_demo(database_url)
    before = query(database_url, "SELECT * FROM species WHERE source_id='starter-samples' ORDER BY id")
    first = apply(database_url)
    assert not first['already_imported']
    assert apply(database_url) == {'sha256': first['sha256'], 'already_imported': True}
    assert query(database_url, 'SELECT count(*) FROM catalog_import') == [(1,)]
    assert query(database_url, "SELECT * FROM species WHERE source_id='starter-samples' ORDER BY id") == before
    monkeypatch.setenv('DATABASE_URL', database_url)
    with TestClient(create_app()) as client:
        response = client.get('/v1/catalog/recommendation-candidates')
    assert response.status_code == 200
    item = response.json()[0]
    assert item['species_id'] == 'test-okra'
    assert item['common_name_bn'] == 'ঢেঁড়স'
    assert item['import_sha256'] == first['sha256']
    assert item['requirements'][0]['source_url'] == 'https://example.test/facts'
    assert item['requirements'][0]['license_name'] == 'CC-BY-4.0'
    assert item['requirements'][0]['source_locator']
    assert len(CatalogRepository(database_url).list_species()) == 3  # preview retained


@pytest.mark.parametrize('statement', [
    "UPDATE catalog_source SET reuse_status='permission_pending' WHERE id='test-source'",
    "UPDATE catalog_source SET reuse_status='restricted' WHERE id='test-source'",
    "UPDATE catalog_source SET access_status='login_required' WHERE id='test-source'",
    "UPDATE catalog_source SET review_status='demo' WHERE id='test-source'",
    "UPDATE catalog_source SET checked_at=CURRENT_DATE-100,valid_until=CURRENT_DATE-1 WHERE id='test-source'",
    "UPDATE catalog_source SET checked_at=CURRENT_DATE+10,valid_until=CURRENT_DATE+20 WHERE id='test-source'",
    "UPDATE plant_profile SET review_status='draft'",
    "UPDATE plant_profile SET reviewed_at=CURRENT_DATE-100,valid_until=CURRENT_DATE-1",
    "UPDATE plant_profile SET reviewed_at=CURRENT_DATE+10,valid_until=CURRENT_DATE+20",
    "UPDATE species SET is_active=false WHERE id='test-okra'",
    "DELETE FROM plant_requirement",
])
def test_live_eligibility_revocation_and_expiry_are_fail_closed(database_url, statement):
    run('upgrade', database_url)
    apply(database_url)
    assert len(CatalogRepository(database_url).list_recommendation_candidates()) == 1
    with psycopg.connect(database_url) as connection:
        connection.execute(statement)
    assert CatalogRepository(database_url).list_recommendation_candidates() == []


def test_every_claim_source_must_be_cleared_not_just_primary_source(database_url):
    run('upgrade', database_url)
    value = valid_bundle()
    extra = copy.deepcopy(value['sources'][0])
    extra.update(id='extra-source', reuse_status='permission_pending')
    value['sources'].append(extra)
    value['plants'][0]['profiles'][0]['requirements'][0]['source_id'] = 'extra-source'
    apply(database_url, value)
    assert CatalogRepository(database_url).list_recommendation_candidates() == []
    with psycopg.connect(database_url) as connection:
        connection.execute("UPDATE catalog_source SET reuse_status='open_license' WHERE id='extra-source'")
    assert len(CatalogRepository(database_url).list_recommendation_candidates()) == 1


def test_demo_origin_stays_excluded_even_if_old_status_is_changed(database_url):
    run('upgrade', database_url)
    seed_demo(database_url)
    result = apply(database_url)
    with psycopg.connect(database_url) as connection:
        connection.execute("UPDATE plant_profile SET species_id='demo-neem'")
        connection.execute("""UPDATE catalog_source SET review_status='reviewed',
          source_url='https://example.test/demo',checked_at=CURRENT_DATE,publisher='Test',
          license_name='Test',license_url='https://example.test/license',rights_note='Test',
          attribution='Test',reviewed_by='Test',valid_until=CURRENT_DATE+30,
          access_status='public',reuse_status='open_license' WHERE id='starter-samples'""")
    assert result['sha256']
    assert CatalogRepository(database_url).list_recommendation_candidates() == []
    with psycopg.connect(database_url) as connection:
        connection.execute("UPDATE species SET id='old-sample' WHERE id='demo-okra'")
        connection.execute("UPDATE plant_profile SET species_id='old-sample'")
    assert CatalogRepository(database_url).list_recommendation_candidates() == []


def test_conflicts_refuse_without_partial_changes_or_overwriting(database_url):
    run('upgrade', database_url)
    first = valid_bundle()
    apply(database_url, first)
    changed = copy.deepcopy(first)
    changed['plants'][0]['common_name_en'] = 'Overwritten'
    with pytest.raises(RuntimeError, match='different content'):
        apply(database_url, changed)
    changed['bundle_id'] = 'test-catalog-v2'
    changed['sources'][0]['id'] = 'new-source'
    changed['plants'][0]['source_id'] = 'new-source'
    changed['plants'][0]['profiles'][0]['requirements'][0]['source_id'] = 'new-source'
    with pytest.raises(sa.exc.IntegrityError):
        apply(database_url, changed)
    assert query(database_url, 'SELECT count(*) FROM catalog_import') == [(1,)]
    assert query(database_url, "SELECT id FROM catalog_source WHERE id='new-source'") == []
    assert query(database_url, "SELECT common_name_en FROM species WHERE id='test-okra'") == [('Okra',)]


def test_pending_import_and_checked_in_drafts_never_become_candidates(database_url):
    run('upgrade', database_url)
    path = Path(__file__).resolve().parents[2] / 'catalog' / 'bangladesh-starter-v1.json'
    bundle = read_bundle(path)
    result = import_bundle(bundle, database_url)
    assert not result['already_imported']
    assert query(database_url, 'SELECT count(*) FROM plant_requirement') == [(11,)]
    assert CatalogRepository(database_url).list_recommendation_candidates() == []
    with pytest.raises(RuntimeError, match='would delete private records'):
        run('downgrade', database_url, '0002', confirm=True)
    assert query(database_url, 'SELECT count(*) FROM plant_requirement') == [(11,)]
    assert run('current', database_url) == ('0005',)


def test_import_requires_migration_head(database_url):
    with pytest.raises(RuntimeError, match='not at migration head'):
        apply(database_url)
    run('upgrade', database_url, '0002')
    with pytest.raises(RuntimeError, match='not at migration head'):
        apply(database_url)


def test_invalid_direct_db_requirement_fails_closed(database_url, monkeypatch):
    run('upgrade', database_url)
    apply(database_url)
    with psycopg.connect(database_url) as connection:
        connection.execute("UPDATE plant_requirement SET value='{" + '"min":9,"max":2' + "}'::jsonb")
    monkeypatch.setenv('DATABASE_URL', database_url)
    with TestClient(create_app()) as client:
        assert client.get('/v1/catalog/recommendation-candidates').status_code == 503


@pytest.mark.parametrize('statement', [
    "UPDATE catalog_source SET license_url=NULL WHERE id='test-source'",
    "UPDATE catalog_source SET valid_until=NULL WHERE id='test-source'",
    "UPDATE plant_profile SET valid_until=NULL",
    "UPDATE plant_profile SET reviewed_by=NULL",
    "UPDATE plant_requirement SET source_id='missing'",
    "UPDATE plant_requirement SET key='pesticide_dose'",
    "UPDATE plant_profile SET country_code='US'",
])
def test_database_provenance_constraints(database_url, statement):
    run('upgrade', database_url)
    apply(database_url)
    with pytest.raises(psycopg.Error), psycopg.connect(database_url) as connection:
        connection.execute(statement)
    assert len(CatalogRepository(database_url).list_recommendation_candidates()) == 1
