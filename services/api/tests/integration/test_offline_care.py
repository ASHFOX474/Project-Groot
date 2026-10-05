"""Offline retry guarantees against disposable PostgreSQL, never the live DB."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import psycopg
import pytest

from app.accounts import AccountRepository, CareInput
from app.catalog_bundle import today_bd
from app.migrations import run
from tests.integration.test_accounts_passports import client, register, create_plant

pytestmark = pytest.mark.integration


def care(**changes):
    return {'kind': 'observation', 'occurred_on': today_bd().isoformat(),
            'note': 'অফলাইন যত্ন', 'request_id': str(uuid4()), **changes}


def test_lost_response_retries_return_same_event_and_conflicts_are_not_overwritten(client, database_url):
    _, headers = register(client)
    passport = create_plant(client, headers)
    root = '/v1/passports/' + passport + '/care'
    body = care()
    first = client.post(root, headers=headers, json=body)
    assert first.status_code == 201, first.text
    replay = client.post(root, headers=headers, json=body)
    assert replay.status_code == 201 and replay.json() == first.json()
    assert client.post(root, headers=headers, json={**body, 'note': 'different'}).status_code == 409
    another = create_plant(client, headers)
    assert client.post('/v1/passports/' + another + '/care', headers=headers, json=body).status_code == 409
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM plant_care_event').fetchone()[0] == 1
        assert db.execute('SELECT note FROM plant_care_event').fetchone()[0] == body['note']


def test_concurrent_duplicate_sync_is_one_record(client, database_url):
    session, headers = register(client)
    passport = create_plant(client, headers)
    body = CareInput.model_validate(care())
    repo = AccountRepository(database_url)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: repo.add_care(session['access_token'], passport, body), range(2)))
    assert results[0]['id'] == results[1]['id']
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM plant_care_event').fetchone()[0] == 1


def test_sync_cannot_resurrect_deleted_plants_or_cross_accounts(client):
    _, owner = register(client, 'owner')
    _, other = register(client, 'other')
    passport = create_plant(client, owner)
    body = care()
    root = '/v1/passports/' + passport
    assert client.post(root + '/care', headers=other, json=body).status_code == 404
    assert client.delete(root, headers=owner).status_code == 204
    assert client.post(root + '/care', headers=owner, json=body).status_code == 404
    other_passport = create_plant(client, other)
    assert client.post('/v1/passports/' + other_passport + '/care', headers=other, json=body).status_code == 201


def test_server_date_validation_and_legacy_clients_are_preserved(client):
    _, headers = register(client)
    root = '/v1/passports/' + create_plant(client, headers) + '/care'
    assert client.post(root, headers=headers, json=care(occurred_on=(today_bd()-timedelta(days=11)).isoformat())).status_code == 422
    assert client.post(root, headers=headers, json=care(occurred_on=(today_bd()+timedelta(days=1)).isoformat())).status_code == 422
    assert client.post(root, headers=headers, json=care(request_id='invalid')).status_code == 422
    legacy = care(); legacy.pop('request_id')
    assert client.post(root, headers=headers, json=legacy).status_code == 201
    assert client.post(root, headers=headers, json=legacy).status_code == 201


def test_additive_upgrade_preserves_existing_private_rows(database_url):
    run('upgrade', database_url, '0006')
    with psycopg.connect(database_url) as db:
        owner, passport, event = uuid4(), uuid4(), uuid4()
        db.execute("INSERT INTO grower_account(id,handle,password_hash,notice_version) VALUES (%s,'legacy','fixture','fixture')", (owner,))
        db.execute("INSERT INTO plant_passport(id,owner_id,nickname,species_name,planted_on,conditions) VALUES (%s,%s,'পুরোনো','Fixture',current_date,'{}')", (passport, owner))
        db.execute("INSERT INTO plant_care_event(id,passport_id,owner_id,kind,occurred_on,note) VALUES (%s,%s,%s,'observation',current_date,'পুরোনো যত্ন')", (event, passport, owner))
        before = db.execute('SELECT * FROM plant_care_event').fetchone()
    run('upgrade', database_url)
    with psycopg.connect(database_url) as db:
        after = db.execute('SELECT * FROM plant_care_event').fetchone()
        assert after[:-1] == before and after[-1] is None
    with pytest.raises(RuntimeError, match='community'):
        run('downgrade', database_url, '0006', confirm=True)
    assert run('current', database_url) == ('0009',)
