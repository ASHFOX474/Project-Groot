"""Strict, offline format for human-reviewed catalog imports (no web fetching)."""
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


def non_demo_id(value):
    if value.startswith('demo-') or value == 'starter-samples':
        raise ValueError('Demo identities cannot enter a reviewed import')
    return value


Identifier = Annotated[str, StringConstraints(pattern=r'^[a-z][a-z0-9-]{1,79}$'), AfterValidator(non_demo_id)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


def today_bd():
    return datetime.now(timezone(timedelta(hours=6))).date()


def public_url(value):
    if value is None:
        return value
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use a credential-free HTTPS reference URL')
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Source(StrictModel):
    id: Identifier
    title: Text
    publisher: Text
    source_url: Text
    checked_at: date
    review_status: Literal['reviewed']
    access_status: Literal['public', 'login_required', 'unavailable', 'unverified']
    reuse_status: Literal['open_license', 'permission_granted', 'permission_pending', 'restricted']
    license_name: Text | None = None
    license_url: Text | None = None
    rights_note: Text
    attribution: Text
    reviewed_by: Text
    valid_until: date

    _urls = field_validator('source_url', 'license_url')(public_url)

    @model_validator(mode='after')
    def review_dates_and_rights(self):
        if self.checked_at > today_bd() or self.valid_until <= self.checked_at:
            raise ValueError('Source review dates must be ordered and not in the future')
        if self.reuse_status in ('open_license', 'permission_granted') and not (self.license_name and self.license_url):
            raise ValueError('Cleared reuse needs an artifact-specific license/permission reference')
        return self


class Requirement(StrictModel):
    key: Literal['soil_ph', 'soil_texture', 'drainage', 'sunlight', 'spacing_cm', 'temperature_c', 'sowing_windows']
    value: Any
    source_id: Identifier
    source_locator: Text
    interpretation_note: Text

    @model_validator(mode='after')
    def typed_value(self):
        value = self.value
        if self.key in ('soil_ph', 'temperature_c', 'spacing_cm'):
            keys = ('row', 'plant') if self.key == 'spacing_cm' else ('min', 'max')
            if not isinstance(value, dict) or set(value) != set(keys):
                raise ValueError('Numeric requirements need exact named bounds/units')
            if any(type(v) not in (float, int) or not math.isfinite(v) for v in value.values()):
                raise ValueError('Requirement numbers must be finite, not booleans')
            low, high = (0, 14) if self.key == 'soil_ph' else ((-20, 60) if self.key == 'temperature_c' else (0.1, 10000))
            if any(not low <= v <= high for v in value.values()):
                raise ValueError('Requirement number outside supported bounds')
            if self.key != 'spacing_cm' and value['min'] > value['max']:
                raise ValueError('Minimum cannot exceed maximum')
        elif self.key == 'soil_texture':
            allowed = {'sand', 'sandy_loam', 'loam', 'clay_loam', 'clay'}
            if not isinstance(value, list) or not value or any(not isinstance(v, str) or v not in allowed for v in value) or len(set(value)) != len(value):
                raise ValueError('Use unique supported soil texture codes')
        elif self.key in ('drainage', 'sunlight'):
            allowed = {'well_drained', 'moist_not_waterlogged'} if self.key == 'drainage' else {'full_sun', 'partial_shade', 'shade'}
            if not isinstance(value, str) or value not in allowed:
                raise ValueError('Use a supported requirement code')
        else:
            if not isinstance(value, list) or not 1 <= len(value) <= 4:
                raise ValueError('Use 1–4 explicit sowing windows')
            for window in value:
                if not isinstance(window, dict) or set(window) != {'start_month', 'start_day', 'end_month', 'end_day'}:
                    raise ValueError('Sowing windows require month/day endpoints')
                if any(type(v) != int for v in window.values()):
                    raise ValueError('Sowing endpoints must be integers')
                date(2000, window['start_month'], window['start_day'])
                date(2000, window['end_month'], window['end_day'])
        return self


class CareGuidance(StrictModel):
    """Human-reviewed, source-authored text/timing, never generated from thresholds."""
    id: Identifier
    topic: Literal['soil_preparation', 'watering', 'nutrition', 'monitoring']
    week_start: int = Field(strict=True, ge=0, le=12)
    week_end: int = Field(strict=True, ge=0, le=12)
    instruction_bn: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)]
    instruction_en: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)]
    source_id: Identifier
    source_locator: Text
    interpretation_note: Text
    review_status: Literal['draft', 'reviewed'] = 'draft'
    reviewed_by: Text | None = None
    reviewed_at: date | None = None
    valid_until: date | None = None

    @field_validator('*')
    @classmethod
    def safe_text(cls, value):
        if isinstance(value, str):
            value.encode('utf-8')
            if '\x00' in value:
                raise ValueError('Null characters are not accepted')
        return value

    @model_validator(mode='after')
    def reviewed_timing(self):
        if self.week_end < self.week_start:
            raise ValueError('Care weeks must be ordered')
        if self.topic == 'soil_preparation' and (self.week_start != 0 or self.week_end != 0):
            raise ValueError('Preparation guidance must cover planting day only')
        if self.topic != 'soil_preparation' and self.week_start == 0:
            raise ValueError('Follow-up guidance starts at week 1')
        if self.review_status == 'reviewed' and not (self.reviewed_by and self.reviewed_at and self.valid_until):
            raise ValueError('Reviewed care needs explicit reviewer and validity')
        if self.reviewed_at and self.reviewed_at > today_bd():
            raise ValueError('Care review cannot be in the future')
        if self.valid_until and (not self.reviewed_at or self.valid_until <= self.reviewed_at):
            raise ValueError('Care expiry must follow review date')
        return self


