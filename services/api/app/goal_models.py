"""Authoritative goal HTTP contract; goals are transient, never stored here."""
from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from app.accounts import StrictModel
from app.catalog_bundle import public_url

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class GoalLocation(StrictModel):
    precision: Literal['none', 'country', 'district'] = 'none'
    country_code: Annotated[str, StringConstraints(pattern=r'^[A-Z]{2}$')] | None = None
    district: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] | None = None

    @model_validator(mode='after')
    def chosen_precision(self):
        if self.precision == 'none' and (self.country_code is not None or self.district is not None):
            raise ValueError('No location means no country or district')
        if self.precision != 'none' and self.country_code is None:
            raise ValueError('Selected location needs a country')
        if (self.precision == 'district') != (self.district is not None):
            raise ValueError('District must be supplied only at district precision')
        return self


class GoalSoil(StrictModel):
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ''
    ph: Annotated[Number, Field(ge=0, le=14)] | None = None
    texture: Literal['sand', 'sandy_loam', 'loam', 'clay_loam', 'clay', 'unknown'] = 'unknown'
    drainage: Literal['well_drained', 'moist_not_waterlogged', 'waterlogged', 'unknown'] = 'unknown'


class GoalInput(StrictModel):
    language: Literal['bn', 'en'] = 'bn'
    goal: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    category: Literal['crop', 'tree', 'any'] = 'any'
    location: GoalLocation = Field(default_factory=GoalLocation)
    growing_context: Literal['container', 'open_ground', 'forestry']
    area_m2: Annotated[Number, Field(gt=0, le=100000)] | None = None
    sunlight: Literal['full_sun', 'partial_shade', 'shade', 'unknown'] = 'unknown'
    soil: GoalSoil = Field(default_factory=GoalSoil)
    planting_date: date
    temperature_c: Annotated[Number, Field(ge=-20, le=60)] | None = None

    @field_validator('planting_date')
    @classmethod
    def bounded_date(cls, value):
        if not 1900 <= value.year <= 2100:
            raise ValueError('Use a date from 1900 through 2100')
        return value


class GoalSource(StrictModel):
    key: str
    source_title: str
    source_url: str
    source_locator: str
    interpretation_note: str
    checked_at: date
    valid_until: date
    license_name: str
    license_url: str
    attribution: str

    _urls = field_validator('source_url', 'license_url')(public_url)


class PlantMatch(StrictModel):
    species_id: str
    profile_id: str
    common_name_bn: str
    common_name_en: str
    variety: str
    assessment: Literal['matching_conditions', 'needs_confirmation']
    reasons: list[str]
    uncertainties: list[str]
    sources: list[GoalSource]
    reviewed_at: date
    valid_until: date
    limitations: str


class GoalResult(StrictModel):
    status: Literal['matches_found', 'needs_details', 'no_reviewed_data', 'no_match', 'unsupported_region']
    language: Literal['bn', 'en']
    message: str
    next_steps: list[str]
    recommendations: list[PlantMatch]
    rules_version: Literal['2026-10-04-v1'] = '2026-10-04-v1'
