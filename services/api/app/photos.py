"""Bounded image sanitization and explicitly unvalidated observation assistance.

No disease classifier, probability, plant segmentation, external provider or
chemical/dose advice. User text and EXIF are never executable/model instructions.
"""
import base64
import binascii
from datetime import date, datetime
from io import BytesIO
from threading import BoundedSemaphore
from typing import Annotated, Literal
from uuid import UUID
import warnings

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, StringConstraints, model_validator, field_validator

from app.accounts import StrictModel, PassportInput

PHOTO_NOTICE = '2026-10-05-photos-v1'
MAX_IMAGE_BYTES = 3 * 1024 * 1024
_slots = BoundedSemaphore(2)
Symptom = Literal['yellowing', 'spots', 'wilting', 'visible_pests', 'rapid_decline']


class PhotoConsent(StrictModel):
    storage: bool = Field(default=False, strict=True)
    health: bool = Field(default=False, strict=True)
    notice_version: Literal['2026-10-05-photos-v1']

    @model_validator(mode='after')
    def separate_opt_ins(self):
        if self.health and not self.storage:
            raise ValueError('Photo storage consent is required')
        return self


class PhotoConsentState(PhotoConsent):
    generation: int = Field(ge=0)


class PhotoInput(StrictModel):
    request_id: UUID
    consent_generation: int = Field(ge=1, strict=True)
    observed_on: date
    media_type: Literal['image/jpeg', 'image/png']
    image_base64: Annotated[str, StringConstraints(min_length=1, max_length=4194304)]
    caption: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ''
    symptoms: list[Symptom] = Field(default_factory=list, max_length=5)
    rights_confirmed: Literal[True]

    @field_validator('rights_confirmed', mode='before')
    @classmethod
    def explicit_rights(cls, value):
        if value is not True:
            raise ValueError('Explicit photo rights confirmation required')
        return value

    @model_validator(mode='after')
    def valid_fields(self):
        PassportInput.not_future(self.observed_on)
        if len(set(self.symptoms)) != len(self.symptoms):
            raise ValueError('Duplicate symptoms')
        return self


class PhotoSummary(StrictModel):
    id: UUID
    observed_on: date
    uploaded_at: datetime
    caption: str
    symptoms: list[Symptom]
    width: int
    height: int
    assistance: dict | None


def sanitize_image(value: PhotoInput):
    if not _slots.acquire(blocking=False):
        raise HTTPException(503, 'Photo processing busy. Retry later.')
    try:
        try:
            raw = base64.b64decode(value.image_base64, validate=True)
            expected = 'JPEG' if value.media_type == 'image/jpeg' else 'PNG'
            magic_ok = raw.startswith(b'\xff\xd8\xff') if expected == 'JPEG' else raw.startswith(b'\x89PNG\r\n\x1a\n')
            if len(raw) > MAX_IMAGE_BYTES or not magic_ok:
                raise ValueError('Invalid image')
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw), formats=['JPEG', 'PNG']) as source:
                    if source.format != expected or source.width * source.height > 12000000 or getattr(source, 'n_frames', 1) != 1:
                        raise ValueError('Invalid dimensions/animation')
                    source.verify()
                with Image.open(BytesIO(raw), formats=['JPEG', 'PNG']) as source:
                    source.load()
                    converted = ImageOps.exif_transpose(source).convert('RGB')
                    converted.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
                    # Fresh pixels, not a save of the original metadata-bearing object.
                    clean = Image.new('RGB', converted.size)
                    clean.paste(converted)
            output = BytesIO()
            clean.save(output, 'JPEG', quality=80, exif=b'', icc_profile=None)
            encoded = output.getvalue()
            if len(encoded) > 524288:
                raise ValueError('Canonical photo too large')
            return encoded, clean
        except (ValueError, binascii.Error, OSError, SyntaxError, UnidentifiedImageError,
                Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise HTTPException(422, 'Use a valid single JPEG/PNG up to 3MiB and 12 megapixels.') from None
    finally:
        _slots.release()


def health_assistance(image, symptoms):
    """Color fractions are NOT health probabilities; background/lighting dominate."""
    sample = image.copy()
    sample.thumbnail((96, 96))
    pixels = list(sample.get_flattened_data())
    yellow = sum(r > 100 and g > 90 and b < min(r, g) * .65 for r, g, b in pixels) / len(pixels)
    brown = sum(50 < r < 180 and r > g * 1.15 and g > b * 1.15 for r, g, b in pixels) / len(pixels)
    light = sum((r + g + b) / 3 for r, g, b in pixels) / len(pixels)
    quality = 'retake' if min(image.size) < 160 or light < 35 or light > 235 else 'usable_not_validated'
    flags = []
    if quality != 'retake' and (yellow > .15 or brown > .15):
        flags.append({'code': 'possible_discoloration', 'basis': 'whole_image_color_heuristic',
                      'message_en': 'Possible yellow/brown areas. They may be normal plant color, soil/background or lighting—not disease evidence.',
                      'message_bn': 'সম্ভাব্য হলুদ/বাদামি অংশ। এটি স্বাভাবিক রং, মাটি/পটভূমি বা আলোও হতে পারে—রোগের প্রমাণ নয়।'})
    for symptom in symptoms:
        flags.append({'code': 'reported_' + symptom, 'basis': 'user_report_not_photo_detection',
                      'message_en': 'You reported ' + symptom.replace('_', ' ') + '; a photo cannot establish its cause.',
                      'message_bn': 'আপনার উল্লেখ করা লক্ষণের কারণ শুধু ছবি থেকে নিশ্চিত করা যায় না।'})
    return {'version': 'local-observation-v1', 'status': 'uncertain',
            'confidence': 'low_uncalibrated', 'probability': None, 'quality': quality,
            'flags': flags, 'expert_recommended': bool(flags) or quality == 'retake',
            'urgent': 'rapid_decline' in symptoms,
            'message_en': 'Not a diagnosis or a healthy-plant certificate. No validated disease model is configured. Take a clear close-up and a whole-plant photo in natural light; seek an agricultural expert for serious, worsening or uncertain symptoms. Do not choose pesticides/fertilizer doses from this result.',
            'message_bn': 'এটি রোগ নির্ণয় বা সুস্থতার সনদ নয়। যাচাইকৃত রোগ শনাক্তকরণ মডেল নেই। প্রাকৃতিক আলোয় পরিষ্কার কাছের ও পুরো গাছের ছবি নিন। গুরুতর, বাড়তে থাকা বা অনিশ্চিত লক্ষণে কৃষি বিশেষজ্ঞের সাহায্য নিন। এই ফল থেকে বালাইনাশক বা সারের মাত্রা ঠিক করবেন না।',
            'expert': {'phone': '16123', 'name': 'Bangladesh agricultural call centre / কৃষি কল সেন্টার',
                       'source_url': 'https://ais.gov.bd/site/page/d9147061-2995-416f-b355-d7feb0d9f9a1/Krishi-call-centre-%2816123%29',
                       'checked_on': '2026-10-05',
                       'availability': 'Official listing checked; live phone reachability/hours not verified. If unavailable, contact your local agricultural extension office.'}}
