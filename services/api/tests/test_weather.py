"""Provider transport is mocked; no requests or credentials leave the test suite."""
from datetime import datetime,timezone
import json
from urllib.error import URLError

import pytest

from app import weather
from tests.test_quests import raw_weather


def test_fixed_host_timeout_size_bound_and_parsed_retrieval_time(monkeypatch):
    monkeypatch.setenv('WEATHER_MODE','open-meteo-noncommercial')
    today=datetime.now(timezone.utc).astimezone(weather.BD).date().isoformat()
    raw=raw_weather();raw['daily']['time']=[today]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):
            assert limit==65537
            return json.dumps(raw).encode()
    class Opener:
        def open(self,req,timeout):
            assert timeout==5
            assert req.full_url.startswith('https://api.open-meteo.com/v1/forecast?latitude=23.81&longitude=90.41')
            assert 'authorization' not in {k.lower() for k in req.headers}
            return Response()
    monkeypatch.setattr(weather,'build_opener',lambda *_:Opener())
    result=weather.fetch_forecast('dhaka',23.81,90.41)
    assert result.district=='dhaka' and result.fetched_at.tzinfo is not None
    monkeypatch.setattr(Response,'read',lambda *_:b'x'*65537)
    with pytest.raises(ValueError,match='too large'):weather.fetch_forecast('dhaka',23.81,90.41)
    assert weather.NoRedirect().redirect_request(None,None,None,None,None,None) is None


def test_disabled_provider_never_opens_network(monkeypatch):
    monkeypatch.delenv('WEATHER_MODE',raising=False)
    with pytest.raises(ValueError,match='disabled'):weather.fetch_forecast('dhaka',23.81,90.41)


def test_parse_rejects_timezone_oversized_and_malformed_response():
    now=datetime(2026,10,5,tzinfo=timezone.utc)
    for change in [None,{}, {'timezone':'UTC'}, {'daily':{'time':[]}}]:
        raw=raw_weather()
        if change is None:raw=None
        elif change=={}:raw={}
        else:raw.update(change)
        with pytest.raises(ValueError):weather.parse_forecast(raw,'dhaka',now)
