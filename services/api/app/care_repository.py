"""Private plan persistence with transactional owner checks and live evidence gates."""
import hashlib
import json
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from app.accounts import AccountRepository
from app.catalog_bundle import today_bd
from app.care_models import PlanRequest, PlanPreview, PlanVersion, PlanIssue, PLAN_NOTICE
from app.care_plans import build_plan, plan_fingerprint, stored_goal
from app.goal_models import GoalInput


class CarePlanRepository(AccountRepository):
    @staticmethod
    def _guidance(db, profile_id):
        today = today_bd()
        rows = db.execute('''SELECT g.*,
            (g.review_status='reviewed' AND g.reviewed_at<=%s AND g.valid_until>=%s
             AND e.id<>'starter-samples' AND e.id NOT LIKE 'demo-%%'
             AND e.review_status='reviewed' AND e.access_status='public'
             AND e.reuse_status IN ('open_license','permission_granted')
             AND e.checked_at<=%s AND e.valid_until>=%s
             AND e.license_name IS NOT NULL AND e.license_url IS NOT NULL) AS eligible,
            jsonb_build_object('key','care:'||g.id,'source_title',e.title,'source_url',e.source_url,
              'source_locator',g.source_locator,'interpretation_note',g.interpretation_note,
              'checked_at',e.checked_at,'valid_until',e.valid_until,'license_name',e.license_name,
              'license_url',e.license_url,'attribution',e.attribution) AS source
            FROM plant_care_guidance g JOIN catalog_source e ON e.id=g.source_id
            WHERE g.profile_id=%s ORDER BY g.id LIMIT 33''', (today, today, today, today, profile_id)).fetchall()
        if len(rows) > 32:
            raise RuntimeError('Care evidence exceeds reviewed profile bounds')
        return rows

    def _compute(self, db, value):
        try:
            candidates = self.recommendation_candidates_from(db, value.profile_id)
            return build_plan(value, candidates, self._guidance(db, value.profile_id))
        except (ValueError, KeyError, TypeError):
            raise RuntimeError('Reviewed care evidence unavailable') from None

    def preview(self, token, value):
        with self._connect() as db:
            self._owner(db, token)
            result = self._compute(db, value)
            self._owner(db, token)
            return result

    @staticmethod
    def _request_hash(value):
        payload = {'profile_id': value.profile_id, 'weeks': value.weeks,
                   'conditions': stored_goal(value.goal).model_dump(mode='json')}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    @staticmethod
    def _plan(db, owner, plan_id):
        row = db.execute('SELECT id FROM care_plan WHERE id=%s AND owner_id=%s FOR UPDATE', (plan_id, owner)).fetchone()
        if row is None:
            raise HTTPException(404, 'Plan not found')

    @staticmethod
    def _version(db, owner, plan_id, version=None):
        row = db.execute('''SELECT * FROM care_plan_version WHERE plan_id=%s AND owner_id=%s
                             AND (%s::integer IS NULL OR version=%s) ORDER BY version DESC LIMIT 1''',
                         (plan_id, owner, version, version)).fetchone()
        if row is None:
            raise HTTPException(404, 'Plan version not found')
        return row

    def _render(self, db, row):
        try:
            snapshot = PlanPreview.model_validate(row['snapshot'])
            conditions = GoalInput.model_validate(row['conditions'])
            request = PlanRequest(profile_id=row['profile_id'], weeks=snapshot.weeks, goal=conditions)
            current = self._compute(db, request)
            availability = 'current' if plan_fingerprint(request, current) == row['fingerprint'] else (
                'unavailable' if current.status == 'blocked' else 'stale')
            if availability != 'current':
                snapshot.instructions = []
                snapshot.status = 'blocked'
                snapshot.message = 'পুরোনো নির্দেশনা স্থগিত।' if snapshot.language == 'bn' else 'Historical instructions withheld.'
                snapshot.issues.append(PlanIssue(code='evidence_changed', message=(
                    'পুরোনো নির্দেশনা স্থগিত: উৎস বা পর্যালোচনা বদলেছে/মেয়াদ শেষ। নতুন পর্যালোচিত সংস্করণ দরকার।'
                    if snapshot.language == 'bn' else
                    'Historical instructions are withheld: evidence changed, expired or became unavailable. Generate a new reviewed version.')))
            return PlanVersion(plan_id=row['plan_id'], version=row['version'], created_at=row['created_at'],
                fingerprint=row['fingerprint'], availability=availability, conditions=conditions, plan=snapshot)
        except (ValueError, KeyError, TypeError):
            raise RuntimeError('Stored plan unavailable') from None

    @staticmethod
    def _append(db, owner, plan_id, number, value, preview):
        return db.execute('''INSERT INTO care_plan_version
            (plan_id,owner_id,version,profile_id,fingerprint,conditions,snapshot)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
            (plan_id, owner, number, value.profile_id, plan_fingerprint(value, preview),
             Jsonb(stored_goal(value.goal).model_dump(mode='json')), Jsonb(preview.model_dump(mode='json')))).fetchone()

    def save(self, token, value):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            digest = self._request_hash(value)
            prior = db.execute('SELECT id,request_hash FROM care_plan WHERE owner_id=%s AND request_id=%s',
                               (owner, value.request_id)).fetchone()
            if prior:
                if prior['request_hash'] != digest:
                    raise HTTPException(409, 'Request identity already used for different conditions')
                result = self._render(db, self._version(db, owner, prior['id'], 1))
            else:
                preview = self._compute(db, value)
                if preview.status == 'blocked':
                    raise HTTPException(409, 'No usable reviewed instructions; preview first')
                plan_id = uuid4()
                db.execute('''INSERT INTO care_plan(id,owner_id,request_id,request_hash,save_notice_version)
                              VALUES (%s,%s,%s,%s,%s)''', (plan_id, owner, value.request_id, digest, PLAN_NOTICE))
                row = self._append(db, owner, plan_id, 1, value, preview)
                result = self._render(db, row)
            self._owner(db, token)  # wall-clock expiry before any commit/response
            return result

    def revise(self, token, plan_id, value):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._plan(db, owner, plan_id)
            latest = self._version(db, owner, plan_id)
            preview = self._compute(db, value)
            if preview.status == 'blocked':
                raise HTTPException(409, 'No usable reviewed instructions; preview first')
            if preview.species_id != latest['snapshot']['species_id']:
                raise HTTPException(409, 'Different species requires a separate plan')
            same = plan_fingerprint(value, preview) == latest['fingerprint']
            # Permit a retry after a lost successful version response, not a stale edit.
            if value.expected_version != latest['version'] and not (same and value.expected_version == latest['version'] - 1):
                raise HTTPException(409, 'Plan changed. Reload before revising.')
            if not same:
                latest = self._append(db, owner, plan_id, latest['version'] + 1, value, preview)
            result = self._render(db, latest)
            self._owner(db, token)
            return result

    def plans(self, token, after, limit):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            result = db.execute('''SELECT p.id,v.version AS latest_version,
                v.snapshot->>'common_name_bn' AS common_name_bn,v.snapshot->>'common_name_en' AS common_name_en,
                v.snapshot->>'language' AS language,v.snapshot->>'status' AS status
                FROM care_plan p JOIN LATERAL (SELECT version,snapshot FROM care_plan_version
                     WHERE plan_id=p.id AND owner_id=p.owner_id ORDER BY version DESC LIMIT 1) v ON true
                WHERE p.owner_id=%s AND (%s::uuid IS NULL OR p.id>%s::uuid) ORDER BY p.id LIMIT %s''',
                (owner, after, after, limit)).fetchall()
            self._owner(db, token)
            return result

    def read(self, token, plan_id, version=None):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._plan(db, owner, plan_id)
            result = self._render(db, self._version(db, owner, plan_id, version))
            self._owner(db, token)
            return result

    def history(self, token, plan_id, before, limit):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._plan(db, owner, plan_id)
            result = db.execute('''SELECT version,created_at,snapshot->>'status' AS status FROM care_plan_version
                WHERE plan_id=%s AND owner_id=%s AND (%s::integer IS NULL OR version<%s)
                ORDER BY version DESC LIMIT %s''', (plan_id, owner, before, before, limit)).fetchall()
            self._owner(db, token)
            return result

    def delete(self, token, plan_id):
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            self._plan(db, owner, plan_id)
            db.execute('DELETE FROM care_plan WHERE id=%s AND owner_id=%s', (plan_id, owner))
            self._owner(db, token)


def get_care_repository():
    return CarePlanRepository()
