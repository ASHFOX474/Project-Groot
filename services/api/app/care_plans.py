"""Extract scoped approved instructions. No LLM, invented irrigation or dosage."""
from datetime import timedelta
import hashlib
import json

from app.care_models import CareGuidance, PlanInstruction, PlanIssue, PlanPreview
from app.goal_models import GoalSource
from app.recommendations import recommend

TOPICS = ('soil_preparation', 'watering', 'nutrition', 'monitoring')
LABELS = dict(zip(TOPICS, ('মাটি প্রস্তুতি', 'পানি', 'পুষ্টি', 'পর্যবেক্ষণ')))


def stored_goal(goal):
    # Free goal/soil prose is not needed for reproducible rules and is not retained.
    return goal.model_copy(update={'goal': 'Care plan', 'soil': goal.soil.model_copy(update={'description': ''})})


def build_plan(request, candidates, guidance):
    goal = request.goal
    def t(bn, en): return bn if goal.language == 'bn' else en
    preview = PlanPreview(profile_id=request.profile_id, language=goal.language,
        weeks=request.weeks, status='blocked', message=t('ব্যবহারযোগ্য পর্যালোচিত যত্ন নির্দেশনা নেই।', 'No usable reviewed care guidance.'),
        disclaimer=t('এটি বেঁচে থাকা বা ফলনের নিশ্চয়তা নয়। আংশিক পরিকল্পনা সম্পূর্ণ যত্ন বা রোপণের অনুমোদন নয়। নির্দেশনা প্রয়োগের আগে বর্তমান পরিবেশ যাচাই করুন।',
                     'Not a survival/yield guarantee. A partial plan is not complete care or planting approval. Recheck current growing conditions before use.'))
    selected = [p for p in candidates if p['id'] == request.profile_id]
    assessment = recommend(goal, selected)
    if not assessment.recommendations:
        preview.issues = [PlanIssue(code='unsupported_conditions', message=assessment.message)]
        return preview
    match = assessment.recommendations[0]
    basis = {'profile': {**selected[0], 'requirements': sorted(selected[0]['requirements'], key=lambda r: r['key'])},
             'guidance': sorted(guidance, key=lambda r: r['id'])}
    preview.evidence_fingerprint = hashlib.sha256(json.dumps(basis, sort_keys=True, default=str,
        ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    preview.common_name_bn, preview.common_name_en = match.common_name_bn, match.common_name_en
    preview.species_id = match.species_id
    preview.profile_reviewed_at, preview.valid_until = match.reviewed_at, match.valid_until
    preview.suitability_reasons, preview.condition_sources = match.reasons, match.sources
    if match.assessment != 'matching_conditions':
        preview.issues.append(PlanIssue(code='conditions_uncertain', message=' '.join(match.uncertainties)))
    rows = []
    for raw in sorted(guidance, key=lambda r: r['id']):
        if raw['profile_id'] != request.profile_id or not raw['eligible']:
            continue
        item = CareGuidance.model_validate({k: raw[k] for k in CareGuidance.model_fields})
        # Eligibility must not be mistaken for a schema-only reviewed assertion.
        if item.review_status != 'reviewed':
            continue
        source = GoalSource.model_validate(raw['source'])
        end = min(item.week_end, request.weeks)
        if item.week_start > end:
            continue
        until = min(item.valid_until, source.valid_until, match.valid_until)
        starts = goal.planting_date + timedelta(days=0 if item.week_start == 0 else (item.week_start - 1) * 7 + 1)
        ends = goal.planting_date + timedelta(days=end * 7)
        if ends > until or goal.planting_date < item.reviewed_at or goal.planting_date < source.checked_at:
            continue  # Do not extrapolate a source's review into the past/future.
        rows.append((item, source, starts, ends, until))
    conflicted = set()
    conflicts = {}
    for n, (a, source_a, _, _, _) in enumerate(rows):
        for b, source_b, _, _, _ in rows[n + 1:]:
            if a.topic == b.topic and max(a.week_start, b.week_start) <= min(a.week_end, b.week_end, request.weeks) and (
                    a.instruction_bn, a.instruction_en) != (b.instruction_bn, b.instruction_en):
                conflicted.update((a.id, b.id))
                conflicts.setdefault(a.topic, set()).update((a.id, b.id))
    for topic, ids in sorted(conflicts.items()):
        preview.issues.append(PlanIssue(code='conflicting_guidance', topic=topic,
            message=t('একই সময়ের নির্দেশনা ভিন্ন; সব বিরোধপূর্ণ নির্দেশনা স্থগিত। বিশেষজ্ঞের পর্যালোচনা দরকার।',
                      'Overlapping guidance differs; conflicting instructions are withheld pending expert review.'),
            guidance_ids=sorted(ids), sources=[source for item, source, _, _, _ in rows if item.id in ids]))
    coverage = {topic: set() for topic in TOPICS}
    for item, source, starts, ends, until in rows:
        if item.id in conflicted:
            continue
        end = min(item.week_end, request.weeks)
        coverage[item.topic].update(range(item.week_start, end + 1))
        preview.instructions.append(PlanInstruction(guidance_ids=[item.id], topic=item.topic,
            week_start=item.week_start, week_end=end, starts_on=starts, ends_on=ends,
            instruction=item.instruction_bn if goal.language == 'bn' else item.instruction_en,
            reviewed_by=item.reviewed_by, reviewed_at=item.reviewed_at, valid_until=until, sources=[source]))
        preview.valid_until = min(preview.valid_until, until)
    preview.instructions.sort(key=lambda step: (step.week_start, TOPICS.index(step.topic), step.week_end, step.guidance_ids))
    for topic in TOPICS:
        required = {0} if topic == 'soil_preparation' else set(range(1, request.weeks + 1))
        missing = sorted(required - coverage[topic])
        if missing:
            preview.issues.append(PlanIssue(code='missing_guidance', topic=topic, weeks=missing,
                message=t(f'{LABELS[topic]} সম্পর্কে পর্যালোচিত নির্দেশনা নেই; কিছু অনুমান করা হয়নি।',
                          f'Reviewed {topic} guidance is missing for the listed weeks; nothing was invented.')))
    if preview.instructions:
        preview.status = 'partial' if preview.issues else 'ready'
        preview.message = t('আংশিক পরিকল্পনা—অসম্পূর্ণতা পড়ুন।', 'Partial plan—read the gaps.') if preview.issues else t('পর্যালোচিত যত্ন পরিকল্পনা।', 'Reviewed care plan.')
    return preview


def plan_fingerprint(request, preview):
    payload = {'profile_id': request.profile_id, 'weeks': request.weeks,
               'conditions': stored_goal(request.goal).model_dump(mode='json'), 'plan': preview.model_dump(mode='json')}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
