from datetime import timedelta
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import time

from fastapi.testclient import TestClient
import psycopg
import pytest

from app.accounts import AccountRepository, get_account_repository, token_digest
from app.catalog_bundle import today_bd
from app.main import create_app
from app.migrations import run
from app.seed_demo import seed_demo

pytestmark = pytest.mark.integration
PASSWORD = 'my private test passphrase'


@pytest.fixture
def client(database_url, monkeypatch):
    run('upgrade', database_url)
    seed_demo(database_url)
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('DATABASE_URL', database_url)
    app = create_app()
    app.dependency_overrides[get_account_repository] = lambda: AccountRepository(database_url)
    with TestClient(app) as value:
        yield value


def register(client, handle='grower'):
    response = client.post('/v1/accounts/register', json={
        'handle': handle, 'password': PASSWORD, 'notice_version': '2026-10-04'})
    assert response.status_code == 201, response.text
    value = response.json()
    assert PASSWORD not in response.text and 'password_hash' not in response.text
    return value, {'Authorization': 'Bearer ' + value['access_token']}


def plant(**changes):
    return {'nickname': 'আমার ঢেঁড়স', 'species_name': 'Okra', 'species_id': None,
            'planted_on': (today_bd() - timedelta(days=10)).isoformat(),
            'conditions': {'growing_context': 'container', 'soil': 'নিজের মাটি', 'sunlight': 'unknown'}, **changes}


def create_plant(client, headers):
    response = client.post('/v1/passports', headers=headers, json=plant())
    assert response.status_code == 201, response.text
    assert 'owner_id' not in response.text
    return response.json()['id']


def test_registration_login_logout_and_stored_secrets(client, database_url):
    value, headers = register(client)
    assert all(choice is False for choice in value['account']['choices'].values())
    response = client.get('/v1/accounts/me', headers=headers)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    with psycopg.connect(database_url) as db:
        stored = db.execute('SELECT password_hash FROM grower_account').fetchone()[0]
        assert stored.startswith('scrypt-v1$') and PASSWORD not in stored
        assert db.execute('SELECT token_hash FROM account_session').fetchone()[0] == token_digest(value['access_token'])
        assert db.execute('SELECT count(*) FROM consent_event').fetchone()[0] == 1
    duplicate = client.post('/v1/accounts/register', json={'handle': 'GROWER', 'password': PASSWORD, 'notice_version': '2026-10-04'})
    assert duplicate.status_code == 409
    wrong = client.post('/v1/accounts/login', json={'handle': 'grower', 'password': 'incorrect long password'})
    missing = client.post('/v1/accounts/login', json={'handle': 'missing', 'password': 'incorrect long password'})
    assert wrong.status_code == missing.status_code == 401 and wrong.json() == missing.json()
    signed_in = client.post('/v1/accounts/login', json={'handle': 'GROWER', 'password': PASSWORD})
    assert signed_in.status_code == 200 and signed_in.json()['access_token'] != value['access_token']
    assert client.post('/v1/accounts/logout', headers=headers).status_code == 204
    assert client.get('/v1/accounts/me', headers=headers).status_code == 401


def test_two_accounts_cannot_read_or_mutate_each_others_plants(client, database_url):
    _, owner = register(client, 'owner')
    _, other = register(client, 'other')
    passport = create_plant(client, owner)
    root = '/v1/passports/' + passport
    assert client.get('/v1/passports', headers=other).json() == []
    for method, path, payload in [('GET', root, None), ('PUT', root, plant()), ('DELETE', root, None),
                                  ('GET', root + '/care', None), ('POST', root + '/care',
                                   {'kind': 'watering', 'occurred_on': today_bd().isoformat()})]:
        response = client.request(method, path, headers=other, json=payload)
        assert response.status_code == 404, response.text
    assert client.get(root, headers=owner).json()['nickname'] == 'আমার ঢেঁড়স'
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM plant_passport').fetchone()[0] == 1
        owner_id = db.execute("SELECT id FROM grower_account WHERE handle='other'").fetchone()[0]
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            db.execute('''INSERT INTO plant_care_event(id,passport_id,owner_id,kind,occurred_on,note)
                          VALUES (%s,%s,%s,'watering',current_date,'')''', (uuid4(), passport, owner_id))


