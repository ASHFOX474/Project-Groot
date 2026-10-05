"""Local account security and transactional owner-scoped Plant Passports.

No email identities, external sharing, location capture or recommendation logic.
"""
from __future__ import annotations

from datetime import date
import hashlib
import hmac
import secrets
from threading import BoundedSemaphore
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, field_validator
from psycopg.types.json import Jsonb

from app.catalog_bundle import today_bd
from app.database import CatalogRepository

NOTICE_VERSION = '2026-10-04'
_password_slots = BoundedSemaphore(2)
Text80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

    @field_validator('*')
    @classmethod
    def database_safe_text(cls, value):
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if isinstance(raw, str):
            try:
                raw.encode('utf-8')
            except UnicodeError:
                raise ValueError('Text must be valid Unicode') from None
            if '\x00' in raw:
                raise ValueError('Null characters are not accepted')
        return value


class Choices(StrictModel):
    location_opt_in: bool = Field(default=False, strict=True)
    community_opt_in: bool = Field(default=False, strict=True)
    impact_opt_in: bool = Field(default=False, strict=True)


class Credentials(StrictModel):
    handle: Annotated[str, StringConstraints(pattern=r'^[a-z0-9_]{3,32}$')]
    password: SecretStr = Field(min_length=15, max_length=128)

    @field_validator('handle', mode='before')
    @classmethod
    def normalize_handle(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator('password')
    @classmethod
    def obvious_weak_password(cls, value):
        raw = value.get_secret_value()
        if not raw.strip() or len(set(raw)) == 1 or raw.casefold() in {
            'passwordpassword', 'password123456789', '123456789012345', 'qwertyuiopasdfgh',
        }:
            raise ValueError('Choose a less predictable passphrase')
        return value


class Registration(Credentials):
    choices: Choices = Field(default_factory=Choices)
    notice_version: Literal['2026-10-04']


class ConsentInput(StrictModel):
    choices: Choices
    notice_version: Literal['2026-10-04']


class PasswordChange(StrictModel):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=15, max_length=128)

    @field_validator('new_password')
    @classmethod
    def obvious_weak_password(cls, value):
        return Credentials.obvious_weak_password(value)


class AccountDelete(StrictModel):
    password: SecretStr = Field(min_length=1, max_length=128)


class Conditions(StrictModel):
    growing_context: Literal['container', 'open_ground', 'forestry']
    sunlight: Literal['full_sun', 'partial_shade', 'shade', 'unknown'] = 'unknown'
    soil: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    approximate_area: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] = ''


class PassportInput(StrictModel):
    nickname: Text80
    species_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    species_id: Annotated[str, StringConstraints(min_length=2, max_length=80)] | None = None
    planted_on: date
    conditions: Conditions

    @field_validator('planted_on')
    @classmethod
    def not_future(cls, value):
        if value < date(1900, 1, 1) or value > today_bd():
            raise ValueError('Date must be from 1900 through today')
        return value


class CareFields(StrictModel):
    kind: Literal['watering', 'feeding', 'pruning', 'repotting', 'observation']
    occurred_on: date
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ''

    @field_validator('occurred_on')
    @classmethod
    def not_future(cls, value):
        return PassportInput.not_future(value)


class CareInput(CareFields):
    # Optional for old online clients. Offline clients must persist this UUID
    # before sending; it is scoped to the authenticated owner, not a caller owner.
    request_id: UUID | None = None


class AccountResponse(StrictModel):
    id: UUID
    handle: str
    choices: Choices
    notice_version: str


class SessionResponse(StrictModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
    expires_in: int = 43200
    account: AccountResponse


class PassportResponse(PassportInput):
    id: UUID
    # Dates written by the DB are serialized by FastAPI, without secrets/ownership fields.


class CareResponse(CareFields):
    id: UUID


def _derive(password, salt):
    # Bound memory-heavy work per process as well as requests per identity/IP.
    if not _password_slots.acquire(blocking=False):
        raise HTTPException(503, 'Sign-in busy. Try again shortly.')
    try:
        return hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2**17, r=8, p=1,
                              maxmem=192 * 1024 * 1024, dklen=32)
    finally:
        _password_slots.release()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    value = _derive(password, salt)
    return 'scrypt-v1$' + salt.hex() + '$' + value.hex()


