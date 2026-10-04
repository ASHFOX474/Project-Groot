import 'goal_models.dart';

const carePlanNoticeVersion = 'care-plan-2026-10-04';

class CareIssue {
  CareIssue(Map<String, dynamic> j)
      : code = j['code'] as String,
        message = j['message'] as String,
        topic = j['topic'] as String?,
        weeks = List.unmodifiable((j['weeks'] as List).cast<int>()),
        sources = List.unmodifiable((j['sources'] as List)
            .map((s) => GoalCitation(s as Map<String, dynamic>)));
  final String code, message;
  final String? topic;
  final List<int> weeks;
  final List<GoalCitation> sources;
}

class CareStep {
  CareStep(Map<String, dynamic> j)
      : topic = j['topic'] as String,
        instruction = j['instruction'] as String,
        weekStart = j['week_start'] as int,
        weekEnd = j['week_end'] as int,
        startsOn = j['starts_on'] as String,
        endsOn = j['ends_on'] as String,
        reviewedAt = j['reviewed_at'] as String,
        validUntil = j['valid_until'] as String,
        reviewedBy = j['reviewed_by'] as String,
        sources = List.unmodifiable((j['sources'] as List)
            .map((s) => GoalCitation(s as Map<String, dynamic>)));
  final String topic,
      instruction,
      startsOn,
      endsOn,
      reviewedAt,
      validUntil,
      reviewedBy;
  final int weekStart, weekEnd;
  final List<GoalCitation> sources;
}

class CarePreview {
  CarePreview(Map<String, dynamic> j)
      : profileId = j['profile_id'] as String,
        language = j['language'] as String,
        weeks = j['weeks'] as int,
        status = j['status'] as String,
        message = j['message'] as String,
        bn = j['common_name_bn'] as String,
        en = j['common_name_en'] as String,
        reviewedAt = j['profile_reviewed_at'] as String?,
        validUntil = j['valid_until'] as String?,
        generator = j['generator_version'] as String,
        disclaimer = j['disclaimer'] as String,
        reasons = List.unmodifiable(
            (j['suitability_reasons'] as List).cast<String>()),
        conditionSources = List.unmodifiable((j['condition_sources'] as List)
            .map((s) => GoalCitation(s as Map<String, dynamic>))),
        steps = List.unmodifiable((j['instructions'] as List)
            .map((s) => CareStep(s as Map<String, dynamic>))),
        issues = List.unmodifiable((j['issues'] as List)
            .map((s) => CareIssue(s as Map<String, dynamic>)));
  final String profileId,
      language,
      status,
      message,
      bn,
      en,
      generator,
      disclaimer;
  final String? reviewedAt, validUntil;
  final int weeks;
  final List<String> reasons;
  final List<GoalCitation> conditionSources;
  final List<CareStep> steps;
  final List<CareIssue> issues;
}

class CareVersion {
  CareVersion(Map<String, dynamic> j)
      : id = j['plan_id'] as String,
        version = j['version'] as int,
        createdAt = j['created_at'] as String,
        fingerprint = j['fingerprint'] as String,
        availability = j['availability'] as String,
        conditions =
            GoalDraft.fromJson(j['conditions'] as Map<String, dynamic>),
        plan = CarePreview(j['plan'] as Map<String, dynamic>);
  final String id, createdAt, fingerprint, availability;
  final int version;
  final GoalDraft conditions;
  final CarePreview plan;
}

class CareSummary {
  CareSummary(Map<String, dynamic> j)
      : id = j['id'] as String,
        version = j['latest_version'] as int,
        bn = j['common_name_bn'] as String,
        en = j['common_name_en'] as String,
        status = j['status'] as String;
  final String id, bn, en, status;
  final int version;
}

class CareHistoryItem {
  CareHistoryItem(Map<String, dynamic> j)
      : version = j['version'] as int,
        date = j['created_at'] as String,
        status = j['status'] as String;
  final int version;
  final String date, status;
}
