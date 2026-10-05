"""Deterministic schedules and weather safety; never call a live provider."""
from datetime import datetime, timedelta, timezone, date
from uuid import uuid4

import pytest

from app.care_models import PlanVersion
from app.care_plans import build_plan
from app.quests import build_board
from app.weather import Forecast, ForecastDay, weather_status, parse_forecast, district_point
from tests.test_care_plans import request, guidance
from tests.test_recommendations import candidate

NOW = datetime(2026, 10, 5, 4, tzinfo=timezone.utc)


def version():
    value = request()
    return PlanVersion(plan_id=uuid4(), version=1, created_at=NOW,
        fingerprint='a'*64, availability='current', conditions=value.goal,
        plan=build_plan(value, [candidate()], guidance()))


def forecast(age=0, rain=0, heat=30):
    return Forecast(fetched_at=NOW-timedelta(hours=age), district='dhaka', days=[
        ForecastDay(day=date(2026,10,5), rain_mm=rain, rain_probability=80, max_temperature_c=heat)])


def test_daily_observation_and_weekly_review_do_not_invent_action_frequency():
    board = build_board(version(), NOW, None, [], False)
    assert len([q for q in board.quests if q.cadence=='daily']) == 1
    weekly = [q for q in board.quests if q.cadence=='weekly']
    assert len(weekly) == 3 and all(q.instruction for q in weekly)
    assert all('Review' in q.title for q in weekly)
    assert len({q.key for q in board.quests}) == len(board.quests)
    assert all(q.starts_on <= q.due_on for q in board.quests)


def test_rain_and_heat_add_checks_without_changing_reviewed_text_or_keys():
    saved = version()
    base = build_board(saved, NOW, None, [], True)
    rainy = build_board(saved, NOW, forecast(rain=7, heat=36), [], True)
    water = next(q for q in rainy.quests if q.topic=='watering')
    assert water.adaptation == 'rain_check' and 'soil' in water.weather_note.lower()
    assert 'heat_check' in [q.adaptation for q in rainy.quests]
    assert [(q.key,q.instruction) for q in base.quests] == [(q.key,q.instruction) for q in rainy.quests]


@pytest.mark.parametrize('age', [6, 48])
def test_stale_forecasts_never_adapt_tasks(age):
    value=forecast(age=age,rain=50,heat=45)
    assert weather_status(value,NOW)=='stale'
    board=build_board(version(),NOW,value,[],True)
    assert all(q.adaptation=='none' for q in board.quests)
    assert board.weather.status=='stale'


def test_changed_evidence_withholds_all_tasks_and_version_completion_is_scoped():
    v=version()
    one=build_board(v,NOW,None,[],False)
    done=[one.quests[0].key]
    assert build_board(v,NOW,None,done,False).quests[0].completed
    v.availability='stale'
    assert build_board(v,NOW,None,done,False).quests==[]
    v=version(); v.conditions.planting_date=date(2026,11,1)
    assert build_board(v,NOW,None,[],False).quests==[]


def test_weather_date_freshness_and_district_precision():
    assert weather_status(forecast(age=-1),NOW)=='stale'
    value=forecast(); value.days[0].day=date(2026,10,4)
    assert weather_status(value,NOW)=='stale'
    assert district_point(version().conditions.location)==('dhaka',23.81,90.41)
    v=version(); v.conditions.location.precision='country'; v.conditions.location.district=None
    assert district_point(v.conditions.location) is None
    v.conditions.location.precision='district';v.conditions.location.district='not-a-supported-district'
    assert district_point(v.conditions.location) is None
    v.conditions.location.district='ঢাকা'
    assert district_point(v.conditions.location)==('dhaka',23.81,90.41)


def test_partial_plan_discloses_gaps_and_never_schedules_missing_topic():
    v=version();v.plan.status='partial'
    v.plan.instructions=[q for q in v.plan.instructions if q.topic!='watering']
    board=build_board(v,NOW,None,[],False)
    assert not any(q.topic=='watering' for q in board.quests)
    assert 'Partial plan' in board.message


def raw_weather():
    return {'timezone':'Asia/Dhaka','utc_offset_seconds':21600,
        'daily_units':{'temperature_2m_max':'°C','precipitation_sum':'mm','precipitation_probability_max':'%'},
        'daily':{'time':['2026-10-05'],'temperature_2m_max':[35],
            'precipitation_sum':[4],'precipitation_probability_max':[75]}}


def test_parse_forecast_validates_units_dates_arrays_and_values():
    assert parse_forecast(raw_weather(),'dhaka',NOW).days[0].rain_mm==4
    for field,value in [('temperature_2m_max',[float('nan')]),('precipitation_sum',[-1]),
                        ('time',['2026-09-01']),('precipitation_probability_max',[])]:
        raw=raw_weather(); raw['daily'][field]=value
        with pytest.raises(ValueError): parse_forecast(raw,'dhaka',NOW)
    raw=raw_weather();raw['daily_units']['precipitation_sum']='inch'
    with pytest.raises(ValueError):parse_forecast(raw,'dhaka',NOW)