def verify_password(password: str, encoded: str) -> bool:
    try:
        version, salt, expected = encoded.split('$')
        if version != 'scrypt-v1' or len(salt) != 32 or len(expected) != 64:
            return False
        value = _derive(password, bytes.fromhex(salt))
        return hmac.compare_digest(value, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def public_account(row) -> dict:
    return {'id': row['id'], 'handle': row['handle'], 'notice_version': row['notice_version'],
            'choices': {key: row[key] for key in Choices.model_fields}}


class AccountRepository(CatalogRepository):
    def _connect(self):
        db = super()._connect()
        db.execute("SET LOCAL lock_timeout='5s'")
        db.execute("SET LOCAL statement_timeout='10s'")
        return db

    def throttle(self, scope: str, identifier: str, limit: int, seconds: int = 900):
        """Atomic fixed window shared by workers; retains only pseudonymous digests."""
        key = token_digest(scope + ':' + identifier)
        with self._connect() as db:
            db.execute('DELETE FROM auth_rate_bucket WHERE expires_at <= now()')
            row = db.execute('''
                INSERT INTO auth_rate_bucket(key_hash,attempts,expires_at)
                VALUES (%s,1,now() + %s * interval '1 second')
                ON CONFLICT (key_hash) DO UPDATE SET attempts=auth_rate_bucket.attempts+1
                RETURNING attempts
            ''', (key, seconds)).fetchone()
        # Raise after commit: failed requests must consume their attempt too.
        if row['attempts'] > limit:
            raise HTTPException(429, 'Too many attempts. Try again later.', headers={'Retry-After': str(seconds)})

    def register(self, value: Registration) -> dict:
        password_hash = hash_password(value.password.get_secret_value())
        with self._connect() as db:
            row = db.execute('''
                INSERT INTO grower_account(id,handle,password_hash,location_opt_in,community_opt_in,impact_opt_in,notice_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (handle) DO NOTHING RETURNING *
            ''', (uuid4(), value.handle, password_hash, value.choices.location_opt_in,
                  value.choices.community_opt_in, value.choices.impact_opt_in, value.notice_version)).fetchone()
            if row is None:
                raise HTTPException(409, 'Account could not be created. Choose another handle.')
            self._consent_receipt(db, row['id'], value.choices, value.notice_version)
            return self._new_session(db, row)

    def login(self, value: Credentials) -> dict:
        with self._connect() as db:
            # Serialize login/password change so an old credential cannot issue a new
            # session concurrently after a password change has revoked prior sessions.
            row = db.execute('SELECT * FROM grower_account WHERE handle=%s FOR UPDATE', (value.handle,)).fetchone()
            if row is None:
                hash_password(value.password.get_secret_value())  # comparable work for unknown handle
                raise HTTPException(401, 'Incorrect handle or password', headers={'WWW-Authenticate': 'Bearer'})
            if not verify_password(value.password.get_secret_value(), row['password_hash']):
                raise HTTPException(401, 'Incorrect handle or password', headers={'WWW-Authenticate': 'Bearer'})
            return self._new_session(db, row)

    def _new_session(self, db, row):
        token = secrets.token_urlsafe(32)
        db.execute('DELETE FROM account_session WHERE account_id=%s AND expires_at<=now()', (row['id'],))
        # Cap live sessions per account; a new login replaces the oldest when full.
        db.execute('''DELETE FROM account_session WHERE token_hash IN (
            SELECT token_hash FROM account_session WHERE account_id=%s
            ORDER BY created_at DESC,token_hash OFFSET 4
        )''', (row['id'],))
        db.execute('INSERT INTO account_session(token_hash,account_id,expires_at) VALUES (%s,%s,now()+interval \'12 hours\')',
                   (token_digest(token), row['id']))
        return {'access_token': token, 'account': public_account(row)}

    def _owner(self, db, token):
        # Lock account first, then recheck its session. Protected writes serialize with
        # logout/password change/deletion; no stale authorization survives revocation.
        row = db.execute('''SELECT a.* FROM grower_account a JOIN account_session s ON s.account_id=a.id
                            WHERE s.token_hash=%s FOR UPDATE OF a''', (token_digest(token),)).fetchone()
        if row is None or not db.execute('''SELECT 1 FROM account_session
                 WHERE token_hash=%s AND account_id=%s AND expires_at>clock_timestamp()''',
                 (token_digest(token), row['id'])).fetchone():
            raise HTTPException(401, 'Sign in again', headers={'WWW-Authenticate': 'Bearer'})
        return row

    def me(self, token):
        with self._connect() as db:
            return public_account(self._owner(db, token))

    def recommend_goal(self, token, value):
        # Lazy import keeps the shared strict input contract free of import cycles.
        from app.recommendations import recommend
        with self._connect() as db:
            self._owner(db, token)
            candidates = self.recommendation_candidates_from(db)
            try:
                result = recommend(value, candidates)
            except (ValueError, KeyError, TypeError):
                raise RuntimeError('Catalog contains invalid recommendation evidence') from None
            self._owner(db, token)  # recheck wall-clock expiry before returning
            return result

    def logout(self, token):
        with self._connect() as db:
            self._owner(db, token)
            db.execute('DELETE FROM account_session WHERE token_hash=%s', (token_digest(token),))

    @staticmethod
    def _consent_receipt(db, owner, choices, version):
        db.execute('INSERT INTO consent_event(account_id,choices,notice_version) VALUES (%s,%s,%s)',
                   (owner, Jsonb(choices.model_dump()), version))

    def consent(self, token, value):
        with self._connect() as db:
            owner = self._owner(db, token)
            row = db.execute('''UPDATE grower_account SET location_opt_in=%s,community_opt_in=%s,
                              impact_opt_in=%s,notice_version=%s WHERE id=%s RETURNING *''',
                             (value.choices.location_opt_in, value.choices.community_opt_in,
                              value.choices.impact_opt_in, value.notice_version, owner['id'])).fetchone()
            self._consent_receipt(db, owner['id'], value.choices, value.notice_version)
            if not value.choices.community_opt_in:
                # Withdrawn community participation is hidden immediately and the
                # district is removed from retained post metadata. Account deletion
                # remains the path for deleting the account's full record set.
                db.execute("UPDATE community_post SET status='hidden',district=NULL WHERE owner_id=%s", (owner['id'],))
                db.execute('DELETE FROM community_profile WHERE account_id=%s', (owner['id'],))
            return public_account(row)

    def change_password(self, token, value):
        with self._connect() as db:
            owner = self._owner(db, token)
            if not verify_password(value.current_password.get_secret_value(), owner['password_hash']):
                raise HTTPException(401, 'Password not accepted')
            db.execute('UPDATE grower_account SET password_hash=%s WHERE id=%s',
                       (hash_password(value.new_password.get_secret_value()), owner['id']))
            db.execute('DELETE FROM account_session WHERE account_id=%s', (owner['id'],))

    def delete_account(self, token, value):
        with self._connect() as db:
            owner = self._owner(db, token)
            if not verify_password(value.password.get_secret_value(), owner['password_hash']):
                raise HTTPException(401, 'Password not accepted')
            db.execute('DELETE FROM grower_account WHERE id=%s', (owner['id'],))

    @staticmethod
    def _passport(db, owner, passport_id):
        row = db.execute('SELECT * FROM plant_passport WHERE id=%s AND owner_id=%s FOR UPDATE',
                         (passport_id, owner)).fetchone()
        if row is None:
            raise HTTPException(404, 'Plant not found')
        return row

    @staticmethod
    def _species(db, species_id):
        if species_id is not None and not db.execute('''
            SELECT 1 FROM species WHERE id=%s AND is_active
              AND id NOT LIKE 'demo-%%' AND source_id<>'starter-samples'
        ''', (species_id,)).fetchone():
            raise HTTPException(422, 'Choose a non-demo species or use your own species name')

    def passports(self, token, after, limit):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            return db.execute('''SELECT id,nickname,species_name,species_id,planted_on,conditions FROM plant_passport
                                 WHERE owner_id=%s AND (%s::uuid IS NULL OR id>%s::uuid)
                                 ORDER BY id LIMIT %s''', (owner, after, after, limit)).fetchall()

    def passport(self, token, passport_id):
        with self._connect() as db:
            row = self._passport(db, self._owner(db, token)['id'], passport_id)
            return self._public_passport(row)

    @staticmethod
    def _public_passport(row):
        return {key: row[key] for key in PassportResponse.model_fields}

    def save_passport(self, token, value, passport_id=None):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            if passport_id is not None:
                self._passport(db, owner, passport_id)
                if db.execute('SELECT 1 FROM plant_care_event WHERE passport_id=%s AND occurred_on<%s LIMIT 1',
                              (passport_id, value.planted_on)).fetchone():
                    raise HTTPException(422, 'Planting date cannot be after existing care history')
                if db.execute('SELECT 1 FROM plant_photo WHERE passport_id=%s AND observed_on<%s LIMIT 1',
                              (passport_id, value.planted_on)).fetchone():
                    raise HTTPException(422, 'Planting date cannot be after existing photo history')
            self._species(db, value.species_id)
            values = (value.nickname, value.species_name, value.species_id,
                      value.planted_on, Jsonb(value.conditions.model_dump()))
            if passport_id is None:
                row = db.execute('''INSERT INTO plant_passport(nickname,species_name,species_id,planted_on,conditions,id,owner_id)
                                      VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *''', (*values, uuid4(), owner)).fetchone()
            else:
                row = db.execute('''UPDATE plant_passport SET nickname=%s,species_name=%s,species_id=%s,
                                 planted_on=%s,conditions=%s,updated_at=now() WHERE id=%s AND owner_id=%s RETURNING *''',
                              (*values, passport_id, owner)).fetchone()
            return self._public_passport(row)

    def delete_passport(self, token, passport_id):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._passport(db, owner, passport_id)
            db.execute('DELETE FROM plant_passport WHERE id=%s AND owner_id=%s', (passport_id, owner))

    def care(self, token, passport_id, after, limit):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._passport(db, owner, passport_id)
            return db.execute('''SELECT id,kind,occurred_on,note FROM plant_care_event
                                 WHERE passport_id=%s AND owner_id=%s AND (%s::uuid IS NULL OR
                                  (occurred_on,id)>(SELECT occurred_on,id FROM plant_care_event
                                   WHERE id=%s::uuid AND passport_id=%s AND owner_id=%s))
                                 ORDER BY occurred_on,id LIMIT %s''',
                              (passport_id, owner, after, after, passport_id, owner, limit)).fetchall()

    def add_care(self, token, passport_id, value):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            plant = self._passport(db, owner, passport_id)
            if value.request_id is not None:
                previous = db.execute('''SELECT * FROM plant_care_event
                    WHERE owner_id=%s AND request_id=%s''', (owner, value.request_id)).fetchone()
                if previous is not None:
                    if (str(previous['passport_id']) != str(passport_id) or
                        (previous['kind'], previous['occurred_on'], previous['note']) !=
                        (value.kind, value.occurred_on, value.note)):
                        raise HTTPException(409, 'Care operation conflicts with its original record')
                    return {key: previous[key] for key in CareResponse.model_fields}
            if value.occurred_on < plant['planted_on']:
                raise HTTPException(422, 'Care date cannot be before planting')
            row = db.execute('''INSERT INTO plant_care_event(id,passport_id,owner_id,kind,occurred_on,note,request_id)
                                  VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
                              (uuid4(), passport_id, owner, value.kind, value.occurred_on, value.note, value.request_id)).fetchone()
            return {key: row[key] for key in CareResponse.model_fields}


def get_account_repository():
    return AccountRepository()
