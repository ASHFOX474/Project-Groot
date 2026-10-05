from datetime import date, timedelta
from uuid import uuid4

from app.rewards import add_months, streaks, summarize


def test_month_math_clamps_end_of_month():
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)


def test_streak_allows_today_or_yesterday_and_tracks_best():
    today = date(2026, 10, 6)
    assert streaks({today - timedelta(days=2), today - timedelta(days=1), today}, today) == (3, 3)
    assert streaks({today - timedelta(days=3), today - timedelta(days=2)}, today) == (0, 2)


def test_summary_averages_per_plant_and_requires_recent_checkin():
    today = date(2026, 10, 6)
    plants = [
        {'id': uuid4(), 'nickname': 'A', 'planted_on': today - timedelta(days=100),
         'care_dates': {today, today - timedelta(days=1)}},
        {'id': uuid4(), 'nickname': 'B', 'planted_on': today - timedelta(days=100),
         'care_dates': set()},
    ]
    result = summarize(plants, today)
    assert result.plant_count == 2
    assert result.score == 13.0
    assert result.plants[0].milestones[0].status == 'earned'
    assert result.plants[1].milestones[0].status == 'awaiting_checkin'
    assert 'plant count adds no points' in result.score_method
