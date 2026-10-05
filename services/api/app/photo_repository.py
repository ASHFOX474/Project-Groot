"""Private photo bytes commit/delete with metadata in one owner transaction."""
import hashlib
import json
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from app.accounts import AccountRepository
from app.photos import PHOTO_NOTICE, PhotoConsentState, PhotoSummary, sanitize_image, health_assistance


class PhotoRepository(AccountRepository):
    @staticmethod
    def _preference(db, owner, passport):
        row = db.execute('SELECT * FROM photo_consent WHERE owner_id=%s AND passport_id=%s',
                         (owner, passport)).fetchone()
        return row or {'storage': False, 'health': False, 'generation': 0}

    def consent(self, token, passport, value=None):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._passport(db, owner, passport)
            if value is None:
                preference = self._preference(db, owner, passport)
                return PhotoConsentState(**{k: preference[k] for k in ('storage', 'health', 'generation')}, notice_version=PHOTO_NOTICE)
            db.execute('''INSERT INTO photo_consent(passport_id,owner_id,storage,health,notice_version)
                VALUES(%s,%s,%s,%s,%s) ON CONFLICT(passport_id) DO UPDATE
                SET storage=excluded.storage,health=excluded.health,notice_version=excluded.notice_version,
                generation=photo_consent.generation+1,updated_at=now()''',
                (passport, owner, value.storage, value.health, value.notice_version))
            db.execute('''INSERT INTO photo_consent_event(passport_id,owner_id,storage,health,notice_version)
                VALUES(%s,%s,%s,%s,%s)''', (passport, owner, value.storage, value.health, value.notice_version))
            if not value.storage:
                db.execute('DELETE FROM plant_photo WHERE owner_id=%s AND passport_id=%s', (owner, passport))
            elif not value.health:
                db.execute("UPDATE plant_photo SET assistance=NULL,symptoms='[]'::jsonb WHERE owner_id=%s AND passport_id=%s", (owner, passport))
            self._owner(db, token)
            return PhotoConsentState(**value.model_dump(), generation=self._preference(db, owner, passport)['generation'])

    def upload(self, token, passport, value):
        # Authenticate/consent before decoding. Recheck after CPU work, not under locks.
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._passport(db, owner, passport)
            preference = self._preference(db, owner, passport)
            if not preference['storage']:
                raise HTTPException(403, 'Enable private photo storage first')
            if value.consent_generation != preference['generation']:
                raise HTTPException(409, 'Photo consent/timeline changed. Refresh before a new operation.')
            if value.symptoms and not preference['health']:
                raise HTTPException(403, 'Enable health assistance before submitting symptoms')
            generation = preference['generation']
        jpeg, image = sanitize_image(value)
        assistance = health_assistance(image, value.symptoms) if preference['health'] else None
        fingerprint = hashlib.sha256(jpeg + json.dumps([str(passport), str(value.observed_on),
            value.caption, sorted(value.symptoms)], ensure_ascii=False).encode()).hexdigest()
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            plant = self._passport(db, owner, passport)
            current = self._preference(db, owner, passport)
            if current['generation'] != generation or not current['storage']:
                raise HTTPException(409, 'Photo consent changed. Refresh before uploading.')
            previous = db.execute('SELECT * FROM plant_photo WHERE owner_id=%s AND request_id=%s',
                                  (owner, value.request_id)).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise HTTPException(409, 'Photo operation conflicts with its original record')
                return self._summary(previous)
            if value.observed_on < plant['planted_on']:
                raise HTTPException(422, 'Photo date cannot be before planting')
            counts = db.execute('''SELECT count(*) AS total,count(*) FILTER(WHERE passport_id=%s) AS plant
                FROM plant_photo WHERE owner_id=%s''', (passport, owner)).fetchone()
            if counts['total'] >= 100 or counts['plant'] >= 50:
                raise HTTPException(409, 'Photo limit reached. Explicitly delete old photos first.')
            row = db.execute('''INSERT INTO plant_photo(id,passport_id,owner_id,request_id,fingerprint,
                observed_on,caption,symptoms,jpeg,width,height,assistance)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
                (uuid4(), passport, owner, value.request_id, fingerprint, value.observed_on,
                 value.caption, Jsonb(value.symptoms), jpeg, image.width, image.height,
                 Jsonb(assistance) if assistance else None)).fetchone()
            self._owner(db, token)
            return self._summary(row)

    @staticmethod
    def _summary(row):
        return {k: row[k] for k in PhotoSummary.model_fields}

    def list(self, token, passport, after=None, limit=20):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._passport(db, owner, passport)
            rows = db.execute('''SELECT id,observed_on,uploaded_at,caption,symptoms,width,height,assistance
                FROM plant_photo WHERE owner_id=%s AND passport_id=%s AND (%s::uuid IS NULL OR
                  (observed_on,id)<(SELECT observed_on,id FROM plant_photo
                    WHERE owner_id=%s AND passport_id=%s AND id=%s))
                ORDER BY observed_on DESC,id DESC LIMIT %s''',
                (owner, passport, after, owner, passport, after, limit)).fetchall()
            self._owner(db, token)
            return rows

    def photo(self, token, passport, photo_id, delete=False):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._passport(db, owner, passport)
            row = db.execute('SELECT jpeg FROM plant_photo WHERE owner_id=%s AND passport_id=%s AND id=%s',
                             (owner, passport, photo_id)).fetchone()
            if row is None:
                raise HTTPException(404, 'Photo not found')
            if delete:
                db.execute('DELETE FROM plant_photo WHERE owner_id=%s AND passport_id=%s AND id=%s',
                           (owner, passport, photo_id))
                # Invalidate all older upload payloads, so a lost response retry
                # cannot recreate a photo deleted here or by another device.
                db.execute('UPDATE photo_consent SET generation=generation+1,updated_at=now() WHERE owner_id=%s AND passport_id=%s', (owner, passport))
            self._owner(db, token)
            return bytes(row['jpeg'])


def get_photo_repository():
    return PhotoRepository()