class Profile(StrictModel):
    id: Identifier
    country_code: Literal['BD']
    locality: Text
    growing_context: Literal['open_ground', 'container', 'forestry']
    variety: Text
    review_status: Literal['draft', 'reviewed']
    reviewed_by: Text | None = None
    reviewed_at: date | None = None
    valid_until: date | None = None
    limitations: Text
    requirements: list[Requirement] = Field(min_length=1, max_length=16)
    care_guidance: list[CareGuidance] = Field(default_factory=list, max_length=32)

    @model_validator(mode='after')
    def review_and_keys(self):
        if len({r.key for r in self.requirements}) != len(self.requirements):
            raise ValueError('Duplicate requirement key')
        if self.review_status == 'reviewed' and not (self.reviewed_by and self.reviewed_at and self.valid_until):
            raise ValueError('Reviewed profile needs a reviewer and review/expiry dates')
        if self.reviewed_at and self.reviewed_at > today_bd():
            raise ValueError('Profile review cannot be in the future')
        if self.valid_until and (not self.reviewed_at or self.valid_until <= self.reviewed_at):
            raise ValueError('Profile expiry must follow review date')
        return self


class Plant(StrictModel):
    id: Identifier
    common_name_en: Text
    common_name_bn: Text
    scientific_name: Text
    category: Literal['crop', 'tree']
    source_id: Identifier
    profiles: list[Profile] = Field(min_length=1, max_length=10)


class CatalogBundle(StrictModel):
    schema_version: Literal[1]
    bundle_id: Identifier
    sources: list[Source] = Field(min_length=1, max_length=100)
    plants: list[Plant] = Field(min_length=1, max_length=200)

    @model_validator(mode='after')
    def identities_and_references(self):
        ids = [s.id for s in self.sources]
        plant_ids = [p.id for p in self.plants]
        profile_ids = [p.id for plant in self.plants for p in plant.profiles]
        care_ids = [g.id for plant in self.plants for p in plant.profiles for g in p.care_guidance]
        for values in (ids, plant_ids, profile_ids, care_ids):
            if len(set(values)) != len(values):
                raise ValueError('Duplicate source/plant/profile identity')
        for plant in self.plants:
            references = [plant.source_id] + [r.source_id for p in plant.profiles for r in p.requirements]
            references += [g.source_id for p in plant.profiles for g in p.care_guidance]
            if any(ref not in ids for ref in references):
                raise ValueError('Missing referenced source')
        return self


def read_bundle(path):
    with Path(path).open('rb') as handle:
        raw = handle.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('Catalog bundle exceeds 2 MiB')

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    return CatalogBundle.model_validate(json.loads(raw.decode('utf-8'), object_pairs_hook=unique_keys))
