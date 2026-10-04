import copy
from datetime import date, timedelta
import json

import pytest
from pydantic import ValidationError

from app.catalog_bundle import CatalogBundle, read_bundle
from app import catalog_import


def valid_bundle():
    today = date.today()
    return {
        "schema_version": 1,
        "bundle_id": "test-catalog-v1",
        "sources": [{
            "id": "test-source", "title": "Test facts", "publisher": "Test publisher",
            "source_url": "https://example.test/facts", "checked_at": str(today),
            "review_status": "reviewed", "access_status": "public",
            "reuse_status": "open_license", "license_name": "CC-BY-4.0",
            "license_url": "https://example.test/license", "rights_note": "License covers this artifact",
            "attribution": "Test author, test facts; normalized by Groot",
            "reviewed_by": "test-source-reviewer", "valid_until": str(today + timedelta(days=30)),
        }],
        "plants": [{
            "id": "test-okra", "common_name_en": "Okra", "common_name_bn": "ঢেঁড়স",
            "category": "crop", "scientific_name": "Abelmoschus esculentus", "source_id": "test-source",
            "profiles": [{
                "id": "test-okra-field", "country_code": "BD", "locality": "Bangladesh general field guidance",
                "growing_context": "open_ground", "variety": "not_specified",
                "review_status": "reviewed", "reviewed_by": "test-agronomic-reviewer",
                "reviewed_at": str(today), "valid_until": str(today + timedelta(days=30)),
                "limitations": "Not container or saline-site advice",
                "requirements": [
                    {"key": "soil_ph", "value": {"min": 6.0, "max": 6.8},
                     "source_id": "test-source", "source_locator": "page 91, Climate and soil",
                     "interpretation_note": "Source optimum range; not a soil test"},
                ],
            }],
        }],
    }


def test_complete_bundle_and_pending_rights():
    parsed = CatalogBundle.model_validate(valid_bundle())
    assert parsed.plants[0].profiles[0].requirements[0].value == {"min": 6.0, "max": 6.8}
    value = valid_bundle()
    value['sources'][0]['reuse_status'] = 'permission_pending'
    assert CatalogBundle.model_validate(value).sources[0].reuse_status == 'permission_pending'


@pytest.mark.parametrize('change', [
    lambda b: b['sources'][0].update(source_url='file:///secret'),
    lambda b: b['sources'][0].update(source_url='https://user:password@example.test'),
    lambda b: b['sources'][0].update(checked_at='2999-01-01'),
    lambda b: b['sources'][0].update(valid_until='2000-01-01'),
    lambda b: b['sources'][0].update(license_url=None),
    lambda b: b['sources'][0].update(review_status='demo'),
    lambda b: b['plants'][0].update(id='demo-okra'),
    lambda b: b['plants'][0].update(source_id='missing'),
    lambda b: b['plants'][0].update(common_name_bn='  '),
    lambda b: b['plants'][0]['profiles'][0].update(country_code='US'),
    lambda b: b['plants'][0]['profiles'][0].update(reviewed_by=None),
    lambda b: b['plants'][0]['profiles'][0]['requirements'][0].update(source_id='missing'),
    lambda b: b['plants'][0]['profiles'][0]['requirements'][0].update(key='pesticide_dose'),
    lambda b: b['plants'][0]['profiles'][0]['requirements'][0].update(value={'min': 9, 'max': 6}),
    lambda b: b['plants'][0]['profiles'][0]['requirements'][0].update(value={'min': 6, 'max': 20}),
    lambda b: b['plants'][0]['profiles'][0]['requirements'][0].update(value={'min': True, 'max': 8}),
    lambda b: b['sources'].append(copy.deepcopy(b['sources'][0])),
    lambda b: b['plants'].append(copy.deepcopy(b['plants'][0])),
    lambda b: b['plants'][0]['profiles'][0]['requirements'].append(copy.deepcopy(b['plants'][0]['profiles'][0]['requirements'][0])),
    lambda b: b.update(unexpected='reject extra fields'),
])
def test_invalid_bundle_rejected(change):
    value = valid_bundle()
    change(value)
    with pytest.raises(ValidationError):
        CatalogBundle.model_validate(value)


