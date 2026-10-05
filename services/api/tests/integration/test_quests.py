"""Quest ownership, weather consent and additive upgrades in fixture-owned DBs."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import psycopg
import pytest

from app.catalog_bundle import CatalogBundle, today_bd
from app.catalog_import import import_bundle
from app.migrations import run
from tests.integration.test_care_plans import client, register, approved_bundle, saved, payload

pytestmark=pytest.mark.integration


def setup_plan(client, database_url):
    value=approved_bundle()
    yesterday=(today_bd()-timedelta(days=1)).isoformat()
    for source in value['sources']: source['checked_at']=yesterday
    for plant in value['plants']:
        for profile in plant['profiles']:
            profile['reviewed_at']=yesterday
            for instruction in profile.get('care_guidance',[]): instruction['reviewed_at']=yesterday
    import_bundle(CatalogBundle.model_validate(value),database_url)
    headers=register(client)
    # All synthetic evidence predates planting; no real records are approved here.
    goal=payload()['goal']; goal['planting_date']=(today_bd()-timedelta(days=1)).isoformat()
    plan=saved(client,headers,goal=goal)
    return headers,plan['plan_id']


def test_quests_are_owned_idempotent_and_withheld_after_review_changes(client,database_url):
    headers,plan_id=setup_plan(client,database_url)
    path=f'/v1/plans/{plan_id}/quests'
    assert client.get(path).status_code==401
    response=client.get(path,headers=headers)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    board=response.json(); assert len(board['quests'])==4
    other=register(client,'quest_other')
    assert client.get(path,headers=other).status_code==404
    q=board['quests'][0]
    body={'version':1,'key':q['key'],'completed':True}
    assert client.post(path+'/completion',headers=other,json=body).status_code==404
    for _ in range(2):
        result=client.post(path+'/completion',headers=headers,json=body)
        assert result.status_code==200
    assert result.json()['quests'][0]['completed']
    assert client.put(path+'/weather',headers=other,json={'enabled':True,'notice_version':'weather-2026-10-05'}).status_code==404
    undone=client.post(path+'/completion',headers=headers,json={**body,'completed':False})
    assert not undone.json()['quests'][0]['completed']
    client.post(path+'/completion',headers=headers,json=body)
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM quest_completion').fetchone()[0]==1
        db.execute("UPDATE plant_care_guidance SET instruction_en='Changed reviewed instruction'")
    assert client.get(path,headers=headers).json()['quests']==[]
    assert client.post(path+'/completion',headers=headers,json=body).status_code==409


def test_weather_optin_supported_location_and_no_calls_without_it(client,database_url,monkeypatch):
    from app.quest_repository import QuestRepository
    from app.weather import Forecast,ForecastDay
    headers,plan_id=setup_plan(client,database_url)
    path=f'/v1/plans/{plan_id}/quests'
    calls=[]
    def fetch(self,district,latitude,longitude):
        calls.append(district)
        return Forecast(fetched_at=datetime.now(timezone.utc),district=district,days=[
            ForecastDay(day=today_bd(),rain_mm=9,rain_probability=90,max_temperature_c=38)])
    monkeypatch.setenv('WEATHER_MODE','open-meteo-noncommercial')
    monkeypatch.setattr(QuestRepository,'_fetch_weather',fetch)
    assert client.get(path,headers=headers).json()['weather']['status']=='disabled'
    assert not calls
    settings={'enabled':True,'notice_version':'weather-2026-10-05'}
    assert client.put(path+'/weather',headers=headers,json=settings).status_code==200
    assert not calls  # preference writes never call the provider
    board=client.get(path,headers=headers).json()
    assert calls==['dhaka'] and board['weather']['status']=='fresh'
    assert any(q['adaptation']=='rain_check' for q in board['quests'])
    client.get(path,headers=headers); assert calls==['dhaka'] # shared bounded cache
    assert client.put(path+'/weather',headers=headers,json={**settings,'enabled':False}).status_code==200
    assert client.get(path,headers=headers).json()['weather']['status']=='disabled'
    assert calls==['dhaka']


def test_stale_cache_failure_corruption_and_session_recheck(client,database_url,monkeypatch):
    from app.quest_repository import QuestRepository
    from app.weather import Forecast,ForecastDay
    from psycopg.types.json import Jsonb
    from urllib.error import URLError
    headers,plan_id=setup_plan(client,database_url)
    path=f'/v1/plans/{plan_id}/quests'
    settings={'enabled':True,'notice_version':'weather-2026-10-05'}
    assert client.put(path+'/weather',headers=headers,json=settings).status_code==200
    assert client.get(path,headers=headers).json()['weather']['status']=='provider_disabled'
    monkeypatch.setenv('WEATHER_MODE','open-meteo-noncommercial')
    stale=Forecast(fetched_at=datetime.now(timezone.utc)-timedelta(hours=8),district='dhaka',days=[
        ForecastDay(day=today_bd(),rain_mm=50,rain_probability=100,max_temperature_c=45)])
    with psycopg.connect(database_url) as db:
        db.execute('INSERT INTO regional_forecast(district,attempted_at,forecast) VALUES(%s,%s,%s)',
            ('dhaka',datetime.now(timezone.utc)-timedelta(hours=1),Jsonb(stale.model_dump(mode='json'))))
    def fail(*args):raise URLError('PRIVATE provider details')
    monkeypatch.setattr('app.quest_repository.fetch_forecast',fail)
    response=client.get(path,headers=headers)
    assert response.status_code==200 and 'PRIVATE' not in response.text
    assert response.json()['weather']['status']=='stale'
    assert all(q['adaptation']=='none' for q in response.json()['quests'])
    with psycopg.connect(database_url) as db:
        db.execute("UPDATE regional_forecast SET forecast='{}'")
    assert client.get(path,headers=headers).json()['weather']['status']=='unavailable'
    def revoke(*args):
        with psycopg.connect(database_url) as db:
            db.execute("UPDATE account_session SET created_at=now()-interval '2 hours',expires_at=now()-interval '1 hour'")
        return stale
    with psycopg.connect(database_url) as db:
        db.execute("UPDATE regional_forecast SET attempted_at=now()-interval '1 hour'")
    monkeypatch.setattr('app.quest_repository.fetch_forecast',revoke)
    assert client.get(path,headers=headers).status_code==401
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT forecast FROM regional_forecast').fetchone()[0]=={}


def test_revision_resets_completions_weather_and_plan_deletion_cascades(client,database_url):
    headers,plan_id=setup_plan(client,database_url)
    path=f'/v1/plans/{plan_id}/quests'
    first=client.get(path,headers=headers).json()
    client.put(path+'/weather',headers=headers,json={'enabled':True,'notice_version':'weather-2026-10-05'})
    key=first['quests'][0]['key']
    client.post(path+'/completion',headers=headers,json={'version':1,'key':key,'completed':True})
    goal=payload()['goal'];goal['planting_date']=(today_bd()-timedelta(days=1)).isoformat()
    goal['area_m2']=3
    response=client.post(f'/v1/plans/{plan_id}/versions',headers=headers,json=payload(
        goal=goal,expected_version=1,save_notice_version='care-plan-2026-10-04'))
    assert response.status_code==200 and response.json()['version']==2
    board=client.get(path,headers=headers).json()
    assert not board['weather_enabled'] and not any(q['completed'] for q in board['quests'])
    client.delete(f'/v1/plans/{plan_id}',headers=headers)
    with psycopg.connect(database_url) as db:
        assert db.execute('SELECT count(*) FROM quest_completion').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM plan_weather_preference').fetchone()[0]==0


def test_completion_rejects_unknown_future_version_and_owner_fields(client,database_url):
    headers,plan_id=setup_plan(client,database_url)
    path=f'/v1/plans/{plan_id}/quests'
    for body,status in [({'version':1,'key':'unknown','completed':True},409),
                        ({'version':2,'key':'observation:2099-01-01','completed':True},409),
                        ({'version':1,'key':'test','completed':True,'owner_id':str(uuid4())},422)]:
        assert client.post(path+'/completion',headers=headers,json=body).status_code==status
    assert client.get(path+'?days=100',headers=headers).status_code==422


def test_0006_preserves_old_plan_rows_and_blocks_destructive_rollback(database_url,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    run('upgrade',database_url,'0005')
    monkeypatch.setenv('DATABASE_URL',database_url);monkeypatch.setenv('APP_ENV','development')
    # Simulate the old application's exact head only while creating fixture rows.
    with monkeypatch.context() as previous_app:
        previous_app.setattr('app.migrations.head_revision',lambda:'0005')
        with TestClient(create_app()) as c:
            headers,plan_id=setup_plan(c,database_url)
    with psycopg.connect(database_url) as db:
        before=db.execute('SELECT * FROM care_plan_version').fetchall()
    assert run('upgrade',database_url)==('0009',)
    with psycopg.connect(database_url) as db:
        assert before==db.execute('SELECT * FROM care_plan_version').fetchall()
        assert db.execute('SELECT count(*) FROM quest_completion').fetchone()[0]==0
    with pytest.raises(RuntimeError,match='community'):
        run('downgrade',database_url,'0005',confirm=True)
    assert run('current',database_url)==('0009',)
