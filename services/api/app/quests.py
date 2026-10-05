"""Daily observations / weekly instruction reviews; never invent care frequency."""
from datetime import date, datetime, timedelta
import hashlib
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from app.accounts import StrictModel
from app.goal_models import GoalSource
from app.weather import BD, WeatherView, weather_status


class QuestCompletion(StrictModel):
    version: Annotated[int,Field(strict=True,ge=1)]
    key: Annotated[str,StringConstraints(pattern=r'^[a-z0-9:.-]{1,100}$')]
    completed: Annotated[bool,Field(strict=True)]


class WeatherPreference(StrictModel):
    enabled: Annotated[bool,Field(strict=True)]
    notice_version: Literal['weather-2026-10-05']


class Quest(StrictModel):
    key: str
    title: str
    cadence: Literal['daily','weekly','once']
    topic: str
    starts_on: date
    due_on: date
    instruction: str
    sources: list[GoalSource] = Field(default_factory=list)
    completed: bool = False
    adaptation: Literal['none','rain_check','heat_check'] = 'none'
    weather_note: str = ''


class QuestBoard(StrictModel):
    plan_id: UUID
    version: int
    today: date
    availability: str
    weather_enabled: bool
    weather: WeatherView
    quests: list[Quest]
    message: str
    reminder_count: int


def build_board(version, now: datetime, forecast, completions, weather_enabled, days=1,
                weather_reason=None):
    today=now.astimezone(BD).date()
    bn=version.plan.language=='bn'
    def t(b,e): return b if bn else e
    state = weather_reason or (weather_status(forecast,now) if weather_enabled else 'disabled')
    messages={
        'disabled':t('আবহাওয়া বন্ধ।','Weather is off.'),
        'unsupported':t('সমর্থিত জেলা বেছে নিন; জিপিএস সংগ্রহ হয় না।','Choose a supported district; no GPS is collected.'),
        'unavailable':t('আবহাওয়া পাওয়া যায়নি; অনুমান করে যত্ন বদলাবেন না।','Forecast unavailable. No weather adaptation.'),
        'stale':t('আবহাওয়া পুরোনো; যত্ন বদলানো হয়নি।','Forecast is stale. No weather adaptation.'),
        'fresh':t('জেলার রেফারেন্স পূর্বাভাস; আপনার মাটির অবস্থা নয়।','District reference forecast, not your soil conditions.'),
        'provider_disabled':t('সার্ভারে আবহাওয়া সেবা চালু হয়নি।','Weather provider is disabled by the operator.'),
    }
    view=WeatherView(status=state,district=forecast.district if forecast else None,
                     fetched_at=forecast.fetched_at if forecast else None,message=messages[state])
    quests=[]
    if version.availability=='current' and version.plan.status!='blocked':
        planting=version.conditions.planting_date
        end=planting+timedelta(days=version.plan.weeks*7)
        window_end=today+timedelta(days=days-1)
        for offset in range(days):
            day=today+timedelta(days=offset)
            if planting<day<=end:
                quests.append(Quest(key='observation:'+day.isoformat(),
                    title=t('গাছ পর্যবেক্ষণ করুন','Observe your plant'),cadence='daily',topic='monitoring',
                    starts_on=day,due_on=day,
                    instruction=t('পাতা ও মাটির অবস্থা দেখুন। এটি পর্যবেক্ষণ, পানি/সারের নির্দেশ নয়।',
                                  'Check visible plant and soil condition. Observation only; not a watering or feeding instruction.')))
        for step in version.plan.instructions:
            # Weekly reminders mean review the existing directive, not perform an action weekly.
            for week in range(step.week_start,step.week_end+1):
                start=planting+timedelta(days=0 if week==0 else (week-1)*7+1)
                due=planting+timedelta(days=week*7)
                if not start<=window_end or due<today or start<step.starts_on or due>step.ends_on:
                    continue
                digest=hashlib.sha256('|'.join(sorted(step.guidance_ids)).encode()).hexdigest()[:16]
                quests.append(Quest(key=f'review:{step.topic}:{digest}:{week}',
                    title=t('পর্যালোচিত নির্দেশনা দেখুন · '+step.topic,'Review reviewed guidance · '+step.topic),
                    cadence='once' if week==0 else 'weekly',topic=step.topic,
                    starts_on=start,due_on=due,instruction=step.instruction,sources=step.sources))
        for quest in quests:
            quest.completed=quest.key in completions
            if state!='fresh': continue
            day=next((d for d in forecast.days if d.day==max(today,quest.starts_on)),None)
            if day is None: continue
            if quest.topic=='watering' and day.rain_mm>=5 and day.rain_probability>=60:
                quest.adaptation='rain_check'
                quest.weather_note=t('বৃষ্টির সম্ভাবনা: মাটি ও আশ্রয় দেখুন। পূর্বাভাস দেখে স্বয়ংক্রিয়ভাবে পানি বন্ধ/বাড়াবেন না।',
                    'Rain possible: check soil moisture and shelter before watering. Do not automatically skip or increase water from a forecast.')
            elif quest.cadence=='daily' and day.max_temperature_c>=35:
                quest.adaptation='heat_check'
                quest.weather_note=t('গরমের সম্ভাবনা: গাছের চাপ ও মাটি আবার দেখুন। পানির মাত্রা বদলানো হয়নি।',
                    'Heat possible: recheck plant stress and soil condition. No water dose has been changed.')
    count=sum(not q.completed and q.starts_on<=today<=q.due_on for q in quests)
    message=t('নিজের দেওয়া সম্পন্ন তথ্য; যত্ন বা বেঁচে থাকার প্রমাণ নয়।',
             'Completion is self-reported, not verified care or survival.')
    if version.plan.status=='partial':
        message += t(' আংশিক পরিকল্পনা: অনুপস্থিত নির্দেশনা থেকে কাজ বানানো হয়নি। ঘাটতি দেখতে পরিকল্পনা খুলুন।',
                     ' Partial plan: missing guidance is not scheduled. Open the plan to review its gaps.')
    return QuestBoard(plan_id=version.plan_id,version=version.version,today=today,
        availability=version.availability,weather_enabled=weather_enabled,weather=view,quests=quests,
        reminder_count=count,message=message)