@pytest.mark.parametrize('key,value', [
    ('soil_texture', ['sandy_loam', 'clay_loam']),
    ('drainage', 'well_drained'),
    ('sunlight', 'full_sun'),
    ('spacing_cm', {'row': 60, 'plant': 30}),
    ('temperature_c', {'min': 20, 'max': 25}),
    ('sowing_windows', [{'start_month': 2, 'start_day': 15, 'end_month': 3, 'end_day': 15}]),
])
def test_supported_requirement_types(key, value):
    bundle = valid_bundle()
    bundle['plants'][0]['profiles'][0]['requirements'][0].update(key=key, value=value)
    assert CatalogBundle.model_validate(bundle)


def test_json_reader_rejects_duplicate_keys_oversize_and_invalid_json(tmp_path):
    path = tmp_path / 'bundle.json'
    path.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(ValueError, match='Duplicate JSON key'):
        read_bundle(path)
    path.write_text(' ' * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match='2 MiB'):
        read_bundle(path)
    path.write_text('{')
    with pytest.raises(ValueError):
        read_bundle(path)
    path.write_text(json.dumps(valid_bundle(), ensure_ascii=False))
    assert read_bundle(path).bundle_id == 'test-catalog-v1'


@pytest.mark.parametrize('key,value', [
    ('soil_ph', {'min': 6}), ('soil_ph', {'min': float('nan'), 'max': 7}),
    ('soil_texture', []), ('soil_texture', ['loam','loam']),
    ('drainage', 'waterlogged'), ('sunlight', 6),
    ('sowing_windows', []), ('sowing_windows', [{'start_month': 2}]),
    ('sowing_windows', [{'start_month': True,'start_day': 1,'end_month': 2,'end_day': 20}]),
    ('sowing_windows', [{'start_month': 2,'start_day': 30,'end_month': 3,'end_day': 1}]),
])
def test_invalid_requirement_shapes_and_calendar_days(key, value):
    bundle = valid_bundle()
    bundle['plants'][0]['profiles'][0]['requirements'][0].update(key=key, value=value)
    with pytest.raises(ValidationError):
        CatalogBundle.model_validate(bundle)


def test_profile_review_dates_and_reserved_source_identity():
    value = valid_bundle()
    value['plants'][0]['profiles'][0]['reviewed_at'] = '2999-01-01'
    with pytest.raises(ValidationError):
        CatalogBundle.model_validate(value)
    value['plants'][0]['profiles'][0].update(reviewed_at='2026-01-01', valid_until='2025-01-01')
    with pytest.raises(ValidationError):
        CatalogBundle.model_validate(value)
    value = valid_bundle()
    value['sources'][0]['id'] = 'starter-samples'
    with pytest.raises(ValidationError):
        CatalogBundle.model_validate(value)


def test_import_cli_defaults_to_validation_and_redacts_input(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'catalog.json'
    path.write_text(json.dumps(valid_bundle()))
    def forbid(*args):
        raise AssertionError('Validation must not connect to a database')
    monkeypatch.setattr(catalog_import, 'import_bundle', forbid)
    assert catalog_import.main([str(path)]) == 0
    assert 'no database writes' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        catalog_import.main([str(path), '--apply'])
    capsys.readouterr()
    monkeypatch.setattr(catalog_import, 'import_bundle', lambda *args: {'already_imported': False})
    assert catalog_import.main([str(path), '--apply', '--confirm']) == 0
    capsys.readouterr()
    path.write_text(json.dumps({'password': 'SECRET'}))
    assert catalog_import.main([str(path)]) == 1
    output = capsys.readouterr().err
    assert 'validation failed' in output and 'SECRET' not in output
    path.write_text('{')
    assert catalog_import.main([str(path)]) == 1
    assert 'invalid or unreadable' in capsys.readouterr().err
    path.write_text(json.dumps(valid_bundle()))
    def refusal(*args):
        raise RuntimeError('not at migration head')
    monkeypatch.setattr(catalog_import, 'import_bundle', refusal)
    assert catalog_import.main([str(path), '--apply', '--confirm']) == 1
    assert 'not at migration head' in capsys.readouterr().err
    def failure(*args):
        raise Exception('SECRET URL')
    monkeypatch.setattr(catalog_import, 'import_bundle', failure)
    assert catalog_import.main([str(path), '--apply', '--confirm']) == 1
    output = capsys.readouterr().err
    assert 'rolled back' in output and 'SECRET' not in output
