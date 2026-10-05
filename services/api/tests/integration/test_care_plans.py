"""Owned disposable DB fixtures only; never approve live/demo records."""
from datetime import timedelta
import hashlib
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
import pytest

from app.care_repository import CarePlanRepository
from app.catalog_bundle import CatalogBundle, today_bd
from app.catalog_import import import_bundle
from app.main import create_app
from app.migrations import run
from app.seed_demo import seed_demo
from tests.test_catalog_bundle import valid_bundle
from tests.test_care_plans import guidance
from tests.test_recommendations import candidate, goal

pytestmark = pytest.mark.integration
PASSWORD = 'Local care fixture passphrase!'


@pytest.fixture
def client(database_url, monkeypatch):
    run('upgrade', database_url)
    monkeypatch.setenv('DATABASE_URL', database_url)
    monkeypatch.setenv('APP_ENV', 'development')
    with TestClient(create_app()) as c: yield c


def register(client, handle='care_owner'):
    response = client.post('/v1/accounts/register', json={
        'handle': handle, 'password': PASSWORD, 'notice_version': '2026-10-04'})
    assert response.status_code == 201
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def approved_bundle():
    value = valid_bundle()
    profile = value['plants'][0]['profiles'][0]
    profile.update(id='test-profile', locality='district:dhaka', growing_context='open_ground')
    profile['requirements'] = [{k: v for k, v in row.items() if k in ('key','value','source_id','source_locator','interpretation_note')}
                               for row in candidate()['requirements']]
    next(r for r in profile['requirements'] if r['key']=='sowing_windows')['value'] = [
        {'start_month':1,'start_day':1,'end_month':12,'end_day':31}]
    profile['care_guidance'] = [{k: v for k, v in row.items() if k not in ('profile_id','source','eligible')}
                               for row in guidance()]
    for row in profile['care_guidance']:
        row.update(reviewed_at=today_bd().isoformat(), valid_until=(today_bd()+timedelta(days=30)).isoformat())
    return value


def payload(**updates):
    return {'profile_id': 'test-profile', 'goal': goal(planting_date=today_bd()).model_dump(mode='json'),
            'weeks': 2, **updates}


def saved(client, headers, **updates):
    response = client.post('/v1/plans', headers=headers, json=payload(
        request_id=str(uuid4()), save_notice_version='care-plan-2026-10-04', **updates))
    assert response.status_code == 201, response.text
    return response.json()


def test_grounded_preview_save_idempotency_and_private_minimal_inputs(client, database_url):
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    headers = register(client)
    value = payload(); value['goal']['goal'] = 'PRIVATE TRANSCRIPT'; value['goal']['soil']['description'] = 'PRIVATE SOIL NOTE'
    assert client.post('/v1/plans/preview', json=value).status_code == 401
    preview = client.post('/v1/plans/preview', headers=headers, json=value)
    assert preview.status_code == 200 and preview.json()['status'] == 'ready'
    assert preview.headers['cache-control'] == 'no-store'
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM care_plan').fetchone()[0] == 0
    create = {**value, 'request_id': str(uuid4()), 'save_notice_version': 'care-plan-2026-10-04'}
    first = client.post('/v1/plans', headers=headers, json=create)
    assert first.status_code == 201, first.text
    second = client.post('/v1/plans', headers=headers, json=create)
    assert second.json()['plan_id'] == first.json()['plan_id'] and second.json()['version'] == 1
    assert first.json()['availability'] == 'current'
    with psycopg.connect(database_url) as db:
        row = db.execute('SELECT conditions,snapshot FROM care_plan_version').fetchone()
        assert 'PRIVATE' not in json.dumps(row)
        assert db.execute('SELECT count(*) FROM care_plan').fetchone()[0] == 1
    create['weeks'] = 1
    assert client.post('/v1/plans', headers=headers, json=create).status_code == 409


def test_corrupt_saved_evidence_fails_safely(client, database_url):
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    headers = register(client)
    first = saved(client, headers)
    with psycopg.connect(database_url) as db:
        # Privileged corruption only in this disposable DB, reset by its fixture.
        db.execute('ALTER TABLE care_plan_version DISABLE TRIGGER care_version_immutable')
        db.execute("UPDATE care_plan_version SET snapshot='{}'")
    assert client.get('/v1/plans/' + first['plan_id'], headers=headers).status_code == 503


def test_different_species_revision_requires_separate_plan(client, database_url):
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    headers = register(client)
    first = saved(client, headers)
    with psycopg.connect(database_url) as db:
        db.execute("INSERT INTO species(id,common_name_en,common_name_bn,scientific_name,category,source_id) SELECT 'other-plant',common_name_en,common_name_bn,scientific_name,category,source_id FROM species WHERE id='test-okra'")
        db.execute("UPDATE plant_profile SET species_id='other-plant' WHERE id='test-profile'")
    revise = payload(expected_version=1, save_notice_version='care-plan-2026-10-04')
    assert client.post(f"/v1/plans/{first['plan_id']}/versions", headers=headers, json=revise).status_code == 409


