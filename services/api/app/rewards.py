"""Pure calculations for transparent, self-reported care rewards."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.accounts import StrictModel


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def streaks(dates: set[date], today: date) -> tuple[int, int]:
    if not dates:
        return 0, 0
    ordered = sorted(dates)
    best = current = 1
    for previous, value in zip(ordered, ordered[1:]):
        if value == previous + timedelta(days=1):
            current += 1
        else:
            current = 1
        best = max(best, current)
    active_end = today if today in dates else today - timedelta(days=1)
    active = 0
    while active_end - timedelta(days=active) in dates:
        active += 1
    return active, best


class Milestone(StrictModel):
    months: Literal[3, 6, 12]
    target_on: date
    status: Literal['upcoming', 'earned', 'awaiting_checkin']
    points: int = Field(ge=0, le=25)
    note: str


class PlantReward(StrictModel):
    passport_id: UUID
    nickname: str
    planted_on: date
    current_streak_days: int = Field(ge=0)
    best_streak_days: int = Field(ge=0)
    milestones: list[Milestone]
    score: int = Field(ge=0, le=100)


class RewardsSummary(StrictModel):
    plant_count: int = Field(ge=0)
    care_days: int = Field(ge=0)
    current_streak_days: int = Field(ge=0)
    best_streak_days: int = Field(ge=0)
    score: float = Field(ge=0, le=100)
    score_method: str
    plants: list[PlantReward]


def plant_reward(passport_id, nickname: str, planted_on: date, dates: set[date], today: date) -> PlantReward:
    current, best = streaks(dates, today)
    recent = any(today - timedelta(days=30) <= value <= today for value in dates)
    milestones: list[Milestone] = []
    for months in (3, 6, 12):
        target = add_months(planted_on, months)
        if today < target:
            status = 'upcoming'
            points = 0
            note = f'{months}-month self-reported survival milestone is upcoming.'
        elif recent:
            status = 'earned'
            points = 25
            note = 'Recorded from the planting date and a care entry in the last 30 days; not independently verified.'
        else:
            status = 'awaiting_checkin'
            points = 0
            note = 'Plant age reached; add a recent care check-in to record this self-reported milestone.'
        milestones.append(Milestone(months=months, target_on=target, status=status,
                                     points=points, note=note))
    score = min(100, sum(item.points for item in milestones) + min(current, 30) * 25 // 30)
    return PlantReward(passport_id=passport_id, nickname=nickname, planted_on=planted_on,
                       current_streak_days=current, best_streak_days=best,
                       milestones=milestones, score=score)


def summarize(plants: list[dict], today: date) -> RewardsSummary:
    rewards: list[PlantReward] = []
    all_dates: set[date] = set()
    for plant in plants:
        dates = {row for row in plant['care_dates'] if plant['planted_on'] <= row <= today}
        all_dates.update(dates)
        rewards.append(plant_reward(plant['id'], plant['nickname'], plant['planted_on'], dates, today))
    current, best = streaks(all_dates, today)
    score = round(sum(item.score for item in rewards) / len(rewards), 1) if rewards else 0.0
    return RewardsSummary(
        plant_count=len(rewards), care_days=len(all_dates), current_streak_days=current,
        best_streak_days=best, score=score,
        score_method='Average of capped per-plant scores; plant count adds no points. Care and survival are self-reported.',
        plants=rewards,
    )
