/// Consumer types for app.goal_models / FastAPI OpenAPI. Shared fixtures test drift.
class GoalDraft {
  factory GoalDraft.fromJson(Map<String, dynamic> j) {
    final location = j['location'] as Map<String, dynamic>;
    final soil = j['soil'] as Map<String, dynamic>;
    return GoalDraft(
        language: j['language'] as String,
        goal: j['goal'] as String,
        category: j['category'] as String,
        precision: location['precision'] as String,
        country: location['country_code'] as String? ?? 'BD',
        district: location['district'] as String? ?? '',
        context: j['growing_context'] as String,
        area: (j['area_m2'] as num?)?.toDouble(),
        sunlight: j['sunlight'] as String,
        description: soil['description'] as String,
        ph: (soil['ph'] as num?)?.toDouble(),
        texture: soil['texture'] as String,
        drainage: soil['drainage'] as String,
        plantingDate: j['planting_date'] as String,
        temperature: (j['temperature_c'] as num?)?.toDouble());
  }
  const GoalDraft(
      {required this.language,
      required this.goal,
      this.category = 'any',
      this.precision = 'none',
      this.country = 'BD',
      this.district = '',
      this.context = 'container',
      this.area,
      this.sunlight = 'unknown',
      this.description = '',
      this.ph,
      this.texture = 'unknown',
      this.drainage = 'unknown',
      required this.plantingDate,
      this.temperature});
  final String language, goal, category, precision, country, district, context;
  final String sunlight, description, texture, drainage, plantingDate;
  final double? area, ph, temperature;
  Map<String, dynamic> toJson() => {
        'language': language,
        'goal': goal,
        'category': category,
        'location': {
          'precision': precision,
          if (precision != 'none') 'country_code': country,
          if (precision == 'district') 'district': district.trim()
        },
        'growing_context': context,
        'area_m2': area,
        'sunlight': sunlight,
        'soil': {
          'description': description,
          'ph': ph,
          'texture': texture,
          'drainage': drainage
        },
        'planting_date': plantingDate,
        'temperature_c': temperature,
      };
}

double? goalNumber(String text) {
  var normalized = text.trim();
  for (var n = 0; n < 10; n++) {
    normalized = normalized.replaceAll('০১২৩৪৫৬৭৮৯'[n], '$n');
  }
  return double.tryParse(normalized);
}

class GoalCitation {
  GoalCitation(Map<String, dynamic> json)
      : key = json['key'] as String,
        title = json['source_title'] as String,
        url = json['source_url'] as String,
        locator = json['source_locator'] as String,
        note = json['interpretation_note'] as String,
        checkedAt = json['checked_at'] as String,
        validUntil = json['valid_until'] as String,
        license = json['license_name'] as String,
        licenseUrl = json['license_url'] as String,
        attribution = json['attribution'] as String;
  final String key,
      title,
      url,
      locator,
      note,
      checkedAt,
      validUntil,
      license,
      licenseUrl,
      attribution;
}

class GoalPlant {
  GoalPlant(Map<String, dynamic> json)
      : speciesId = json['species_id'] as String,
        profileId = json['profile_id'] as String,
        bn = json['common_name_bn'] as String,
        en = json['common_name_en'] as String,
        variety = json['variety'] as String,
        assessment = json['assessment'] as String,
        reasons = List.unmodifiable((json['reasons'] as List).cast<String>()),
        uncertainties =
            List.unmodifiable((json['uncertainties'] as List).cast<String>()),
        sources = List.unmodifiable((json['sources'] as List)
            .map((x) => GoalCitation(x as Map<String, dynamic>))),
        reviewedAt = json['reviewed_at'] as String,
        validUntil = json['valid_until'] as String,
        limitations = json['limitations'] as String;
  final String speciesId,
      profileId,
      bn,
      en,
      variety,
      assessment,
      reviewedAt,
      validUntil,
      limitations;
  final List<String> reasons, uncertainties;
  final List<GoalCitation> sources;
}

class GoalAssessment {
  GoalAssessment(Map<String, dynamic> json)
      : status = json['status'] as String,
        language = json['language'] as String,
        message = json['message'] as String,
        rulesVersion = json['rules_version'] as String,
        nextSteps =
            List.unmodifiable((json['next_steps'] as List).cast<String>()),
        plants = List.unmodifiable((json['recommendations'] as List)
            .map((x) => GoalPlant(x as Map<String, dynamic>)));
  final String status, language, message, rulesVersion;
  final List<String> nextSteps;
  final List<GoalPlant> plants;
}