def test_consent_is_independent_editable_and_audited(client, database_url):
    value, headers = register(client)
    choices = {'location_opt_in': False, 'community_opt_in': True, 'impact_opt_in': False}
    response = client.put('/v1/accounts/consent', headers=headers, json={'choices': choices, 'notice_version': '2026-10-04'})
    assert response.json()['choices'] == choices
    assert response.json()['id'] == value['account']['id']
    choices['community_opt_in'] = False
    assert client.put('/v1/accounts/consent', headers=headers, json={'choices': choices, 'notice_version': '2026-10-04'}).status_code == 200
    with psycopg.connect(database_url) as db:
        receipts = db.execute('SELECT choices FROM consent_event ORDER BY id').fetchall()
        assert len(receipts) == 3 and receipts[1][0]['community_opt_in'] is True and receipts[2][0]['community_opt_in'] is False
    assert client.get('/v1/accounts/me', headers=headers).json()['choices'] == choices


def test_passport_edit_care_chronology_and_cursor_pagination(client):
    _, headers = register(client)
    passport = create_plant(client, headers)
    root = '/v1/passports/' + passport
    for days in (1, 8, 3):
        assert client.post(root + '/care', headers=headers, json={'kind': 'watering',
            'occurred_on': (today_bd() - timedelta(days=days)).isoformat(), 'note': 'নিজের যত্ন'}).status_code == 201
    first = client.get(root + '/care?limit=2', headers=headers).json()
    second = client.get(root + '/care?limit=2&after=' + first[-1]['id'], headers=headers).json()
    assert len(first) == 2 and len(second) == 1
    assert [row['occurred_on'] for row in first + second] == sorted(row['occurred_on'] for row in first + second)
    assert client.put(root, headers=headers, json=plant(nickname='Edited')).json()['nickname'] == 'Edited'
    assert client.put(root, headers=headers, json=plant(planted_on=today_bd().isoformat())).status_code == 422
    assert client.post(root + '/care', headers=headers, json={'kind': 'pruning', 'occurred_on': (today_bd()-timedelta(days=11)).isoformat()}).status_code == 422
    for _ in range(2):
        create_plant(client, headers)
    items = client.get('/v1/passports?limit=2', headers=headers).json()
    rest = client.get('/v1/passports?limit=2&after=' + items[-1]['id'], headers=headers).json()
    assert len(items) == 2 and len(rest) == 1 and {x['id'] for x in items}.isdisjoint(x['id'] for x in rest)
    assert client.get('/v1/passports?limit=101', headers=headers).status_code == 422


def test_species_reference_is_optional_and_never_promotes_demo_advice(client, database_url):
    _, headers = register(client)
    for species in ('demo-okra', 'missing-species'):
        assert client.post('/v1/passports', headers=headers, json=plant(species_id=species)).status_code == 422
    with psycopg.connect(database_url) as db:
        db.execute("INSERT INTO catalog_source(id,title,review_status) VALUES ('local','Local','demo')")
        db.execute("INSERT INTO species(id,common_name_en,common_name_bn,category,source_id) VALUES ('local-okra','Okra','ঢেঁড়স','crop','local')")
    response = client.post('/v1/passports', headers=headers, json=plant(species_id='local-okra'))
    assert response.status_code == 201
    assert client.get('/v1/catalog/recommendation-candidates').json() == []


def test_invalid_expired_sessions_and_input_errors_are_private(client, database_url):
    value, headers = register(client)
    for auth in (None, 'Bearer invalid', 'Basic abc', 'Bearer ' + 'a'*43):
        assert client.get('/v1/passports', headers={} if auth is None else {'Authorization': auth}).status_code == 401
    with psycopg.connect(database_url) as db:
        db.execute('UPDATE account_session SET created_at=now()-interval \'2 days\', expires_at=now()-interval \'1 day\' WHERE token_hash=%s', (token_digest(value['access_token']),))
    assert client.get('/v1/passports', headers=headers).status_code == 401
    response = client.post('/v1/accounts/login', json={'handle': 'grower', 'password': 'secret-short'})
    assert response.status_code == 422 and 'secret-short' not in response.text and 'input' not in response.text
    assert client.post('/v1/accounts/login', content='x'*17000).status_code == 413


def test_password_change_revokes_all_sessions_and_preserves_records(client, database_url):
    _, headers = register(client)
    passport = create_plant(client, headers)
    assert client.post('/v1/accounts/password', headers=headers, json={'current_password': 'wrong', 'new_password': 'a replacement passphrase'}).status_code == 401
    response = client.post('/v1/accounts/password', headers=headers, json={'current_password': PASSWORD, 'new_password': 'a replacement passphrase'})
    assert response.status_code == 204
    assert client.get('/v1/passports', headers=headers).status_code == 401
    assert client.post('/v1/accounts/login', json={'handle': 'grower', 'password': PASSWORD}).status_code == 401
    signed_in = client.post('/v1/accounts/login', json={'handle': 'grower', 'password': 'a replacement passphrase'}).json()
    assert client.get('/v1/passports/'+passport, headers={'Authorization': 'Bearer ' + signed_in['access_token']}).status_code == 200


