"""Consent and image privacy contracts on disposable PostgreSQL only."""
import base64
from io import BytesIO
from uuid import uuid4

import pytest
import psycopg
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fastapi import HTTPException
from app.catalog_bundle import today_bd
from app.accounts import token_digest
from app.migrations import run
from app.photos import PhotoInput
from app.photo_repository import PhotoRepository

from tests.integration.test_accounts_passports import client, register, create_plant

pytestmark = pytest.mark.integration


def image_bytes():
    from PIL import Image
    image = Image.new('RGB', (240, 320), (190, 170, 20))
    output = BytesIO()
    image.save(output, 'PNG')
    return output.getvalue()


def upload(**changes):
    from app.catalog_bundle import today_bd
    return {'request_id': str(uuid4()), 'consent_generation': 1, 'observed_on': today_bd().isoformat(),
            'image_base64': base64.b64encode(image_bytes()).decode(),
            'media_type': 'image/png', 'caption': 'নিজের ছবি',
            'symptoms': [], 'rights_confirmed': True, **changes}


def enable(client, root, headers, health=False):
    result = client.put(root + '/photo-consent', headers=headers, json={
        'storage': True, 'health': health, 'notice_version': '2026-10-05-photos-v1'})
    assert result.status_code == 200, result.text


def test_upload_requires_feature_consent_and_is_owner_private(client):
    _, owner = register(client, 'owner')
    _, other = register(client, 'other')
    root = '/v1/passports/' + create_plant(client, owner)
    assert client.post(root + '/photos', headers=owner, json=upload()).status_code == 403
    enable(client, root, owner)
    # Real image fixture is supplied in the expanded decoder tests.
    assert client.get(root + '/photos', headers=owner).json() == []
    assert client.get(root + '/photos', headers=other).status_code == 404
    assert client.put(root + '/photo-consent', headers=other, json={
        'storage': True, 'health': False, 'notice_version': '2026-10-05-photos-v1'}).status_code == 404


def test_photo_request_body_gets_bounded_exception_not_other_routes(client):
    _, headers = register(client)
    root = '/v1/passports/' + create_plant(client, headers)
    enable(client, root, headers)
    result = client.post(root + '/photos', headers=headers, json=upload(image_base64='a' * 20000))
    assert result.status_code == 422 and 'a' * 100 not in result.text
    assert client.post(root + '/care', headers=headers, json={'note': 'a' * 20000}).status_code == 413


def test_photo_upload_read_retry_conflict_and_owner_isolation(client, database_url):
    _, owner = register(client, 'owner')
    _, other = register(client, 'other')
    plant = create_plant(client, owner)
    root = '/v1/passports/' + plant
    enable(client, root, owner, health=True)
    body = upload(symptoms=['spots'])
    first = client.post(root + '/photos', headers=owner, json=body)
    assert first.status_code == 201, first.text
    photo = first.json()
    assert photo['assistance']['probability'] is None
    assert 'jpeg' not in photo and 'image_base64' not in photo and 'owner_id' not in photo
    assert client.post(root + '/photos', headers=owner, json=body).json() == photo
    assert client.post(root + '/photos', headers=owner, json={**body, 'caption': 'changed'}).status_code == 409
    image = root + '/photos/' + photo['id'] + '/image'
    response = client.get(image, headers=owner)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    with Image.open(BytesIO(response.content)) as saved:
        assert saved.format == 'JPEG' and not saved.getexif()
    assert client.get(image).status_code == 401
    assert client.get(image, headers=other).status_code == 404
    assert client.delete(root + '/photos/' + photo['id'], headers=other).status_code == 404
    assert len(client.get(root + '/photos', headers=owner).json()) == 1
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM plant_photo').fetchone()[0] == 1


def test_health_storage_withdrawal_and_deleted_photo_cannot_be_replayed(client, database_url):
    _, headers = register(client)
    root = '/v1/passports/' + create_plant(client, headers)
    enable(client, root, headers, health=True)
    body = upload(symptoms=['wilting'])
    first = client.post(root + '/photos', headers=headers, json=body).json()
    choices = {'storage': True, 'health': False, 'notice_version': '2026-10-05-photos-v1'}
    assert client.put(root + '/photo-consent', headers=headers, json=choices).status_code == 200
    row = client.get(root + '/photos', headers=headers).json()[0]
    assert row['assistance'] is None and row['symptoms'] == []
    assert client.post(root + '/photos', headers=headers, json=body).status_code == 409
    assert client.delete(root + '/photos/' + first['id'], headers=headers).status_code == 204
    assert client.post(root + '/photos', headers=headers, json=body).status_code == 409
    current = client.get(root + '/photo-consent', headers=headers).json()['generation']
    second = client.post(root + '/photos', headers=headers, json=upload(consent_generation=current))
    assert second.status_code == 201 and second.json()['assistance'] is None
    assert client.put(root + '/photo-consent', headers=headers, json={**choices, 'storage': False}).status_code == 200
    assert client.get(root + '/photos', headers=headers).json() == []
    assert client.post(root + '/photos', headers=headers, json=upload()).status_code == 403
    enable(client, root, headers)
    assert client.post(root + '/photos', headers=headers, json=body).status_code == 409
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM plant_photo').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM photo_consent_event').fetchone()[0] == 4


