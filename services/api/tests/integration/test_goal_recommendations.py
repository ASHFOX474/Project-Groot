"""Real DB: reuse the eligibility boundary; no goals/location/audio are stored."""
from copy import deepcopy

from fastapi.testclient import TestClient
import psycopg
import pytest

from app.accounts import AccountRepository
from app.catalog_bundle import CatalogBundle, today_bd
from app.catalog_import import import_bundle
from app.main import create_app
from app.migrations import run
from app.seed_demo import seed_demo
from tests.test_catalog_bundle import valid_bundle
from tests.test_recommendations import candidate, goal

pytestmark = pytest.mark.integration


@pytest.fixture
def client(database_url, monkeypatch):
    run('upgrade', database_url)
    monkeypatch.setenv('DATABASE_URL', database_url)
    monkeypatch.setenv('APP_ENV', 'development')
    with TestClient(create_app()) as value:
        yield value


def register(client):
    result = client.post('/v1/accounts/register', json={
        'handle': 'goal_test', 'password': 'Local goal test passphrase!', 'notice_version': '2026-10-04'})
    assert result.status_code == 201
    return {'Authorization': 'Bearer ' + result.json()['access_token']}


def approved_fixture(database_url):
    bundle = valid_bundle()
    profile = bundle['plants'][0]['profiles'][0]
    profile.update(locality='district:dhaka', growing_context='open_ground')
    profile['requirements'] = [
        {key: value for key, value in fact.items() if key in {'key', 'value', 'source_id', 'source_locator', 'interpretation_note'}}
        for fact in candidate()['requirements']]
    import_bundle(CatalogBundle.model_validate(bundle), database_url)


def test_goal_is_private_transient_and_demo_is_excluded(client, database_url):
    seed_demo(database_url)
    headers = register(client)
    payload = goal().model_dump(mode='json')
    assert client.post('/v1/goals/recommendations', json=payload).status_code == 401
    response = client.post('/v1/goals/recommendations', headers=headers, json=payload)
    assert response.status_code == 200 and response.json()['status'] == 'no_reviewed_data'
    assert response.json()['recommendations'] == []
    assert response.headers['cache-control'] == 'no-store'
    assert payload['goal'] not in response.text and 'goal_test' not in response.text
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM plant_passport').fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='plant_goal'").fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM species').fetchone()[0] == 2
    assert client.post('/v1/accounts/logout', headers=headers).status_code == 204
    assert client.post('/v1/goals/recommendations', headers=headers, json=payload).status_code == 401


def test_approved_fixture_matches_then_rights_revocation_excludes_it(client, database_url):
    approved_fixture(database_url)
    headers = register(client)
    payload = goal(planting_date=today_bd().replace(month=10, day=4)).model_dump(mode='json')
    response = client.post('/v1/goals/recommendations', headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()['recommendations'][0]['sources'][0]['source_url'] == 'https://example.test/facts'
    assert response.json()['status'] in {'matches_found', 'needs_details'}
    with psycopg.connect(database_url) as db:
        db.execute("UPDATE catalog_source SET reuse_status='permission_pending' WHERE id='test-source'")
    response = client.post('/v1/goals/recommendations', headers=headers, json=payload)
    assert response.json()['status'] == 'no_reviewed_data' and response.json()['recommendations'] == []


def test_goal_privacy_validation_bounds_tls_and_unavailable_data(client, database_url, monkeypatch):
    headers = register(client)
    payload = goal().model_dump(mode='json')
    invalid = deepcopy(payload)
    invalid['location']['latitude'] = 23.7
    invalid['goal'] = 'Never echo this private transcript'
    response = client.post('/v1/goals/recommendations', headers=headers, json=invalid)
    assert response.status_code == 422 and invalid['goal'] not in response.text
    assert client.post('/v1/goals/recommendations', headers=headers, content=b'x' * 17000).status_code == 413
    monkeypatch.setenv('APP_ENV', 'production')
    assert client.post('/v1/goals/recommendations', headers=headers, json=payload).status_code == 403
    monkeypatch.setenv('APP_ENV', 'development')
    with psycopg.connect(database_url) as db:
        db.execute('DROP VIEW recommendation_profile')  # disposable test DB only
    response = client.post('/v1/goals/recommendations', headers=headers, json=payload)
    assert response.status_code == 503


def test_malformed_citation_fails_closed(client, database_url):
    approved_fixture(database_url)
    headers = register(client)
    with psycopg.connect(database_url) as db:
        db.execute("UPDATE catalog_source SET source_url='https://user:private@example.test/data'")
    response = client.post('/v1/goals/recommendations', headers=headers, json=goal().model_dump(mode='json'))
    assert response.status_code == 503 and 'private' not in response.text


def test_session_expiry_is_checked_again_before_return(client, database_url, monkeypatch):
    headers = register(client)
    original = AccountRepository.recommendation_candidates_from

    def expire(connection):
        rows = original(connection)
        # Within this fixture-owned transaction, simulate expiry after first check.
        connection.execute("UPDATE account_session SET created_at=now()-interval '2 hours',expires_at=now()-interval '1 hour'")
        return rows

    monkeypatch.setattr(AccountRepository, 'recommendation_candidates_from', staticmethod(expire))
    assert client.post('/v1/goals/recommendations', headers=headers, json=goal().model_dump(mode='json')).status_code == 401
