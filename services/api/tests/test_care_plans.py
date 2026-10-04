"""Only synthetic approved guidance is used here, never imported live."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.care_models import PlanRequest, SavePlanRequest, CareGuidance, PlanPreview
from app.catalog_bundle import CatalogBundle, today_bd
from tests.test_catalog_bundle import valid_bundle
from app.care_plans import build_plan, plan_fingerprint, stored_goal
from app.goal_models import GoalSource
from tests.test_recommendations import candidate, goal


def request(**updates):
    return PlanRequest(profile_id='test-profile', goal=goal(), weeks=2, **updates)


def guidance():
    source = candidate()['requirements'][0]
    return [dict(id='care-' + topic.replace('_', '-'), profile_id='test-profile', topic=topic,
                 week_start=0 if topic == 'soil_preparation' else 1,
                 week_end=0 if topic == 'soil_preparation' else 2,
                 instruction_bn='শুধু পরীক্ষার পর্যালোচিত নির্দেশনা ' + topic,
                 instruction_en='Reviewed test instruction ' + topic,
                 source_id='test-source', source_locator='Test care section',
                 interpretation_note='Synthetic care only', review_status='reviewed',
                 reviewed_by='Test reviewer', reviewed_at=date(2026, 1, 1),
                 valid_until=date(2028, 1, 1), eligible=True,
                 source={**{k: v for k, v in source.items() if k in GoalSource.model_fields}, 'key': 'care-' + topic})
            for topic in ('soil_preparation', 'watering', 'nutrition', 'monitoring')]


def test_complete_grounded_plan_has_review_dates_citations_and_week_dates():
    value = build_plan(request(), [candidate()], guidance())
    assert value.status == 'ready' and len(value.instructions) == 4
    assert not value.issues
    assert value.instructions[1].sources[0].source_locator
    assert value.instructions[1].reviewed_at == date(2026, 1, 1)
    assert value.instructions[1].ends_on == date(2026, 10, 18)
    assert value.generator_version
    assert value.instructions[0].topic == 'soil_preparation'
    assert value.instructions[1].topic == 'watering'


def test_missing_or_withdrawn_data_never_uses_demo():
    value = build_plan(request(), [], guidance())
    assert value.status == 'blocked' and not value.instructions
    plant = candidate(); plant['species_id'] = 'demo-okra'
    assert build_plan(request(), [plant], guidance()).status == 'blocked'
    rows = guidance(); rows[1]['eligible'] = False
    result = build_plan(request(), [candidate()], rows)
    assert result.status == 'partial'
    assert not any(s.topic == 'watering' for s in result.instructions)
    assert any(i.code == 'missing_guidance' for i in result.issues)


def test_conflicting_overlap_is_withheld_not_cherry_picked():
    rows = guidance(); other = deepcopy(rows[1]); other['id'] = 'care-conflict'
    other['instruction_en'] = 'Different advice'; rows.append(other)
    value = build_plan(request(), [candidate()], rows)
    assert value.status == 'partial'
    assert not any(s.topic == 'watering' for s in value.instructions)
    conflict = next(i for i in value.issues if i.code == 'conflicting_guidance')
    assert len(conflict.sources) == 2 and conflict.guidance_ids


def test_unknown_conditions_partial_known_mismatch_blocked_and_no_invented_doses():
    value = build_plan(request().model_copy(update={'goal': goal(soil={})}), [candidate()], guidance())
    assert value.status == 'partial' and any(i.code == 'conditions_uncertain' for i in value.issues)
    assert build_plan(request().model_copy(update={'goal': goal(sunlight='shade')}), [candidate()], guidance()).status == 'blocked'
    value = build_plan(request(), [candidate()], [])
    assert value.status == 'blocked' and not value.instructions and len(value.issues) >= 4


def test_future_source_expiry_withholds_affected_guidance_and_localizes_without_translation():
    rows = guidance(); rows[1]['source']['valid_until'] = date(2026, 10, 10)
    value = build_plan(request(), [candidate()], rows)
    assert not any(s.topic == 'watering' for s in value.instructions)
    value = build_plan(request().model_copy(update={'goal': goal(language='bn')}), [candidate()], guidance())
    assert value.instructions[0].instruction.startswith('শুধু')
    assert 'নিশ্চয়তা' in value.disclaimer


def test_snapshots_exclude_goal_prose_and_fingerprints_ignore_order():
    raw = goal(goal='Private transcript', soil={'description': 'Private note'})
    saved = stored_goal(raw)
    assert saved.goal == 'Care plan' and saved.soil.description == ''
    a = build_plan(request(), [candidate()], guidance())
    b = build_plan(request(), [candidate()], list(reversed(guidance())))
    assert plan_fingerprint(request(), a) == plan_fingerprint(request(), b)


@pytest.mark.parametrize('update', [{'weeks': 0}, {'weeks': 13}, {'weeks': True}, {'owner_id': 'foreign'}, {'profile_id': 'demo-okra'}])
def test_request_contract_rejects_unsupported_inputs(update):
    values = {'profile_id': 'test-profile', 'goal': goal(), 'weeks': 2, **update}
    with pytest.raises(ValidationError): PlanRequest.model_validate(values)


def test_save_requires_current_notice_and_guidance_timing_is_validated():
    with pytest.raises(ValidationError): SavePlanRequest.model_validate(request().model_dump())
    row = {k: v for k, v in guidance()[0].items() if k not in ('source', 'eligible', 'profile_id')}
    with pytest.raises(ValidationError): CareGuidance.model_validate({**row, 'week_start': 3, 'week_end': 1})
    with pytest.raises(ValidationError): CareGuidance.model_validate({**row, 'instruction_bn': '\x00'})


def test_shared_care_contract_and_draft_guidance_never_publishes():
    value = json.loads((Path(__file__).parent / 'fixtures/care_contract.json').read_text())
    assert PlanPreview.model_validate(value).model_dump(mode='json') == value
    rows = guidance(); rows[0]['review_status'] = 'draft'
    assert not any(s.topic == 'soil_preparation' for s in build_plan(request(), [candidate()], rows).instructions)
    rows = guidance(); rows[1]['week_start'] = rows[1]['week_end'] = 3
    assert not any(s.topic == 'watering' for s in build_plan(request(), [candidate()], rows).instructions)


@pytest.mark.parametrize('update', [
    {'week_start': 1, 'week_end': 1},
    {'topic': 'watering', 'week_start': 0},
    {'reviewed_by': None},
    {'reviewed_at': today_bd() + timedelta(days=1)},
    {'valid_until': date(2025, 1, 1)},
    {'instruction_en': '\ud800'},
])
def test_care_review_and_timing_reject_invalid_evidence(update):
    row = {k: v for k, v in guidance()[0].items() if k in CareGuidance.model_fields}
    with pytest.raises(ValidationError): CareGuidance.model_validate({**row, **update})


def test_import_rejects_missing_care_sources_and_duplicate_care_ids():
    bundle = valid_bundle()
    row = {k: v for k, v in guidance()[0].items() if k in CareGuidance.model_fields}
    bundle['plants'][0]['profiles'][0]['care_guidance'] = [row, row]
    with pytest.raises(ValidationError): CatalogBundle.model_validate(bundle)
    row['source_id'] = 'missing-source'
    bundle['plants'][0]['profiles'][0]['care_guidance'] = [row]
    with pytest.raises(ValidationError): CatalogBundle.model_validate(bundle)