def test_dates_cursor_and_explicit_account_deletion_cascade(client, database_url):
    _, headers = register(client)
    plant = create_plant(client, headers)
    root = '/v1/passports/' + plant
    enable(client, root, headers)
    assert client.post(root + '/photos', headers=headers, json=upload(observed_on=(today_bd()-timedelta(days=11)).isoformat())).status_code == 422
    assert client.post(root + '/photos', headers=headers, json=upload(symptoms=['spots'])).status_code == 403
    ids = []
    for ago in [1, 0, 2]:
        result = client.post(root + '/photos', headers=headers, json=upload(observed_on=(today_bd()-timedelta(days=ago)).isoformat()))
        assert result.status_code == 201, result.text
        ids.append(result.json()['id'])
    first = client.get(root + '/photos?limit=1', headers=headers).json()[0]
    assert first['id'] == ids[1]
    page = client.get(root + '/photos?after=' + first['id'], headers=headers).json()
    assert [p['id'] for p in page] == [ids[0], ids[2]]
    updated = client.get(root, headers=headers).json(); updated.pop('id')
    updated['planted_on'] = today_bd().isoformat()
    assert client.put(root, headers=headers, json=updated).status_code == 422
    from tests.integration.test_accounts_passports import PASSWORD
    assert client.post('/v1/accounts/delete', headers=headers, json={'password': PASSWORD}).status_code == 204
    with psycopg.connect(database_url) as db:
        for table in ['plant_photo', 'photo_consent', 'photo_consent_event']:
            assert db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0


def test_concurrent_retry_and_foreign_owner_fk(client, database_url):
    session, headers = register(client)
    plant = create_plant(client, headers)
    root = '/v1/passports/' + plant
    enable(client, root, headers)
    repo = PhotoRepository(database_url)
    body = PhotoInput.model_validate(upload())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: repo.upload(session['access_token'], plant, body), range(2)))
    assert results[0]['id'] == results[1]['id']
    with psycopg.connect(database_url) as db:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            db.execute('UPDATE plant_photo SET owner_id=%s', (uuid4(),))


@pytest.mark.parametrize('change', ['withdraw', 'logout', 'delete'])
def test_consent_session_and_deletion_rechecked_after_decode(client, database_url, monkeypatch, change):
    session, headers = register(client)
    plant = create_plant(client, headers)
    root = '/v1/passports/' + plant
    enable(client, root, headers)
    import app.photo_repository as module
    decode = module.sanitize_image
    def changed(value):
        result = decode(value)
        with psycopg.connect(database_url) as db:
            if change == 'withdraw':
                db.execute('UPDATE photo_consent SET storage=false,generation=generation+1 WHERE passport_id=%s', (plant,))
            elif change == 'logout':
                db.execute('DELETE FROM account_session WHERE token_hash=%s', (token_digest(session['access_token']),))
            else:
                db.execute('DELETE FROM plant_passport WHERE id=%s', (plant,))
        return result
    monkeypatch.setattr(module, 'sanitize_image', changed)
    with pytest.raises(HTTPException) as error:
        PhotoRepository(database_url).upload(session['access_token'], plant, PhotoInput.model_validate(upload()))
    assert error.value.status_code == {'withdraw': 409, 'logout': 401, 'delete': 404}[change]
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM plant_photo').fetchone()[0] == 0


def test_additive_photo_migration_preserves_old_schema_rows_and_blocks_rollback(database_url):
    run('upgrade', database_url, '0007')
    with psycopg.connect(database_url) as db:
        db.execute("INSERT INTO grower_account(id,handle,password_hash,notice_version) VALUES(%s,'old','fixture','old')", (uuid4(),))
        before = db.execute('SELECT id,handle,password_hash,location_opt_in,community_opt_in,impact_opt_in,notice_version,created_at FROM grower_account').fetchall()
    run('upgrade', database_url)
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT id,handle,password_hash,location_opt_in,community_opt_in,impact_opt_in,notice_version,created_at FROM grower_account').fetchall() == before
        assert db.execute('SELECT count(*) FROM plant_photo').fetchone()[0] == 0
    with pytest.raises(RuntimeError, match='community'):
        run('downgrade', database_url, '0007', confirm=True)
    assert run('current', database_url) == ('0009',)


def test_plant_and_account_photo_caps_do_not_silently_evict(client, database_url):
    session, headers = register(client)
    first = create_plant(client, headers)
    second = create_plant(client, headers)
    third = create_plant(client, headers)
    for plant in [first, second, third]: enable(client, '/v1/passports/' + plant, headers)
    repo = PhotoRepository(database_url)
    repo.upload(session['access_token'], first, PhotoInput.model_validate(upload()))
    with psycopg.connect(database_url) as db:
        for plant, count in [(first, 49), (second, 50)]:
            for _ in range(count):
                db.execute('''INSERT INTO plant_photo(id,passport_id,owner_id,request_id,fingerprint,
                    observed_on,caption,symptoms,jpeg,width,height)
                    SELECT %s,%s,owner_id,%s,fingerprint,observed_on,caption,symptoms,jpeg,width,height
                    FROM plant_photo LIMIT 1''', (uuid4(), plant, uuid4()))
    for plant in [first, third]:
        with pytest.raises(HTTPException) as error:
            repo.upload(session['access_token'], plant, PhotoInput.model_validate(upload()))
        assert error.value.status_code == 409
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM plant_photo').fetchone()[0] == 100
