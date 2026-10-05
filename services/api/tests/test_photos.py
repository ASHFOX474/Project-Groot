import base64
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, PngImagePlugin
import pytest
from pydantic import ValidationError

from app.catalog_bundle import today_bd
from app.photos import PhotoInput, PhotoConsent, sanitize_image, health_assistance


def payload(raw, kind='image/png', **extra):
    from uuid import uuid4
    return PhotoInput.model_validate({'request_id': str(uuid4()), 'consent_generation': 1,
        'observed_on': today_bd().isoformat(), 'media_type': kind,
        'image_base64': base64.b64encode(raw).decode(), 'rights_confirmed': True, **extra})


def picture(color=(170, 190, 40), size=(320, 240), fmt='PNG', **options):
    output = BytesIO()
    Image.new('RGB', size, color).save(output, fmt, **options)
    return output.getvalue()


def test_canonical_image_strips_exif_png_text_and_limits_dimensions():
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('private-location', 'secret photo caption/address')
    raw = picture(size=(1800, 900), pnginfo=metadata)
    jpeg, clean = sanitize_image(payload(raw))
    assert clean.size == (1280, 640) and len(jpeg) <= 524288
    assert b'secret photo' not in jpeg
    with Image.open(BytesIO(jpeg)) as result:
        assert result.format == 'JPEG' and not result.getexif()
        assert 'icc_profile' not in result.info and 'comment' not in result.info
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = 'private GPS/description'
    encoded, clean = sanitize_image(payload(picture(fmt='JPEG', exif=exif), 'image/jpeg'))
    assert clean.size == (240, 320) and b'private GPS' not in encoded


@pytest.mark.parametrize('raw,kind', [(b'not image','image/png'),
    (b'<svg>attack</svg>','image/png'), (picture(fmt='JPEG'),'image/png'),
    (picture()[:-20], 'image/png'), (b'\xff\xd8\xff' + b'a' * 3145728,'image/jpeg')],
    ids=['not-image','svg','mime-mismatch','truncated','over-limit'])
def test_invalid_mismatched_truncated_and_oversized_images_rejected(raw, kind):
    with pytest.raises((HTTPException, ValidationError)) as error:
        sanitize_image(payload(raw, kind))
    if isinstance(error.value, HTTPException):
        assert error.value.status_code == 422


def test_animation_and_pixel_bomb_rejected():
    output = BytesIO()
    frames = [Image.new('RGB', (20, 20), c) for c in ['green', 'red']]
    frames[0].save(output, 'PNG', save_all=True, append_images=frames[1:])
    with pytest.raises(HTTPException):
        sanitize_image(payload(output.getvalue()))
    with pytest.raises(HTTPException):
        sanitize_image(payload(picture(size=(4000, 3100))))


def test_busy_processor_and_invalid_base64_are_safe(monkeypatch):
    import app.photos as module
    class Busy:
        def acquire(self, **kwargs): return False
    monkeypatch.setattr(module, '_slots', Busy())
    with pytest.raises(HTTPException) as error:
        sanitize_image(payload(picture()))
    assert error.value.status_code == 503


@pytest.mark.parametrize('change', [{'rights_confirmed': False}, {'rights_confirmed': 1},
    {'symptoms': ['unknown']}, {'symptoms': ['spots', 'spots']},
    {'consent_generation': True}, {'observed_on': '2099-01-01'}, {'owner_id': 'caller'}])
def test_photo_contract_does_not_accept_implied_rights_or_arbitrary_fields(change):
    with pytest.raises(ValidationError):
        payload(picture(), **change)


def test_missing_notice_and_inconsistent_consent_rejected():
    with pytest.raises(ValidationError): PhotoConsent(storage=True)
    with pytest.raises(ValidationError):
        PhotoConsent(storage=False, health=True, notice_version='2026-10-05-photos-v1')


def test_assistance_cannot_claim_probability_diagnosis_or_healthy_certification():
    healthy_color = health_assistance(Image.new('RGB', (240, 240), (30, 170, 50)), [])
    possible = health_assistance(Image.new('RGB', (240, 240), (180, 160, 20)), ['rapid_decline'])
    assert healthy_color['status'] == possible['status'] == 'uncertain'
    assert healthy_color['probability'] is possible['probability'] is None
    assert possible['confidence'] == 'low_uncalibrated'
    assert possible['urgent'] and possible['expert_recommended']
    assert possible['flags'][0]['code'] == 'possible_discoloration'
    assert possible['flags'][1]['basis'] == 'user_report_not_photo_detection'
    assert possible['expert']['phone'] == '16123'
    retake = health_assistance(Image.new('RGB', (30, 30), (0, 0, 0)), [])
    assert retake['quality'] == 'retake' and retake['expert_recommended']


def test_chunked_photo_body_limit_remains_exact_and_redacted(monkeypatch):
    import asyncio
    from app.privacy_middleware import PrivacyMiddleware
    monkeypatch.setenv('APP_ENV', 'development')
    accepted = []
    async def app(scope, receive, send): accepted.append(await receive())
    async def request(path, sizes):
        chunks = [{'type': 'http.request', 'body': b'x' * size, 'more_body': i < len(sizes)-1}
                  for i, size in enumerate(sizes)]
        responses = []
        async def receive(): return chunks.pop(0)
        async def send(value): responses.append(value)
        await PrivacyMiddleware(app)({'type': 'http', 'path': path, 'method': 'POST', 'scheme': 'http'}, receive, send)
        return responses
    path = '/v1/passports/00000000-0000-0000-0000-000000000001/photos'
    response = asyncio.run(request(path, [2100000, 2100001]))
    assert response[0]['status'] == 413 and not accepted
    response = asyncio.run(request(path + '/other', [17000]))
    assert response[0]['status'] == 413 and not accepted
    assert asyncio.run(request(path, [10000, 10000])) == []
    assert len(accepted[0]['body']) == 20000