def test_explicit_delete_removes_only_owned_private_records(client, database_url):
    _, owner = register(client, 'owner')
    _, other = register(client, 'other')
    passport = create_plant(client, owner)
    retained = create_plant(client, other)
    client.post('/v1/passports/'+passport+'/care', headers=owner, json={'kind': 'observation', 'occurred_on': today_bd().isoformat()})
    assert client.post('/v1/accounts/delete', headers=owner, json={'password': 'wrong'}).status_code == 401
    assert client.post('/v1/accounts/delete', headers=owner, json={'password': PASSWORD}).status_code == 204
    assert client.get('/v1/accounts/me', headers=owner).status_code == 401
    assert client.get('/v1/passports/'+retained, headers=other).status_code == 200
    assert client.delete('/v1/passports/'+retained, headers=other).status_code == 204
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM grower_account').fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM plant_passport').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM plant_care_event').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM species').fetchone()[0] == 2
    with pytest.raises(RuntimeError, match='would delete private records'):
        run('downgrade', database_url, '0003', confirm=True)
    assert run('current', database_url) == ('0005',)


def test_rate_limits_are_committed_even_when_requests_fail(client, database_url):
    repo = AccountRepository(database_url)
    repo.throttle('test', 'subject', 1)
    with pytest.raises(Exception) as error:
        repo.throttle('test', 'subject', 1)
    assert error.value.status_code == 429
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT attempts FROM auth_rate_bucket WHERE key_hash=%s', (token_digest('test:subject'),)).fetchone()[0] == 2
        db.execute('UPDATE auth_rate_bucket SET expires_at=now()-interval \'1 second\'')
    repo.throttle('test', 'subject', 1)
    for _ in range(10):
        assert client.post('/v1/accounts/login', json={'handle': 'nobody', 'password': PASSWORD}).status_code == 401
    response = client.post('/v1/accounts/login', json={'handle': 'nobody', 'password': PASSWORD})
    assert response.status_code == 429 and 'Retry-After' in response.headers


def test_tls_is_required_outside_explicit_development(client, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    response = client.get('/v1/accounts/me', headers={'X-Forwarded-Proto': 'https'})
    assert response.status_code == 403 and response.headers['cache-control'] == 'no-store'


def test_session_cap_and_revocation_during_a_waiting_request(client, database_url):
    value, headers = register(client)
    for _ in range(5):
        assert client.post('/v1/accounts/login', json={'handle': 'grower', 'password': PASSWORD}).status_code == 200
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM account_session').fetchone()[0] == 5
    assert client.get('/v1/accounts/me', headers=headers).status_code == 401
    new = client.post('/v1/accounts/login', json={'handle': 'grower', 'password': PASSWORD}).json()
    repo = AccountRepository(database_url)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database_url) as db:
            db.execute('SELECT id FROM grower_account FOR UPDATE')
            future = pool.submit(repo.me, new['access_token'])
            db.execute('DELETE FROM account_session WHERE token_hash=%s', (token_digest(new['access_token']),))
        with pytest.raises(Exception) as error:
            future.result(timeout=10)
        assert error.value.status_code == 401


def test_old_catalog_revision_guard_is_still_protective(database_url):
    run('upgrade', database_url, '0003')
    with pytest.raises(RuntimeError, match='would delete provenance'):
        run('downgrade', database_url, '0002', confirm=True)
    assert run('current', database_url) == ('0003',)


def test_https_private_route_works_when_session_is_valid(client, database_url, monkeypatch):
    _, headers = register(client)
    monkeypatch.setenv('APP_ENV', 'production')
    with TestClient(client.app, base_url='https://testserver') as secure:
        assert secure.get('/v1/accounts/me', headers=headers).status_code == 200


def test_session_expiring_while_waiting_for_owner_lock_is_rejected(client, database_url):
    value, _ = register(client)
    with psycopg.connect(database_url) as db:
        db.execute('UPDATE account_session SET expires_at=clock_timestamp()+interval \'2 seconds\'')
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database_url) as db:
            db.execute('SELECT id FROM grower_account FOR UPDATE')
            future = pool.submit(AccountRepository(database_url).me, value['access_token'])
            for _ in range(100):
                db.execute('SELECT pg_stat_clear_snapshot()')
                waiting = db.execute("""SELECT 1 FROM pg_stat_activity WHERE datname=current_database()
                    AND wait_event_type='Lock' AND query LIKE 'SELECT a.%'""").fetchone()
                if waiting:
                    break
                time.sleep(0.01)
            assert waiting, 'Private request must actually be waiting on the account lock'
            db.execute("SELECT pg_sleep(2.1)")
        with pytest.raises(Exception) as error:
            future.result(timeout=5)
        assert error.value.status_code == 401
