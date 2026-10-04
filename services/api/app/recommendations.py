"""Conservative deterministic matching of eligible catalog profiles, not an LLM.

The database eligibility view is the source boundary. Free goal/soil prose is
never parsed into facts, commands or assumed plot conditions. Unknown != match.
"""
import unicodedata

from app.goal_models import GoalInput, GoalResult, GoalSource, PlantMatch

# UI aliases, not a claim that these districts have reviewed planting data.
DISTRICTS = {'ঢাকা': 'dhaka', 'চট্টগ্রাম': 'chattogram', 'খুলনা': 'khulna',
             'রাজশাহী': 'rajshahi', 'বরিশাল': 'barishal', 'সিলেট': 'sylhet',
             'রংপুর': 'rangpur', 'ময়মনসিংহ': 'mymensingh', 'চিটাগং': 'chattogram',
             'chittagong': 'chattogram', 'barisal': 'barishal'}


def district_key(value):
    value = unicodedata.normalize('NFC', value).strip().casefold()
    return DISTRICTS.get(value, value)


def recommend(goal: GoalInput, candidates: list[dict]) -> GoalResult:
    def text(bn, en):
        return bn if goal.language == 'bn' else en

    def result(status, message, next_steps, matches=None):
        if len(candidates) >= 100:
            next_steps = [*next_steps, text('প্রথম ১০০টি যোগ্য প্রোফাইল দেখা হয়েছে; এটি সম্পূর্ণ তালিকা বা পূর্ণাঙ্গ অনুসন্ধান নয়।',
                          'Only the first 100 eligible profiles were considered; this is not an exhaustive catalog search.')]
        return GoalResult(status=status, language=goal.language, message=message,
                          next_steps=next_steps, recommendations=matches or [])

    caution = text('এটি শর্ত মিলানোর ফল, বেঁচে থাকা বা ফলনের নিশ্চয়তা নয়। লিখিত লক্ষ্য ও মাটির বর্ণনা স্বয়ংক্রিয়ভাবে ব্যাখ্যা করা হয়নি।',
                   'Condition matching is not a survival/yield guarantee. Free-text goals and soil descriptions are not automatically interpreted.')
    if goal.location.country_code not in (None, 'BD'):
        return result('unsupported_region', text('শুধু বাংলাদেশের পর্যালোচিত তথ্য ব্যবহার করা হয়।',
                      'Only reviewed Bangladesh profiles are supported.'), [caution])
    if goal.location.precision != 'district':
        return result('needs_details', text('জেলা না জানলে স্থানীয় উপযোগিতা যাচাই করা যায় না। আরও অবস্থান দিতে বাধ্য নন।',
                      'Local suitability cannot be checked without a district. You do not have to share more location.'),
                      [text('চাইলে শুধু জেলা দিন; ঠিকানা বা GPS দরকার নেই।',
                            'Optionally share only a district; no address or GPS is needed.'), caution])
    candidates = [c for c in candidates if not c['species_id'].startswith('demo-')]
    if not candidates:
        return result('no_reviewed_data', text('এখনও অনুমোদিত উদ্ভিদ তথ্য নেই। ডেমো বা খসড়া থেকে পরামর্শ দেওয়া হবে না।',
                      'No approved plant profiles are available yet. Demo or draft data will not be used.'),
                      [text('অধিকার-যাচাইকৃত স্থানীয় পর্যালোচনা যোগ হলে আবার চেষ্টা করুন।',
                            'Try again after rights-cleared, locally reviewed profiles are added.'), caution])
    scope = 'district:' + district_key(goal.location.district)
    regional = [c for c in candidates if c['country_code'] == 'BD' and c['locality'] == scope]
    if not regional:
        return result('unsupported_region', text('এই জেলার জন্য নির্দিষ্ট পর্যালোচিত তথ্য নেই। দেশের সাধারণ তথ্যকে স্থানীয় প্রমাণ ধরা হয়নি।',
                      'No explicitly reviewed profile covers this district. Country-level prose is not treated as local evidence.'), [caution])
    matches = []
    rejected = set()
    for plant in sorted(regional, key=lambda p: p['id']):
        if plant['growing_context'] != goal.growing_context or (
                goal.category != 'any' and plant['category'] != goal.category):
            rejected.add(text('লক্ষ্যের ধরন বা চাষের পরিবেশের অমিল।', 'Goal category or growing context differs.'))
            continue
        facts = {r['key']: r for r in plant['requirements']}
        reasons = [text('পর্যালোচিত জেলা ও চাষের পরিবেশ আপনার নির্বাচনের সঙ্গে মেলে।',
                        'The reviewed district and growing context match your selections.')]
        unknown = []
        conflicts = []

        def compare(key, supplied, fits, bn, en):
            fact = facts.get(key)
            if fact is None:
                unknown.append(text(f'উৎসে {key} সম্পর্কে যথেষ্ট তথ্য নেই।', f'The source lacks a reviewed {key} requirement.'))
            elif supplied is None or supplied == 'unknown':
                unknown.append(text(f'{key} যাচাই করতে আপনার তথ্য দরকার।', f'Your {key} details are needed to check this condition.'))
            elif not fits(supplied, fact['value']):
                conflicts.append(text(f'{key} পর্যালোচিত শর্তের সঙ্গে মেলে না।', f'{key} does not match the reviewed requirement.'))
            else:
                reasons.append(text(bn, en))

        compare('sunlight', goal.sunlight, lambda a, b: a == b,
                'আপনার সূর্যালোকের ধরন উৎসের শর্তের সঙ্গে মেলে।', 'Your sunlight category matches the cited requirement.')
        compare('soil_ph', goal.soil.ph, lambda a, b: b['min'] <= a <= b['max'],
                'মাটির দেওয়া pH উৎসের সীমার মধ্যে।', 'Your reported soil pH is within the cited range.')
        compare('soil_texture', goal.soil.texture, lambda a, b: a in b,
                'মাটির গঠন উৎসের গ্রহণযোগ্য তালিকায় আছে।', 'Your soil texture is in the cited acceptable list.')
        compare('drainage', goal.soil.drainage, lambda a, b: a == b,
                'মাটির পানি নিষ্কাশনের ধরন উৎসের শর্তের সঙ্গে মেলে।', 'Your drainage category matches the cited requirement.')
        compare('temperature_c', goal.temperature_c, lambda a, b: b['min'] <= a <= b['max'],
                'দেওয়া তাপমাত্রা উৎসের সীমার মধ্যে; এটি পূর্বাভাস নয়।', 'Your reported temperature is within the cited range; it is not a forecast.')
        if goal.growing_context == 'container':
            unknown.append(text('টবের গভীরতা, শিকড়ের জায়গা ও মাধ্যমের উপযোগিতা এই তথ্য দিয়ে যাচাই হয় না।',
                                'Container depth, rooting space and substrate suitability are not validated by these requirements.'))
        else:
            compare('spacing_cm', goal.area_m2, lambda a, b: a >= b['row'] * b['plant'] / 10000,
                    'মোট জায়গা উৎসের এক গাছের দূরত্বের ক্ষেত্রফলের চেয়ে কম নয়; আকার ও চলাচলের জায়গা আলাদা যাচাই চাই।',
                    'Total area covers one cited spacing cell; plot shape and access space still need checking.')
        md = (goal.planting_date.month, goal.planting_date.day)

        def in_window(_, windows):
            for window in windows:
                start = (window['start_month'], window['start_day'])
                end = (window['end_month'], window['end_day'])
                within = (start <= md <= end) if start <= end else (md >= start or md <= end)
                if within:
                    return True
            return False

        compare('sowing_windows', md, in_window,
                'নির্বাচিত তারিখ উৎসের বীজ বপনের সময়ের মধ্যে; রোপণ ও ফসল তোলার তারিখ নয়।',
                'The selected date is in a cited seed-sowing window, not a transplant or harvest schedule.')
        # The earliest profile OR referenced-source expiry controls future advice.
        sources = [GoalSource.model_validate({k: r[k] for k in GoalSource.model_fields})
                   for r in plant['requirements']]
        valid_until = min(plant['valid_until'], plant['primary_valid_until'],
                          *(source.valid_until for source in sources))
        if goal.planting_date > valid_until:
            unknown.append(text('বপনের তারিখের আগে উৎসের পর্যালোচনা নবায়ন দরকার।', 'Source review must be renewed before the planned planting date.'))
        if conflicts:
            rejected.update(conflicts)
            continue
        matches.append(PlantMatch(
            species_id=plant['species_id'], profile_id=plant['id'],
            common_name_bn=plant['common_name_bn'], common_name_en=plant['common_name_en'],
            variety=plant['variety'], assessment='needs_confirmation' if unknown else 'matching_conditions',
            reasons=reasons, uncertainties=[*unknown, caution],
            sources=sources, reviewed_at=plant['reviewed_at'],
            valid_until=valid_until, limitations=plant['limitations']))
    matches.sort(key=lambda x: (x.assessment != 'matching_conditions', x.profile_id))
    if not matches:
        return result('no_match', text('নির্বাচিত শর্তে পর্যালোচিত মিল পাওয়া যায়নি।', 'No reviewed plant matches these conditions.'),
                      [*sorted(rejected), caution])
    ready = any(m.assessment == 'matching_conditions' for m in matches)
    return result('matches_found' if ready else 'needs_details',
                  text('পর্যালোচিত শর্তের মিল পাওয়া গেছে; অনিশ্চয়তা পড়ুন।', 'Reviewed conditions match; read the uncertainties.') if ready else
                  text('সম্ভাব্য মিলের জন্য আরও তথ্য বা বিশেষজ্ঞের নিশ্চিতকরণ দরকার।', 'Possible matches need more details or expert confirmation.'),
                  [caution], matches[:10])
