"""Typed contracts for the consented, moderated community surface."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from app.accounts import StrictModel

District = Literal['dhaka', 'chattogram', 'rajshahi', 'khulna', 'sylhet', 'rangpur', 'barishal', 'mymensingh']
CommunityTopic = Literal['milestone', 'care', 'question', 'general']
ReportReason = Literal['harassment', 'unsafe_advice', 'privacy', 'spam', 'other']


class CommunityProfileInput(StrictModel):
    district: District
    public_alias: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=40)]
    notice_version: Literal['community-2026-10-06']


class CommunityProfile(StrictModel):
    district: District
    public_alias: str
    notice_version: str


class CommunityPostInput(StrictModel):
    topic: CommunityTopic
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class CommunityPost(StrictModel):
    id: UUID
    author_alias: str
    topic: CommunityTopic
    body: str
    created_at: datetime
    status: Literal['pending', 'approved', 'rejected', 'hidden'] = 'approved'


class CommunityReportInput(StrictModel):
    reason: ReportReason
    details: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ''


class CommunityReportResponse(StrictModel):
    accepted: bool
    auto_hidden: bool


class ModerationInput(StrictModel):
    status: Literal['approved', 'rejected', 'hidden']


class LeaderboardEntry(StrictModel):
    public_alias: str
    score: float = Field(ge=0, le=100)
    current_streak_days: int = Field(ge=0)
    milestones_earned: int = Field(ge=0)
    plant_count_band: Literal['1', '2-5', '6+']


class NeighborhoodSummary(StrictModel):
    district: District
    available: bool
    participating_growers: int = Field(ge=0)
    minimum_growers: int = 5
    average_score: float | None = Field(default=None, ge=0, le=100)
    average_current_streak_days: float | None = Field(default=None, ge=0)
    milestones_3_months: int = Field(ge=0)
    milestones_6_months: int = Field(ge=0)
    milestones_12_months: int = Field(ge=0)
    message: str
