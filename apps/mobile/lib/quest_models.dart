import 'goal_models.dart';

class CareQuest {
  CareQuest(Map<String, dynamic> j)
      : key = j['key'] as String,
        title = j['title'] as String,
        cadence = j['cadence'] as String,
        topic = j['topic'] as String,
        startsOn = j['starts_on'] as String,
        dueOn = j['due_on'] as String,
        instruction = j['instruction'] as String,
        completed = j['completed'] as bool,
        adaptation = j['adaptation'] as String,
        weatherNote = j['weather_note'] as String,
        sources = List.unmodifiable((j['sources'] as List)
            .map((s) => GoalCitation(s as Map<String, dynamic>)));
  final String key,
      title,
      cadence,
      topic,
      startsOn,
      dueOn,
      instruction,
      adaptation,
      weatherNote;
  final bool completed;
  final List<GoalCitation> sources;
}

class QuestWeather {
  QuestWeather(Map<String, dynamic> j)
      : status = j['status'] as String,
        district = j['district'] as String?,
        fetchedAt = j['fetched_at'] as String?,
        message = j['message'] as String,
        attribution = j['attribution'] as String,
        sourceUrl = j['source_url'] as String;
  final String status, message, attribution, sourceUrl;
  final String? district, fetchedAt;
}

class QuestData {
  QuestData(Map<String, dynamic> j)
      : planId = j['plan_id'] as String,
        version = j['version'] as int,
        today = j['today'] as String,
        availability = j['availability'] as String,
        weatherEnabled = j['weather_enabled'] as bool,
        weather = QuestWeather(j['weather'] as Map<String, dynamic>),
        message = j['message'] as String,
        reminderCount = j['reminder_count'] as int,
        quests = List.unmodifiable((j['quests'] as List)
            .map((q) => CareQuest(q as Map<String, dynamic>)));
  final String planId, today, availability, message;
  final int version, reminderCount;
  final bool weatherEnabled;
  final QuestWeather weather;
  final List<CareQuest> quests;
}
