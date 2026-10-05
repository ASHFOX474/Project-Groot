from datetime import timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

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
    with TestClient(create_app()) as value:
        yield value


def register(client, handle, community=False):
    response = client.post('/v1/accounts/register', json={
        'handle': handle, 'password': PASSWORD, 'notice_version': '2026-10-04',
        'choices': {'community_opt_in': community},
    })
    assert response.status_code == 201, response.text
    value = response.json()
    return {'Authorization': 'Bearer ' + value['access_token']}


def add_plant(client, headers, days=10):
    response = client.post('/v1/passports', headers=headers, json={
        'nickname': 'বাগানের গাছ', 'species_name': 'Okra', 'planted_on':
        (today_bd() - timedelta(days=days)).isoformat(),
        'conditions': {'growing_context': 'container', 'soil': 'নিজের মাটি', 'sunlight': 'unknown'},
    })
    assert response.status_code == 201, response.text
    return response.json()['id']


def enable_profile(client, headers, alias='Garden voice'):
    assert client.put('/v1/accounts/consent', headers=headers, json={
        'choices': {'community_opt_in': True}, 'notice_version': '2026-10-04'}).status_code == 200
    response = client.put('/v1/community/profile', headers=headers, json={
        'district': 'dhaka', 'public_alias': alias, 'notice_version': 'community-2026-10-06'})
    assert response.status_code == 200, response.text


def test_rewards_return_streaks_milestones_and_size_fair_score(client):
    headers = register(client, 'rewards')
    plant = add_plant(client, headers, days=100)
    for days in (0, 1):
        response = client.post(f'/v1/passports/{plant}/care', headers=headers, json={
            'kind': 'observation', 'occurred_on': (today_bd() - timedelta(days=days)).isoformat()})
        assert response.status_code == 201
    result = client.get('/v1/rewards', headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body['plant_count'] == 1 and body['current_streak_days'] == 2
    assert body['plants'][0]['milestones'][0]['status'] == 'earned'
    assert body['plants'][0]['milestones'][1]['status'] == 'upcoming'
    assert 'Average of capped per-plant scores' in body['score_method']


def test_community_posts_are_pending_until_moderated_and_withdrawal_hides(client, database_url):
    author = register(client, 'author', community=True)
    enable_profile(client, author)
    add_plant(client, author)
    created = client.post('/v1/community/posts', headers=author, json={
        'topic': 'milestone', 'body': 'Three months of careful observations.'})
    assert created.status_code == 201 and created.json()['status'] == 'pending'
    assert client.get('/v1/community/feed', headers=author).json() == []
    assert client.get('/v1/community/moderation/queue', headers=author).status_code == 403

    with psycopg.connect(database_url) as db:
        db.execute("UPDATE grower_account SET is_moderator=true WHERE handle='author'")
    post_id = created.json()['id']
    moderated = client.post(f'/v1/community/moderation/{post_id}', headers=author,
                            json={'status': 'approved'})
    assert moderated.status_code == 200 and moderated.json()['status'] == 'approved'
    assert len(client.get('/v1/community/feed', headers=author).json()) == 1
    assert client.get('/v1/community/leaderboard', headers=author).json()[0]['public_alias'] == 'Garden voice'

    for index in range(1, 4):
        reporter = register(client, f'reporter{index}')
        response = client.post(f'/v1/community/posts/{post_id}/report', headers=reporter,
                               json={'reason': 'spam'})
        assert response.status_code == 200
        if index < 3:
            assert response.json()['accepted'] is True and response.json()['auto_hidden'] is False
        else:
            assert response.json()['accepted'] is True and response.json()['auto_hidden'] is True
    assert client.get('/v1/community/feed', headers=author).json() == []

    assert client.put('/v1/accounts/consent', headers=author, json={
        'choices': {'community_opt_in': False}, 'notice_version': '2026-10-04'}).status_code == 200
    assert client.get('/v1/community/feed', headers=author).json() == []
    with psycopg.connect(database_url) as db:
        assert db.execute("SELECT status,district FROM community_post WHERE id=%s", (post_id,)).fetchone() == ('hidden', None)


def test_neighborhood_summary_is_k_anonymous(client):
    headers = register(client, 'grower0')
    enable_profile(client, headers, 'Grower zero')
    add_plant(client, headers)
    for index in range(1, 5):
        other = register(client, f'grower{index}')
        enable_profile(client, other, f'Grower {index}')
        add_plant(client, other)
    summary = client.get('/v1/community/neighborhood', headers=headers)
    assert summary.status_code == 200
    assert summary.json()['available'] is True
    assert summary.json()['participating_growers'] == 5
