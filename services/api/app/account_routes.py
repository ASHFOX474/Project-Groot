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

router = APIRouter(prefix='/v1', tags=['Private accounts and Plant Passports'])
Repository = Annotated[AccountRepository, Depends(get_account_repository)]
bearer = HTTPBearer(auto_error=False)


def session_token(value: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if value is None or len(value.credentials) != 43 or not all(c.isascii() and (c.isalnum() or c in '_-') for c in value.credentials):
        raise HTTPException(401, 'Sign in again', headers={'WWW-Authenticate': 'Bearer'})
    return value.credentials


Token = Annotated[str, Depends(session_token)]
CareRepository = Annotated[CarePlanRepository, Depends(get_care_repository)]


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


router.include_router(private)