def test_evidence_row_bound_fails_closed(client, database_url):
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    headers = register(client)
    with psycopg.connect(database_url) as db:
        for i in range(30):
            db.execute('''INSERT INTO plant_care_guidance
              (id,profile_id,topic,week_start,week_end,instruction_bn,instruction_en,source_id,source_locator,
               interpretation_note,review_status,reviewed_by,reviewed_at,valid_until)
              SELECT %s,profile_id,topic,week_start,week_end,instruction_bn,instruction_en,source_id,source_locator,
               interpretation_note,review_status,reviewed_by,reviewed_at,valid_until
              FROM plant_care_guidance LIMIT 1''', ('oversized-' + str(i),))
    response = client.post('/v1/plans/preview', headers=headers, json=payload())
    assert response.status_code == 503 and 'oversized' not in response.text


@pytest.mark.parametrize('change', [
    "reuse_status='permission_pending'",
    "access_status='login_required'",
    "review_status='demo'",
    "checked_at=CURRENT_DATE-2, valid_until=CURRENT_DATE-1",
])
def test_independent_care_source_gate_withholds_only_affected_topic(client, database_url, change):
    value = approved_bundle()
    other = {**value['sources'][0], 'id': 'care-only-source'}
    value['sources'].append(other)
    next(row for row in value['plants'][0]['profiles'][0]['care_guidance'] if row['topic']=='watering')['source_id'] = other['id']
    import_bundle(CatalogBundle.model_validate(value), database_url)
    headers = register(client)
    first = saved(client, headers)
    with psycopg.connect(database_url) as db:
        db.execute("UPDATE catalog_source SET " + change + " WHERE id='care-only-source'")
    result = client.post('/v1/plans/preview', headers=headers, json=payload()).json()
    assert result['status'] == 'partial' and not any(s['topic']=='watering' for s in result['instructions'])
    old = client.get('/v1/plans/' + first['plan_id'], headers=headers).json()
    assert old['availability'] == 'stale' and not old['plan']['instructions']


def test_versions_preserve_old_snapshot_detect_evidence_changes_and_retry(client, database_url):
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    headers = register(client)
    first = saved(client, headers)
    plan_id = first['plan_id']
    revise = payload(expected_version=1, save_notice_version='care-plan-2026-10-04')
    assert client.post(f'/v1/plans/{plan_id}/versions', headers=headers, json=revise).json()['version'] == 1
    with psycopg.connect(database_url) as db:
        db.execute("UPDATE plant_care_guidance SET instruction_en='New reviewed fixture instruction' WHERE topic='monitoring'")
        original = db.execute('SELECT snapshot FROM care_plan_version WHERE version=1').fetchone()[0]
    old = client.get(f'/v1/plans/{plan_id}/versions/1', headers=headers).json()
    assert old['availability'] == 'stale' and not old['plan']['instructions'] and old['plan']['status'] == 'blocked'
    second = client.post(f'/v1/plans/{plan_id}/versions', headers=headers, json=revise)
    assert second.status_code == 200 and second.json()['version'] == 2
    assert client.post(f'/v1/plans/{plan_id}/versions', headers=headers, json=revise).json()['version'] == 2
    revise['weeks'] = 1
    assert client.post(f'/v1/plans/{plan_id}/versions', headers=headers, json=revise).status_code == 409
    history = client.get(f'/v1/plans/{plan_id}/versions?limit=1', headers=headers).json()
    assert history[0]['version'] == 2
    assert client.get(f'/v1/plans/{plan_id}/versions?before=2', headers=headers).json()[0]['version'] == 1
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT snapshot FROM care_plan_version WHERE version=1').fetchone()[0] == original
    with pytest.raises(psycopg.Error), psycopg.connect(database_url) as db:
        db.execute("UPDATE care_plan_version SET snapshot='{}'")
    assert len(client.get('/v1/plans', headers=headers).json()) == 1


def test_unusable_or_revoked_evidence_withholds_instructions_and_cannot_save(client, database_url):
    headers = register(client)
    seed_demo(database_url)
    assert client.post('/v1/plans/preview', headers=headers, json=payload()).json()['status'] == 'blocked'
    assert client.post('/v1/plans', headers=headers, json=payload(request_id=str(uuid4()),save_notice_version='care-plan-2026-10-04')).status_code == 409
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    plan_id = saved(client, headers)['plan_id']
    with psycopg.connect(database_url) as db:
        db.execute("UPDATE catalog_source SET reuse_status='restricted' WHERE id='test-source'")
    result = client.get(f'/v1/plans/{plan_id}', headers=headers).json()
    assert result['availability'] == 'unavailable' and not result['plan']['instructions']
    revise = payload(expected_version=1,save_notice_version='care-plan-2026-10-04')
    assert client.post(f'/v1/plans/{plan_id}/versions', headers=headers, json=revise).status_code == 409


