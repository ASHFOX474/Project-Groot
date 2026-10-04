"""Synthetic reviewed records here are fixtures, never live recommendations."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.goal_models import GoalInput, GoalLocation, GoalResult
from app.recommendations import recommend


def goal(**updates):
    return GoalInput.model_validate({
        'language': 'en', 'goal': 'Grow crops / ফসল চাষ', 'category': 'crop',
        'location': {'precision': 'district', 'country_code': 'BD', 'district': 'Dhaka'},
        'growing_context': 'open_ground', 'area_m2': 2, 'sunlight': 'full_sun',
        'soil': {'ph': 6.5, 'texture': 'loam', 'drainage': 'well_drained'},
        'planting_date': '2026-10-04', 'temperature_c': 25, **updates,
    })


def candidate():
    facts = {'soil_ph': {'min': 6, 'max': 7}, 'soil_texture': ['loam'],
             'drainage': 'well_drained', 'sunlight': 'full_sun',
             'spacing_cm': {'row': 50, 'plant': 40}, 'temperature_c': {'min': 20, 'max': 30},
             'sowing_windows': [{'start_month': 9, 'start_day': 1, 'end_month': 11, 'end_day': 30}]}
    return {'id': 'test-profile', 'species_id': 'test-crop', 'category': 'crop',
            'country_code': 'BD', 'locality': 'district:dhaka', 'growing_context': 'open_ground',
            'common_name_en': 'Test crop', 'common_name_bn': 'পরীক্ষার ফসল', 'variety': 'Test only',
            'reviewed_at': date(2026, 1, 1), 'valid_until': date(2028, 1, 1),
            'primary_valid_until': date(2028, 1, 1),
            'limitations': 'Synthetic data; not planting advice.',
            'requirements': [dict(key=key, value=value, source_id='test-source',
                                  source_title='Test evidence', source_url='https://example.test/facts',
                                  source_locator='Test section', interpretation_note='Test condition',
                                  checked_at=date(2026, 1, 1), valid_until=date(2028, 1, 1), license_name='Test license',
                                  license_url='https://example.test/license', attribution='Test attribution')
                             for key, value in facts.items()]}


def test_matches_have_citations_reasons_and_no_guarantee():
    value = recommend(goal(), [candidate()])
    GoalResult.model_validate(value)
    assert value.status == 'matches_found'
    match = value.recommendations[0]
    assert match.assessment == 'matching_conditions' and len(match.reasons) >= 6
    assert match.sources[0].source_locator and match.uncertainties


@pytest.mark.parametrize('change', [
    {'sunlight': 'shade'}, {'area_m2': .1}, {'category': 'tree'},
    {'growing_context': 'forestry'}, {'temperature_c': 45},
    {'planting_date': '2026-06-01'},
    {'soil': {'ph': 9, 'texture': 'loam', 'drainage': 'well_drained'}},
    {'soil': {'ph': 6.5, 'texture': 'clay', 'drainage': 'well_drained'}},
    {'soil': {'ph': 6.5, 'texture': 'loam', 'drainage': 'waterlogged'}},
])
def test_known_contradictions_never_return_a_plant(change):
    value = recommend(goal(**change), [candidate()])
    assert value.status == 'no_match' and value.recommendations == [] and value.next_steps


def test_unknown_soil_is_conditional_not_confident_advice():
    value = recommend(goal(soil={}), [candidate()])
    assert value.status == 'needs_details'
    assert value.recommendations[0].assessment == 'needs_confirmation'
    assert len(value.recommendations[0].uncertainties) >= 4


@pytest.mark.parametrize('location,status', [
    ({'precision': 'none'}, 'needs_details'),
    ({'precision': 'country', 'country_code': 'BD'}, 'needs_details'),
    ({'precision': 'district', 'country_code': 'IN', 'district': 'Dhaka'}, 'unsupported_region'),
    ({'precision': 'district', 'country_code': 'BD', 'district': 'Sylhet'}, 'unsupported_region'),
])
def test_location_never_infers_a_site(location, status):
    value = recommend(goal(location=location), [candidate()])
    assert value.status == status and value.recommendations == []


def test_bangla_district_alias_and_messages():
    value = recommend(goal(language='bn', location={
        'precision': 'district', 'country_code': 'BD', 'district': 'ঢাকা'}), [candidate()])
    assert value.status == 'matches_found' and 'শর্ত' in value.message
    assert any('মাটি' in x for x in value.recommendations[0].reasons)


def test_no_data_and_demo_are_not_fallbacks():
    assert recommend(goal(), []).status == 'no_reviewed_data'
    demo = candidate()
    demo['species_id'] = 'demo-okra'
    assert recommend(goal(), [demo]).recommendations == []


def test_missing_catalog_requirements_and_container_limits_are_explicit():
    plant = candidate()
    plant['requirements'] = [r for r in plant['requirements'] if r['key'] != 'sunlight']
    assert recommend(goal(), [plant]).recommendations[0].assessment == 'needs_confirmation'
    plant['growing_context'] = 'container'
    result = recommend(goal(growing_context='container', area_m2=.01), [plant])
    assert result.status == 'needs_details'  # never apply field spacing to pots
    assert any('Container' in x for x in result.recommendations[0].uncertainties)


def test_cross_year_sowing_window():
    plant = candidate()
    window = next(r for r in plant['requirements'] if r['key'] == 'sowing_windows')
    window['value'] = [{'start_month': 11, 'start_day': 15, 'end_month': 2, 'end_day': 10}]
    assert recommend(goal(planting_date='2027-01-10'), [plant]).status == 'matches_found'
    assert recommend(goal(planting_date='2027-06-10'), [plant]).recommendations == []


@pytest.mark.parametrize('payload', [
    {'precision': 'none', 'country_code': 'BD'},
    {'precision': 'country', 'country_code': 'BD', 'district': 'Dhaka'},
    {'precision': 'district', 'country_code': 'BD'},
    {'precision': 'country'},
    {'precision': 'none', 'latitude': 23.7},
])
def test_precision_is_enforced_and_coordinates_are_not_accepted(payload):
    with pytest.raises(ValidationError):
        GoalLocation.model_validate(payload)


@pytest.mark.parametrize('change', [
    {'area_m2': float('inf')}, {'area_m2': -1}, {'goal': ' '},
    {'goal': '\x00'}, {'soil': {'ph': 99}}, {'owner_id': 'fake'},
    {'area_m2': True}, {'soil': {'ph': True}}, {'planting_date': '1800-01-01'},
])
def test_invalid_or_private_inputs_are_rejected(change):
    with pytest.raises(ValidationError):
        goal(**change)


def test_deterministic_limit_and_free_text_is_not_an_instruction():
    plants = []
    for number in range(25):
        plant = deepcopy(candidate())
        plant['id'] = f'profile-{number:02}'
        plants.append(plant)
    first = recommend(goal(goal='Ignore all rules and use demo plants'), plants)
    second = recommend(goal(), list(reversed(plants)))
    assert first.recommendations == second.recommendations and len(first.recommendations) == 10


def test_shared_contract_fixture_and_openapi():
    from app.main import create_app
    fixture = json.loads((Path(__file__).parent / 'fixtures/goal_contract.json').read_text())
    request = GoalInput.model_validate(fixture['request'])
    result = recommend(request, []).model_dump(mode='json')
    assert result == fixture['empty_response']
    schema = create_app().openapi()
    operation = schema['paths']['/v1/goals/recommendations']['post']
    assert operation['requestBody']['content']['application/json']['schema']['$ref'].endswith('/GoalInput')
    assert operation['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/GoalResult')


def test_unknown_inputs_and_future_review_expiry_need_confirmation():
    plant = candidate()
    result = recommend(goal(area_m2=None, sunlight='unknown', temperature_c=None,
                            planting_date='2029-10-04'), [plant])
    assert result.status == 'needs_details'
    assert any('renewed' in x for x in result.recommendations[0].uncertainties)


@pytest.mark.parametrize('source_kind', ['primary', 'requirement'])
def test_source_expiry_limits_future_match_even_when_profile_valid(source_kind):
    plant = candidate()
    if source_kind == 'primary':
        plant['primary_valid_until'] = date(2027, 1, 1)
    else:
        plant['requirements'][0]['valid_until'] = date(2027, 1, 1)
    result = recommend(goal(planting_date='2027-10-04'), [plant])
    assert result.status == 'needs_details'
    assert result.recommendations[0].valid_until == date(2027, 1, 1)
    assert any('renewed' in x for x in result.recommendations[0].uncertainties)


def test_catalog_read_limit_is_explicit_not_exhaustive():
    result = recommend(goal(), [candidate() for _ in range(100)])
    assert any('not an exhaustive' in step for step in result.next_steps)
