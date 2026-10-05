"""Thin account routes. Ownership is checked inside each database transaction."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.accounts import (AccountDelete, AccountRepository, AccountResponse, CareInput, CareResponse,
                          ConsentInput, Credentials, PassportInput, PassportResponse, PasswordChange,
                          Registration, SessionResponse, get_account_repository)
from app.goal_models import GoalInput, GoalResult
from app.care_models import PlanRequest, SavePlanRequest, RevisePlanRequest, PlanPreview, PlanVersion, PlanSummary, VersionSummary
from app.care_repository import CarePlanRepository, get_care_repository
from app.quest_repository import QuestRepository, get_quest_repository
from app.quests import QuestBoard, QuestCompletion, WeatherPreference
from app.photos import PhotoConsent, PhotoConsentState, PhotoInput, PhotoSummary
from app.photo_repository import PhotoRepository, get_photo_repository
from app.community import (CommunityPost, CommunityPostInput, CommunityProfile,
                           CommunityProfileInput, CommunityReportInput, CommunityReportResponse,
                           LeaderboardEntry, ModerationInput, NeighborhoodSummary)
from app.community_repository import CommunityRepository, get_community_repository
from app.rewards import RewardsSummary

router = APIRouter(prefix='/v1', tags=['Private accounts and Plant Passports'])
Repository = Annotated[AccountRepository, Depends(get_account_repository)]
bearer = HTTPBearer(auto_error=False)


def session_token(value: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if value is None or len(value.credentials) != 43 or not all(c.isascii() and (c.isalnum() or c in '_-') for c in value.credentials):
        raise HTTPException(401, 'Sign in again', headers={'WWW-Authenticate': 'Bearer'})
    return value.credentials


Token = Annotated[str, Depends(session_token)]
CareRepository = Annotated[CarePlanRepository, Depends(get_care_repository)]
QuestRepo = Annotated[QuestRepository, Depends(get_quest_repository)]
PhotoRepo = Annotated[PhotoRepository, Depends(get_photo_repository)]
CommunityRepo = Annotated[CommunityRepository, Depends(get_community_repository)]


def private_limit(request: Request, repo: Repository):
    repo.throttle('private-ip', request.client.host if request.client else 'unknown', 120, 60)


def auth_limit(request, repo, handle, scope):
    ip = request.client.host if request.client else 'unknown'
    repo.throttle(scope + '-ip', ip, 10 if scope == 'register' else 30)
    repo.throttle(scope + '-handle', handle, 10)


@router.post('/accounts/register', response_model=SessionResponse, status_code=201)
def register(value: Registration, request: Request, repo: Repository):
    auth_limit(request, repo, value.handle, 'register')
    return repo.register(value)


@router.post('/accounts/login', response_model=SessionResponse)
def login(value: Credentials, request: Request, repo: Repository):
    auth_limit(request, repo, value.handle, 'login')
    return repo.login(value)


private = APIRouter(dependencies=[Depends(private_limit)])


@private.post('/goals/recommendations', response_model=GoalResult)
def recommendations(value: GoalInput, token: Token, repo: Repository):
    try:
        return repo.recommend_goal(token, value)
    except RuntimeError:
        raise HTTPException(503, 'Reviewed catalog unavailable') from None


@private.get('/accounts/me', response_model=AccountResponse)
def me(token: Token, repo: Repository):
    return repo.me(token)


@private.put('/accounts/consent', response_model=AccountResponse)
def consent(value: ConsentInput, token: Token, repo: Repository):
    return repo.consent(token, value)


@private.post('/accounts/logout', status_code=204)
def logout(token: Token, repo: Repository):
    repo.logout(token)
    return Response(status_code=204)


@private.post('/accounts/password', status_code=204)
def password(value: PasswordChange, token: Token, request: Request, repo: Repository):
    repo.throttle('password-ip', request.client.host if request.client else 'unknown', 10)
    repo.change_password(token, value)
    return Response(status_code=204)


@private.post('/accounts/delete', status_code=204)
def delete_account(value: AccountDelete, token: Token, request: Request, repo: Repository):
    repo.throttle('password-ip', request.client.host if request.client else 'unknown', 10)
    repo.delete_account(token, value)
    return Response(status_code=204)


@private.get('/passports', response_model=list[PassportResponse])
def passports(token: Token, repo: Repository, after: UUID | None = None,
              limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return repo.passports(token, after, limit)


@private.post('/passports', response_model=PassportResponse, status_code=201)
def create_passport(value: PassportInput, token: Token, repo: Repository):
    return repo.save_passport(token, value)


@private.get('/passports/{passport_id}', response_model=PassportResponse)
def passport(passport_id: UUID, token: Token, repo: Repository):
    return repo.passport(token, passport_id)


@private.put('/passports/{passport_id}', response_model=PassportResponse)
def update_passport(passport_id: UUID, value: PassportInput, token: Token, repo: Repository):
    return repo.save_passport(token, value, passport_id)


@private.delete('/passports/{passport_id}', status_code=204)
def delete_passport(passport_id: UUID, token: Token, repo: Repository):
    repo.delete_passport(token, passport_id)
    return Response(status_code=204)


@private.get('/passports/{passport_id}/care', response_model=list[CareResponse])
def care(passport_id: UUID, token: Token, repo: Repository, after: UUID | None = None,
         limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return repo.care(token, passport_id, after, limit)


@private.post('/passports/{passport_id}/care', response_model=CareResponse, status_code=201)
def add_care(passport_id: UUID, value: CareInput, token: Token, repo: Repository):
    return repo.add_care(token, passport_id, value)


def care_result(operation):
    try:
        return operation()
    except RuntimeError:
        raise HTTPException(503, 'Reviewed care service unavailable') from None


@private.post('/plans/preview', response_model=PlanPreview)
def preview_plan(value: PlanRequest, token: Token, repo: CareRepository):
    return care_result(lambda: repo.preview(token, value))


@private.post('/plans', response_model=PlanVersion, status_code=201)
def save_plan(value: SavePlanRequest, token: Token, repo: CareRepository):
    return care_result(lambda: repo.save(token, value))


@private.get('/plans', response_model=list[PlanSummary])
def plans(token: Token, repo: CareRepository, after: UUID | None = None,
          limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return care_result(lambda: repo.plans(token, after, limit))


@private.get('/plans/{plan_id}/versions', response_model=list[VersionSummary])
def plan_versions(plan_id: UUID, token: Token, repo: CareRepository,
                  before: Annotated[int | None, Query(ge=1)] = None,
                  limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return care_result(lambda: repo.history(token, plan_id, before, limit))


@private.get('/plans/{plan_id}/versions/{number}', response_model=PlanVersion)
def plan_version(plan_id: UUID, number: Annotated[int, Path(ge=1)], token: Token, repo: CareRepository):
    return care_result(lambda: repo.read(token, plan_id, number))


@private.post('/plans/{plan_id}/versions', response_model=PlanVersion)
def revise_plan(plan_id: UUID, value: RevisePlanRequest, token: Token, repo: CareRepository):
    return care_result(lambda: repo.revise(token, plan_id, value))


@private.get('/plans/{plan_id}', response_model=PlanVersion)
def plan(plan_id: UUID, token: Token, repo: CareRepository):
    return care_result(lambda: repo.read(token, plan_id))


@private.delete('/plans/{plan_id}', status_code=204)
def delete_plan(plan_id: UUID, token: Token, repo: CareRepository):
    care_result(lambda: repo.delete(token, plan_id))
    return Response(status_code=204)


@private.get('/plans/{plan_id}/quests', response_model=QuestBoard)
def quests(plan_id: UUID, token: Token, repo: QuestRepo,
           days: Annotated[int,Query(ge=1,le=7)] = 1):
    return care_result(lambda: repo.board(token,plan_id,days))


@private.post('/plans/{plan_id}/quests/completion', response_model=QuestBoard)
def complete_quest(plan_id: UUID, value: QuestCompletion, token: Token, repo: QuestRepo):
    return care_result(lambda: repo.complete(token,plan_id,value))


@private.put('/plans/{plan_id}/quests/weather', response_model=dict)
def quest_weather(plan_id: UUID, value: WeatherPreference, token: Token, repo: QuestRepo):
    return care_result(lambda: repo.preference(token,plan_id,value))


@private.get('/passports/{passport_id}/photo-consent', response_model=PhotoConsentState)
def photo_consent(passport_id: UUID, token: Token, repo: PhotoRepo):
    return repo.consent(token, passport_id)


@private.put('/passports/{passport_id}/photo-consent', response_model=PhotoConsentState)
def set_photo_consent(passport_id: UUID, value: PhotoConsent, token: Token, repo: PhotoRepo):
    return repo.consent(token, passport_id, value)


@private.get('/passports/{passport_id}/photos', response_model=list[PhotoSummary])
def photos(passport_id: UUID, token: Token, repo: PhotoRepo, after: UUID | None = None,
           limit: Annotated[int, Query(ge=1, le=20)] = 20):
    return repo.list(token, passport_id, after, limit)


@private.post('/passports/{passport_id}/photos', response_model=PhotoSummary, status_code=201)
def upload_photo(passport_id: UUID, value: PhotoInput, token: Token, repo: PhotoRepo):
    owner = repo.me(token)['id']
    repo.throttle('photo-owner', str(owner), 10, 60)
    return repo.upload(token, passport_id, value)


@private.get('/passports/{passport_id}/photos/{photo_id}/image')
def photo_image(passport_id: UUID, photo_id: UUID, token: Token, repo: PhotoRepo):
    return Response(repo.photo(token, passport_id, photo_id), media_type='image/jpeg')


@private.delete('/passports/{passport_id}/photos/{photo_id}', status_code=204)
def delete_photo(passport_id: UUID, photo_id: UUID, token: Token, repo: PhotoRepo):
    repo.photo(token, passport_id, photo_id, delete=True)
    return Response(status_code=204)


@private.get('/rewards', response_model=RewardsSummary)
def rewards(token: Token, repo: CommunityRepo):
    return repo.rewards(token)


@private.get('/community/profile', response_model=CommunityProfile | None)
def community_profile(token: Token, repo: CommunityRepo):
    return repo.profile(token)


@private.put('/community/profile', response_model=CommunityProfile)
def save_community_profile(value: CommunityProfileInput, token: Token, repo: CommunityRepo):
    return repo.save_profile(token, value)


@private.get('/community/feed', response_model=list[CommunityPost])
def community_feed(token: Token, repo: CommunityRepo, after: UUID | None = None,
                   limit: Annotated[int, Query(ge=1, le=50)] = 20):
    return repo.feed(token, after, limit)


@private.post('/community/posts', response_model=CommunityPost, status_code=201)
def create_community_post(value: CommunityPostInput, token: Token, repo: CommunityRepo):
    return repo.create_post(token, value)


@private.delete('/community/posts/{post_id}', status_code=204)
def delete_community_post(post_id: UUID, token: Token, repo: CommunityRepo):
    repo.delete_post(token, post_id)
    return Response(status_code=204)


@private.post('/community/posts/{post_id}/report', response_model=CommunityReportResponse)
def report_community_post(post_id: UUID, value: CommunityReportInput, token: Token, repo: CommunityRepo):
    return repo.report(token, post_id, value)


@private.get('/community/leaderboard', response_model=list[LeaderboardEntry])
def community_leaderboard(token: Token, repo: CommunityRepo,
                          limit: Annotated[int, Query(ge=1, le=20)] = 10):
    return repo.leaderboard(token, limit)


@private.get('/community/neighborhood', response_model=NeighborhoodSummary)
def community_neighborhood(token: Token, repo: CommunityRepo):
    return repo.neighborhood(token)


@private.get('/community/moderation/queue', response_model=list[CommunityPost])
def community_moderation_queue(token: Token, repo: CommunityRepo,
                               limit: Annotated[int, Query(ge=1, le=100)] = 50):
    return repo.moderation_queue(token, limit)


@private.post('/community/moderation/{post_id}', response_model=CommunityPost)
def moderate_community_post(post_id: UUID, value: ModerationInput, token: Token, repo: CommunityRepo):
    return repo.moderate(token, post_id, value)


router.include_router(private)