def test_owner_isolation_history_delete_and_fk_enforcement(client, database_url):
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    one, two = register(client), register(client, 'care_other')
    a, b = saved(client, one)['plan_id'], saved(client, two)['plan_id']
    assert client.get('/v1/plans', headers=one).json()[0]['id'] == a
    assert client.get(f'/v1/plans?after={a}', headers=one).json() == []
    for suffix in ('', '/versions', '/versions/1'):
        assert client.get('/v1/plans/'+a+suffix, headers=two).status_code == 404
    assert client.delete('/v1/plans/'+a, headers=two).status_code == 404
    assert client.post('/v1/plans/'+a+'/versions', headers=two, json=payload(
        expected_version=1, save_notice_version='care-plan-2026-10-04')).status_code == 404
    assert client.get('/v1/plans/'+a+'/versions/999', headers=one).status_code == 404
    with pytest.raises(psycopg.Error), psycopg.connect(database_url) as db:
        db.execute('''INSERT INTO care_plan_version(plan_id,owner_id,version,profile_id,fingerprint,conditions,snapshot)
            SELECT %s,owner_id,2,profile_id,fingerprint,conditions,snapshot FROM care_plan_version WHERE plan_id=%s''', (a,b))
    assert client.delete('/v1/plans/'+a, headers=one).status_code == 204
    assert client.get('/v1/plans/'+a, headers=one).status_code == 404
    assert client.post('/v1/accounts/delete',headers=two,json={'password':PASSWORD}).status_code == 204
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM care_plan_version').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM plant_care_guidance').fetchone()[0] == 4


def test_atomic_upgrade_preserves_catalog_and_private_rows_and_old_manifest_hash(database_url):
    run('upgrade', database_url, '0004')
    value = CatalogBundle.model_validate(valid_bundle())
    # Simulate the exact schema-v1 legacy manifest format without empty care arrays.
    manifest = value.model_dump(mode='json')
    for p in manifest['plants'][0]['profiles']: p.pop('care_guidance')
    digest = hashlib.sha256(json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with psycopg.connect(database_url) as db:
        db.execute('INSERT INTO catalog_import(sha256,bundle_id,manifest) VALUES (%s,%s,%s::jsonb)', (digest,value.bundle_id,json.dumps(manifest)))
        account = uuid4()
        db.execute("INSERT INTO grower_account(id,handle,password_hash,notice_version) VALUES (%s,'retained','TEST HASH','2026-10-04')", (account,))
    run('upgrade', database_url)
    assert import_bundle(value, database_url) == {'sha256':digest,'already_imported':True}
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT handle,password_hash FROM grower_account WHERE id=%s',(account,)).fetchone() == ('retained','TEST HASH')
        assert db.execute('SELECT count(*) FROM plant_care_guidance').fetchone()[0] == 0
    with pytest.raises(RuntimeError, match='community'):
        run('downgrade', database_url, '0004', confirm=True)
    assert run('current', database_url) == ('0009',)


def test_plan_input_redaction_tls_bounds_and_invalid_evidence(client, database_url, monkeypatch):
    headers = register(client)
    bad = payload(); bad['goal']['goal']='PRIVATE TEXT'; bad['owner_id']='foreign'
    response = client.post('/v1/plans/preview', headers=headers, json=bad)
    assert response.status_code == 422 and 'PRIVATE TEXT' not in response.text
    assert client.post('/v1/plans/preview',headers=headers,content=b'x'*17000).status_code == 413
    monkeypatch.setenv('APP_ENV','production')
    assert client.get('/v1/plans',headers=headers).status_code == 403
    monkeypatch.setenv('APP_ENV','development')
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    with psycopg.connect(database_url) as db:
        db.execute("UPDATE catalog_source SET source_url='https://user:SECRET@example.test/care'")
    result = client.post('/v1/plans/preview',headers=headers,json=payload())
    assert result.status_code == 503 and 'SECRET' not in result.text


def test_expiring_session_rolls_back_saved_plan(client, database_url, monkeypatch):
    import_bundle(CatalogBundle.model_validate(approved_bundle()), database_url)
    headers=register(client)
    original=CarePlanRepository._append
    def expire(db, *args):
        row=original(db,*args)
        db.execute("UPDATE account_session SET created_at=now()-interval '2 hours',expires_at=now()-interval '1 hour'")
        return row
    monkeypatch.setattr(CarePlanRepository,'_append',staticmethod(expire))
    result=client.post('/v1/plans',headers=headers,json=payload(request_id=str(uuid4()),save_notice_version='care-plan-2026-10-04'))
    assert result.status_code == 401
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM care_plan').fetchone()[0] == 0
