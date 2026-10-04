"""Authoritative care-plan HTTP contract; no client-authored plan snapshots."""
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.accounts import StrictModel
from app.catalog_bundle import CareGuidance, Identifier
from app.goal_models import GoalInput, GoalSource

PLAN_NOTICE = 'care-plan-2026-10-04'
Topic = Literal['soil_preparation', 'watering', 'nutrition', 'monitoring']


class PlanRequest(StrictModel):
    profile_id: Identifier
    goal: GoalInput
    weeks: Annotated[int, Field(strict=True, ge=1, le=12)] = 4


class SavePlanRequest(PlanRequest):
    request_id: UUID
    save_notice_version: Literal['care-plan-2026-10-04']


class RevisePlanRequest(PlanRequest):
    expected_version: Annotated[int, Field(strict=True, ge=1)]
    save_notice_version: Literal['care-plan-2026-10-04']


class PlanIssue(StrictModel):
    code: Literal['unsupported_conditions', 'conditions_uncertain', 'missing_guidance', 'conflicting_guidance', 'evidence_changed']
    message: str
    topic: Topic | None = None
    weeks: list[int] = Field(default_factory=list)
    guidance_ids: list[str] = Field(default_factory=list)
    sources: list[GoalSource] = Field(default_factory=list)


class PlanInstruction(StrictModel):
    guidance_ids: list[str]
    topic: Topic
    week_start: int
    week_end: int
    starts_on: date
    ends_on: date
    instruction: str
    reviewed_by: str
    reviewed_at: date
    valid_until: date
    sources: list[GoalSource]


class PlanPreview(StrictModel):
    profile_id: str
    language: Literal['bn', 'en']
    weeks: int
    status: Literal['ready', 'partial', 'blocked']
    message: str
    common_name_bn: str = ''
    common_name_en: str = ''
    species_id: str = ''
    profile_reviewed_at: date | None = None
    valid_until: date | None = None
    generator_version: Literal['reviewed-care-v1'] = 'reviewed-care-v1'
    evidence_fingerprint: str = ''
    disclaimer: str
    suitability_reasons: list[str] = Field(default_factory=list)
    condition_sources: list[GoalSource] = Field(default_factory=list)
    instructions: list[PlanInstruction] = Field(default_factory=list)
    issues: list[PlanIssue] = Field(default_factory=list)


class PlanVersion(StrictModel):
    plan_id: UUID
    version: int
    created_at: datetime
    fingerprint: str
    availability: Literal['current', 'stale', 'unavailable']
    conditions: GoalInput
    plan: PlanPreview


class PlanSummary(StrictModel):
    id: UUID
    latest_version: int
    common_name_bn: str
    common_name_en: str
    language: str
    status: str


class VersionSummary(StrictModel):
    version: int
    created_at: datetime
    status: str
