from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.accounts import Credentials, PassportInput, hash_password, verify_password, token_digest
from app import accounts
from app.privacy_middleware import PrivacyMiddleware
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import create_app
from app.accounts import get_account_repository
import asyncio
import psycopg


def test_password_hashes_are_salted_and_never_plaintext():
    password = 'a long unique passphrase'
    first, second = hash_password(password), hash_password(password)
    assert first != second and password not in first
    assert verify_password(password, first)
    assert not verify_password('another long password', first)
    assert not verify_password(password, 'corrupt')
    assert len(token_digest('session')) == 64


@pytest.mark.parametrize('changes', [
    {'password': 'short'}, {'handle': 'email@example.com'},
    {'handle': 'a'}, {'admin': True}, {'password': 'x' * 129},
    {'password': 'passwordpassword'}, {'password': ' '*15}, {'password': 'x'*15},
    {'password': 'a long bad\x00password'}, {'password': 'a long bad\ud800password'},
])
def test_credentials_reject_invalid_or_extra_fields(changes):
    with pytest.raises(ValidationError):
        Credentials.model_validate({'handle': 'grower', 'password': 'a long unique passphrase', **changes})


def test_handle_is_normalized_but_password_is_not_trimmed():
    value = Credentials(handle=' GROWER ', password='  a long passphrase  ')
    assert value.handle == 'grower'
    assert value.password.get_secret_value() == '  a long passphrase  '


def test_passport_rejects_future_date_and_unrecognized_conditions():
    valid = {'nickname': 'My okra', 'species_name': 'Okra', 'planted_on': date.today().isoformat(),
             'conditions': {'growing_context': 'container', 'sunlight': 'unknown', 'soil': 'Unknown'}}
    assert PassportInput.model_validate(valid).species_name == 'Okra'
    with pytest.raises(ValidationError):
        PassportInput.model_validate({**valid, 'planted_on': (date.today() + timedelta(days=2)).isoformat()})
    with pytest.raises(ValidationError):
        PassportInput.model_validate({**valid, 'conditions': {'latitude': 23.5}})


def test_corrupt_hash_and_memory_bound_are_safe():
    assert not verify_password('any password', 'other$' + 'aa'*16 + '$' + 'bb'*32)
    assert not verify_password('any password', 'scrypt-v1$' + 'zz'*16 + '$' + '00'*32)
    assert accounts._password_slots.acquire(blocking=False)
    assert accounts._password_slots.acquire(blocking=False)
    try:
        with pytest.raises(HTTPException) as error:
            hash_password('a long unique passphrase')
        assert error.value.status_code == 503
    finally:
        accounts._password_slots.release()
        accounts._password_slots.release()
    assert isinstance(accounts.get_account_repository(), accounts.AccountRepository)


def test_database_errors_do_not_expose_private_values(monkeypatch):
    class Unavailable:
        def throttle(self, *args):
            raise psycopg.OperationalError('password or private note')
    monkeypatch.setenv('APP_ENV', 'development')
    app = create_app()
    app.dependency_overrides[get_account_repository] = lambda: Unavailable()
    with TestClient(app) as client:
        response = client.get('/v1/accounts/me')
        assert response.status_code == 503
        assert 'password' not in response.text and 'private note' not in response.text


def test_body_limit_covers_chunks_and_disconnects(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    messages = []
    async def app(scope, receive, send):
        messages.append(await receive())
    middleware = PrivacyMiddleware(app)
    async def check(chunks):
        responses = []
        async def receive():
            return chunks.pop(0)
        async def send(message):
            responses.append(message)
        await middleware({'type': 'http', 'path': '/v1/accounts/register', 'method': 'POST', 'scheme': 'http'}, receive, send)
        return responses
    assert asyncio.run(check([{'type': 'http.disconnect'}])) == []
    response = asyncio.run(check([
        {'type': 'http.request', 'body': b'x'*8000, 'more_body': True},
        {'type': 'http.request', 'body': b'x'*9000, 'more_body': False}]))
    assert response[0]['status'] == 413 and not messages
