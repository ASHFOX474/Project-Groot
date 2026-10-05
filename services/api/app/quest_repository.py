"""Short owner transactions surround network I/O; latest evidence gates every task."""
from datetime import datetime, timedelta, timezone
import os
from urllib.error import URLError

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from app.care_repository import CarePlanRepository
from app.quests import build_board
from app.weather import Forecast, district_point, fetch_forecast


class QuestRepository(CarePlanRepository):
    def _context(self,db,token,plan_id):
        owner=self._owner(db,token)['id']
        self._plan(db,owner,plan_id)
        version=self._render(db,self._version(db,owner,plan_id))
        preference=db.execute('''SELECT enabled FROM plan_weather_preference
            WHERE plan_id=%s AND owner_id=%s AND version=%s''',(plan_id,owner,version.version)).fetchone()
        enabled=bool(preference and preference['enabled'])
        done=db.execute('''SELECT quest_key FROM quest_completion WHERE plan_id=%s
                            AND owner_id=%s AND version=%s''',(plan_id,owner,version.version)).fetchall()
        return owner,version,enabled,[q['quest_key'] for q in done]

    def preference(self,token,plan_id,value):
        with self._connect() as db:
            owner,version,_,_=self._context(db,token,plan_id)
            if value.enabled and (version.availability!='current' or not district_point(version.conditions.location)):
                raise HTTPException(409,'A current plan with a supported district is required')
            db.execute('''INSERT INTO plan_weather_preference(plan_id,owner_id,version,enabled,notice_version)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT(plan_id,version) DO UPDATE
                SET enabled=excluded.enabled,notice_version=excluded.notice_version,updated_at=now()''',
                (plan_id,owner,version.version,value.enabled,value.notice_version))
            self._owner(db,token)
            return {'enabled':value.enabled,'version':version.version}

    def _fetch_weather(self,district,latitude,longitude):
        return fetch_forecast(district,latitude,longitude)

    @staticmethod
    def _cached(db,district):
        row=db.execute('SELECT forecast FROM regional_forecast WHERE district=%s',(district,)).fetchone()
        if not row or row['forecast'] is None: return None
        try:
            result=Forecast.model_validate(row['forecast'])
            return result if result.district==district else None
        except ValueError:
            return None

    def board(self,token,plan_id,days=1):
        now=datetime.now(timezone.utc)
        point=None; claimed=False
        with self._connect() as db:
            _,version,enabled,done=self._context(db,token,plan_id)
            if enabled and version.availability=='current':
                point=district_point(version.conditions.location)
            reason=('provider_disabled' if enabled and os.environ.get('WEATHER_MODE')!='open-meteo-noncommercial'
                    else 'unsupported' if enabled and point is None else None)
            if point and reason is None:
                # Shared fixed district keys cap outbound calls; retries, including failures,
                # are at most once per district / 15 min across all accounts and workers.
                claimed=db.execute('''INSERT INTO regional_forecast(district,attempted_at) VALUES(%s,%s)
                    ON CONFLICT(district) DO UPDATE SET attempted_at=excluded.attempted_at
                    WHERE regional_forecast.attempted_at<=%s RETURNING district''',
                    (point[0],now,now-timedelta(minutes=15))).fetchone() is not None
            self._owner(db,token)
        # No account/plan locks or DB connections are held while calling a provider.
        fresh=None
        if claimed:
            try:
                fresh=self._fetch_weather(*point)
            except (URLError,OSError,ValueError):
                pass  # no exception details, provider URLs or user input returned/logged
        with self._connect() as db:
            _,version,enabled,done=self._context(db,token,plan_id)  # expiry/revocation/revision recheck
            current_point=district_point(version.conditions.location) if enabled else None
            reason=('provider_disabled' if enabled and os.environ.get('WEATHER_MODE')!='open-meteo-noncommercial'
                    else 'unsupported' if enabled and current_point is None else None)
            if fresh and point==current_point and version.availability=='current':
                db.execute('UPDATE regional_forecast SET forecast=%s WHERE district=%s AND attempted_at=%s',
                    (Jsonb(fresh.model_dump(mode='json')),point[0],now))
            cached=self._cached(db,current_point[0]) if current_point and reason is None else None
            result=build_board(version,datetime.now(timezone.utc),cached,done,enabled,days,
                weather_reason=reason if enabled else None)
            self._owner(db,token)
            return result

    def complete(self,token,plan_id,value):
        with self._connect() as db:
            owner,version,enabled,done=self._context(db,token,plan_id)
            board=build_board(version,datetime.now(timezone.utc),None,done,enabled)
            quest=next((q for q in board.quests if q.key==value.key),None)
            if version.version!=value.version or quest is None or quest.starts_on>board.today:
                raise HTTPException(409,'Quest changed or unavailable. Reload current tasks.')
            if value.completed:
                db.execute('''INSERT INTO quest_completion(plan_id,owner_id,version,quest_key)
                    VALUES(%s,%s,%s,%s) ON CONFLICT(plan_id,version,quest_key) DO NOTHING''',
                    (plan_id,owner,version.version,value.key))
            else:
                db.execute('DELETE FROM quest_completion WHERE plan_id=%s AND owner_id=%s AND version=%s AND quest_key=%s',
                    (plan_id,owner,version.version,value.key))
            self._owner(db,token)
        # Completion itself never makes a provider call; UI can explicitly refresh weather.
        with self._connect() as db:
            _,version,enabled,done=self._context(db,token,plan_id)
            point=district_point(version.conditions.location) if enabled else None
            reason=('provider_disabled' if enabled and os.environ.get('WEATHER_MODE')!='open-meteo-noncommercial'
                    else 'unsupported' if enabled and point is None else None)
            result=build_board(version,datetime.now(timezone.utc),self._cached(db,point[0]) if point and reason is None else None,
                done,enabled,weather_reason=reason)
            self._owner(db,token)
            return result


def get_quest_repository():
    return QuestRepository()
