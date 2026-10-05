"""Owner-scoped rewards and moderated community persistence."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.accounts import AccountRepository
from app.catalog_bundle import today_bd
from app.community import (
    CommunityPostInput, CommunityProfileInput, CommunityReportInput,
    CommunityReportResponse, CommunityPost, CommunityProfile, LeaderboardEntry,
    ModerationInput, NeighborhoodSummary,
)
from app.rewards import RewardsSummary, summarize

DISTRICTS = {'dhaka', 'chattogram', 'rajshahi', 'khulna', 'sylhet', 'rangpur', 'barishal', 'mymensingh'}


class CommunityRepository(AccountRepository):
    def _owned_plants(self, db, owner_id):
        rows = db.execute('''
            SELECT p.id,p.nickname,p.planted_on,c.occurred_on
              FROM plant_passport p
              LEFT JOIN plant_care_event c ON c.passport_id=p.id AND c.owner_id=p.owner_id
             WHERE p.owner_id=%s
             ORDER BY p.id,c.occurred_on,c.id
        ''', (owner_id,)).fetchall()
        plants = {}
        for row in rows:
            plant = plants.setdefault(str(row['id']), {
                'id': row['id'], 'nickname': row['nickname'],
                'planted_on': row['planted_on'], 'care_dates': set(),
            })
            if row['occurred_on'] is not None:
                plant['care_dates'].add(row['occurred_on'])
        return list(plants.values())

    def rewards(self, token) -> RewardsSummary:
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            result = summarize(self._owned_plants(db, owner), today_bd())
            self._owner(db, token)
            return result

    def profile(self, token) -> CommunityProfile | None:
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            row = db.execute('SELECT district,public_alias,notice_version FROM community_profile WHERE account_id=%s',
                             (owner,)).fetchone()
            return CommunityProfile.model_validate(row) if row else None

    def save_profile(self, token, value: CommunityProfileInput) -> CommunityProfile:
        with self._connect() as db:
            owner = self._owner(db, token)
            if not owner['community_opt_in']:
                raise HTTPException(403, 'Enable community consent before creating a public profile')
            row = db.execute('''
                INSERT INTO community_profile(account_id,district,public_alias,notice_version)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT(account_id) DO UPDATE SET district=excluded.district,
                    public_alias=excluded.public_alias,notice_version=excluded.notice_version,updated_at=now()
                RETURNING district,public_alias,notice_version
            ''', (owner['id'], value.district, value.public_alias, value.notice_version)).fetchone()
            self._owner(db, token)
            return CommunityProfile.model_validate(row)

    def feed(self, token, after: UUID | None, limit: int) -> list[CommunityPost]:
        with self._connect() as db:
            self._owner(db, token)
            rows = db.execute('''
                SELECT p.id,cp.public_alias AS author_alias,p.topic,p.body,p.created_at,p.status
                  FROM community_post p JOIN community_profile cp ON cp.account_id=p.owner_id
                 WHERE p.status='approved'
                   AND (%s::uuid IS NULL OR (p.created_at,p.id) <
                        (SELECT created_at,id FROM community_post WHERE id=%s))
                 ORDER BY p.created_at DESC,p.id DESC LIMIT %s
            ''', (after, after, limit)).fetchall()
            return [CommunityPost.model_validate(row) for row in rows]

    def create_post(self, token, value: CommunityPostInput) -> CommunityPost:
        with self._connect() as db:
            owner = self._owner(db, token)
            if not owner['community_opt_in']:
                raise HTTPException(403, 'Enable community consent before posting')
            profile = db.execute('SELECT district,public_alias FROM community_profile WHERE account_id=%s',
                                 (owner['id'],)).fetchone()
            if profile is None:
                raise HTTPException(409, 'Create a district-level community profile first')
            row = db.execute('''
                INSERT INTO community_post(id,owner_id,district,topic,body,status)
                VALUES (%s,%s,%s,%s,%s,'pending')
                RETURNING id,topic,body,status,created_at
            ''', (uuid4(), owner['id'], profile['district'], value.topic, value.body)).fetchone()
            self._owner(db, token)
            return CommunityPost(id=row['id'], author_alias=profile['public_alias'], topic=row['topic'],
                                 body=row['body'], status=row['status'], created_at=row['created_at'])

    def delete_post(self, token, post_id: UUID) -> None:
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            row = db.execute('SELECT id FROM community_post WHERE id=%s AND owner_id=%s FOR UPDATE',
                             (post_id, owner)).fetchone()
            if row is None:
                raise HTTPException(404, 'Post not found')
            db.execute("UPDATE community_post SET status='hidden',district=NULL WHERE id=%s", (post_id,))

    def report(self, token, post_id: UUID, value: CommunityReportInput) -> CommunityReportResponse:
        with self._connect() as db:
            owner = self._owner(db, token)['id']
            post = db.execute('SELECT owner_id,status FROM community_post WHERE id=%s FOR UPDATE', (post_id,)).fetchone()
            if post is None or post['status'] in ('hidden', 'rejected'):
                raise HTTPException(404, 'Post not found')
            if post['owner_id'] == owner:
                raise HTTPException(409, 'Authors cannot report their own post')
            inserted = db.execute('''
                INSERT INTO community_report(post_id,reporter_id,reason,details)
                VALUES (%s,%s,%s,%s) ON CONFLICT(post_id,reporter_id) DO NOTHING RETURNING id
            ''', (post_id, owner, value.reason, value.details)).fetchone()
            count = db.execute('SELECT count(*) AS count FROM community_report WHERE post_id=%s', (post_id,)).fetchone()['count']
            auto_hidden = count >= 3 and post['status'] != 'hidden'
            if auto_hidden:
                db.execute("UPDATE community_post SET status='hidden',moderated_at=now() WHERE id=%s", (post_id,))
            self._owner(db, token)
            return CommunityReportResponse(accepted=inserted is not None, auto_hidden=auto_hidden)

    def _participants(self, db):
        rows = db.execute('''
            SELECT a.id,cp.public_alias,cp.district,p.id AS passport_id,p.nickname,p.planted_on,c.occurred_on
              FROM grower_account a JOIN community_profile cp ON cp.account_id=a.id
              LEFT JOIN plant_passport p ON p.owner_id=a.id
              LEFT JOIN plant_care_event c ON c.passport_id=p.id AND c.owner_id=p.owner_id
             WHERE a.community_opt_in
             ORDER BY a.id,p.id,c.occurred_on,c.id LIMIT 10000
        ''').fetchall()
        grouped = {}
        for row in rows:
            account = grouped.setdefault(row['id'], {
                'alias': row['public_alias'], 'district': row['district'], 'plants': {},
            })
            if row['passport_id'] is not None:
                plant = account['plants'].setdefault(row['passport_id'], {
                    'id': row['passport_id'], 'nickname': row['nickname'],
                    'planted_on': row['planted_on'], 'care_dates': set(),
                })
                if row['occurred_on'] is not None:
                    plant['care_dates'].add(row['occurred_on'])
        return grouped

    @staticmethod
    def _plant_band(count: int) -> str:
        return '1' if count == 1 else '2-5' if count <= 5 else '6+'

    def leaderboard(self, token, limit: int) -> list[LeaderboardEntry]:
        with self._connect() as db:
            self._owner(db, token)
            participants = self._participants(db)
            today = today_bd()
            entries = []
            for account in participants.values():
                result = summarize(list(account['plants'].values()), today)
                if result.plant_count:
                    entries.append(LeaderboardEntry(
                        public_alias=account['alias'], score=result.score,
                        current_streak_days=result.current_streak_days,
                        milestones_earned=sum(m.status == 'earned' for p in result.plants for m in p.milestones),
                        plant_count_band=self._plant_band(result.plant_count),
                    ))
            entries.sort(key=lambda item: (-item.score, -item.current_streak_days, item.public_alias))
            return entries[:limit]

    def neighborhood(self, token, district: str | None = None) -> NeighborhoodSummary:
        with self._connect() as db:
            owner = self._owner(db, token)
            profile = db.execute('SELECT district FROM community_profile WHERE account_id=%s', (owner['id'],)).fetchone()
            district = district or (profile['district'] if profile else None)
            if district not in DISTRICTS:
                raise HTTPException(409, 'Create a district-level community profile first')
            participants = self._participants(db)
            selected = [a for a in participants.values() if a['district'] == district and a['plants']]
            if len(selected) < 5:
                return NeighborhoodSummary(district=district, available=False, participating_growers=len(selected),
                    message='Neighborhood trends are shown only after at least five opted-in growers participate.')
            results = [summarize(list(a['plants'].values()), today_bd()) for a in selected]
            total = len(results)
            milestone_counts = {
                months: sum(m.status == 'earned' for result in results for plant in result.plants
                            for m in plant.milestones if m.months == months)
                for months in (3, 6, 12)
            }
            return NeighborhoodSummary(
                district=district, available=True, participating_growers=total,
                average_score=round(sum(r.score for r in results) / total, 1),
                average_current_streak_days=round(sum(r.current_streak_days for r in results) / total, 1),
                milestones_3_months=milestone_counts[3], milestones_6_months=milestone_counts[6],
                milestones_12_months=milestone_counts[12],
                message='Aggregate self-reported care trends from opted-in growers; no home locations or individual gardens are shown.',
            )

    def _moderator(self, db, token):
        owner = self._owner(db, token)
        if not owner['is_moderator']:
            raise HTTPException(403, 'Moderator access required')
        return owner

    def moderation_queue(self, token, limit: int) -> list[CommunityPost]:
        with self._connect() as db:
            self._moderator(db, token)
            rows = db.execute('''
                SELECT p.id,cp.public_alias AS author_alias,p.topic,p.body,p.created_at,p.status
                  FROM community_post p JOIN community_profile cp ON cp.account_id=p.owner_id
                 WHERE p.status='pending' ORDER BY p.created_at,p.id LIMIT %s
            ''', (limit,)).fetchall()
            return [CommunityPost.model_validate(row) for row in rows]

    def moderate(self, token, post_id: UUID, value: ModerationInput) -> CommunityPost:
        with self._connect() as db:
            moderator = self._moderator(db, token)
            row = db.execute('''
                SELECT p.id,cp.public_alias AS author_alias,p.topic,p.body,p.created_at,p.status
                  FROM community_post p JOIN community_profile cp ON cp.account_id=p.owner_id
                 WHERE p.id=%s FOR UPDATE
            ''', (post_id,)).fetchone()
            if row is None:
                raise HTTPException(404, 'Post not found')
            updated = db.execute('''
                UPDATE community_post SET status=%s,moderated_at=now(),moderated_by=%s
                 WHERE id=%s RETURNING id,topic,body,status,created_at
            ''', (value.status, moderator['id'], post_id)).fetchone()
            self._owner(db, token)
            return CommunityPost(id=updated['id'], author_alias=row['author_alias'], topic=updated['topic'],
                                 body=updated['body'], status=updated['status'], created_at=updated['created_at'])


def get_community_repository():
    return CommunityRepository()
