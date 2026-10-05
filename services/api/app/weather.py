"""Bounded, coarse-location forecast adapter. Never infer GPS or soil moisture."""
from datetime import date, datetime, timedelta, timezone
import json
import os
from typing import Annotated
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

from pydantic import Field

from app.accounts import StrictModel
from app.recommendations import district_key

BD = timezone(timedelta(hours=6))
# Approximate city reference points, not a user's home or a district-wide guarantee.
DISTRICTS = {
    'dhaka': (23.81,90.41), 'chattogram': (22.36,91.78),
    'rajshahi': (24.37,88.60), 'khulna': (22.85,89.54),
    'sylhet': (24.90,91.87), 'rangpur': (25.75,89.25),
    'barishal': (22.70,90.35), 'mymensingh': (24.75,90.41),
}


class ForecastDay(StrictModel):
    day: date
    rain_mm: Annotated[float, Field(strict=True,ge=0,le=2000,allow_inf_nan=False)]
    rain_probability: Annotated[float, Field(strict=True,ge=0,le=100,allow_inf_nan=False)]
    max_temperature_c: Annotated[float, Field(strict=True,ge=-20,le=60,allow_inf_nan=False)]


class Forecast(StrictModel):
    fetched_at: datetime
    district: str
    days: Annotated[list[ForecastDay], Field(min_length=1,max_length=7)]


class WeatherView(StrictModel):
    status: Literal['fresh','stale','unavailable','disabled','unsupported','provider_disabled']
    district: str | None = None
    fetched_at: datetime | None = None
    message: str
    attribution: str = 'Weather data: Open-Meteo (CC BY 4.0); regional estimate, not plot conditions.'
    source_url: str = 'https://open-meteo.com/'


def district_point(location):
    if location.precision != 'district' or location.country_code != 'BD':
        return None
    district = district_key(location.district or '')
    if district not in DISTRICTS:
        return None
    return (district,*DISTRICTS[district])


def weather_status(forecast, now):
    if forecast is None:
        return 'unavailable'
    fetched = forecast.fetched_at
    if fetched.tzinfo is None or not timedelta(0) <= now-fetched < timedelta(hours=6):
        return 'stale'
    if now.astimezone(BD).date() not in {d.day for d in forecast.days}:
        return 'stale'
    return 'fresh'


def parse_forecast(raw, district, now):
    try:
        if raw['timezone'] != 'Asia/Dhaka' or raw['utc_offset_seconds'] != 21600:
            raise ValueError('Forecast timezone mismatch')
        units = raw['daily_units']
        if any(units[k]!=u for k,u in [('temperature_2m_max','°C'),
                ('precipitation_sum','mm'),('precipitation_probability_max','%')]):
            raise ValueError('Forecast units mismatch')
        daily = raw['daily']
        dates = daily['time']
        if not isinstance(dates,list) or not 1<=len(dates)<=7:
            raise ValueError('Forecast date bounds')
        fields=['precipitation_sum','precipitation_probability_max','temperature_2m_max']
        if any(not isinstance(daily[k],list) or len(daily[k])!=len(dates) for k in fields):
            raise ValueError('Forecast array mismatch')
        days=[ForecastDay(day=d,rain_mm=daily[fields[0]][i],
                rain_probability=daily[fields[1]][i],max_temperature_c=daily[fields[2]][i])
              for i,d in enumerate(dates)]
        today=now.astimezone(BD).date()
        if [d.day for d in days] != [today+timedelta(days=i) for i in range(len(days))]:
            raise ValueError('Forecast date mismatch')
        return Forecast(fetched_at=now,district=district,days=days)
    except (KeyError, TypeError, ValueError):
        raise ValueError('Invalid forecast response') from None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_forecast(district, latitude, longitude):
    # Explicit operator enablement after reviewing non-commercial service terms.
    if os.environ.get('WEATHER_MODE') != 'open-meteo-noncommercial':
        raise ValueError('Weather provider disabled')
    params=urlencode({'latitude':latitude,'longitude':longitude,'timezone':'Asia/Dhaka',
        'daily':'temperature_2m_max,precipitation_sum,precipitation_probability_max',
        'forecast_days':7,'temperature_unit':'celsius','precipitation_unit':'mm'})
    request=Request('https://api.open-meteo.com/v1/forecast?'+params,
                    headers={'User-Agent':'GrootPrototype/0.1','Accept':'application/json'})
    # Fixed HTTPS host; no user URL, redirects, account details or bearer credentials.
    with build_opener(NoRedirect).open(request,timeout=5) as response:
        payload=response.read(65537)
        if len(payload)>65536:
            raise ValueError('Forecast too large')
        return parse_forecast(json.loads(payload),district,datetime.now(timezone.utc))
