import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'goal_models.dart';
import 'care_models.dart';

const privacyNoticeVersion = '2026-10-04';

DateTime bangladeshToday() {
  final now = DateTime.now().toUtc().add(const Duration(hours: 6));
  return DateTime(now.year, now.month, now.day);
}

class PrivateApiException implements Exception {
  const PrivateApiException(this.message, {this.signedOut = false});
  final String message;
  final bool signedOut;
}

class ConsentChoices {
  const ConsentChoices(
      {this.location = false, this.community = false, this.impact = false});
  final bool location;
  final bool community;
  final bool impact;
  Map<String, dynamic> toJson() => {
        'location_opt_in': location,
        'community_opt_in': community,
        'impact_opt_in': impact,
      };
  factory ConsentChoices.fromJson(Map<String, dynamic> json) => ConsentChoices(
        location: json['location_opt_in'] as bool,
        community: json['community_opt_in'] as bool,
        impact: json['impact_opt_in'] as bool,
      );
}

class GrowerAccount {
  const GrowerAccount(this.handle, this.choices);
  final String handle;
  final ConsentChoices choices;
  factory GrowerAccount.fromJson(Map<String, dynamic> json) => GrowerAccount(
        json['handle'] as String,
        ConsentChoices.fromJson(json['choices'] as Map<String, dynamic>),
      );
}

class PlantPassport {
  const PlantPassport(
      {required this.id,
      required this.nickname,
      required this.species,
      required this.plantedOn,
      required this.conditions,
      this.speciesId});
  final String id;
  final String nickname;
  final String species;
  final String? speciesId;
  final String plantedOn;
  final Map<String, dynamic> conditions;
  factory PlantPassport.fromJson(Map<String, dynamic> json) => PlantPassport(
        id: json['id'] as String,
        nickname: json['nickname'] as String,
        species: json['species_name'] as String,
        speciesId: json['species_id'] as String?,
        plantedOn: json['planted_on'] as String,
        conditions:
            Map.unmodifiable(json['conditions'] as Map<String, dynamic>),
      );
  Map<String, dynamic> toJson() => {
        'nickname': nickname,
        'species_name': species,
        'species_id': speciesId,
        'planted_on': plantedOn,
        'conditions': conditions
      };
}

class CareEvent {
  const CareEvent(this.id, this.kind, this.date, this.note);
  final String id;
  final String kind;
  final String date;
  final String note;
  factory CareEvent.fromJson(Map<String, dynamic> json) => CareEvent(
        json['id'] as String,
        json['kind'] as String,
        json['occurred_on'] as String,
        json['note'] as String,
      );
}

class PrivateApi {
  PrivateApi({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = baseUrl ??
            const String.fromEnvironment('API_BASE_URL',
                defaultValue: 'http://10.0.2.2:8000');
  final http.Client _client;
  final String _baseUrl;
  // Deliberately memory-only. App restart requires sign-in; no token/password is
  // written to preferences, files, URLs or logs. Persistence needs secure storage.
  String? _token;

  Future<dynamic> _request(String method, String path,
      [Map<String, dynamic>? body]) async {
    final uri = Uri.parse('$_baseUrl/v1/$path');
    if (uri.scheme != 'https' && !kDebugMode) {
      throw const PrivateApiException('Secure HTTPS is required.');
    }
    final request = http.Request(method, uri)
      ..headers['Content-Type'] = 'application/json';
    if (_token case final token?) {
      request.headers['Authorization'] = 'Bearer $token';
    }
    if (body != null) request.body = jsonEncode(body);
    final response = await http.Response.fromStream(
            await _client.send(request).timeout(const Duration(seconds: 15)))
        .timeout(const Duration(seconds: 15));
    if (response.statusCode == 401) {
      _token = null;
      throw const PrivateApiException(
          'Sign in again; check your handle and password.',
          signedOut: true);
    }
    if (response.statusCode >= 400) {
      throw PrivateApiException(switch (response.statusCode) {
        409 => path.startsWith('plans')
            ? 'Plan unavailable or changed. Preview/reload reviewed guidance before saving.'
            : 'Handle unavailable. Choose another.',
        422 => path.startsWith('goals/') || path.startsWith('plans')
            ? 'Check the goal, chosen location and measurements.'
            : 'Check the fields and dates. Demo species cannot be linked.',
        429 => 'Too many attempts. Please wait before trying again.',
        404 => 'This plant is unavailable.',
        _ => 'Service unavailable. Try again later.',
      });
    }
    return response.statusCode == 204
        ? null
        : jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<GrowerAccount> signIn(String handle, String password,
      {bool register = false,
      ConsentChoices choices = const ConsentChoices()}) async {
    final result =
        await _request('POST', 'accounts/${register ? 'register' : 'login'}', {
      'handle': handle,
      'password': password,
      if (register) 'notice_version': privacyNoticeVersion,
      if (register) 'choices': choices.toJson(),
    }) as Map<String, dynamic>;
    _token = result['access_token'] as String;
    return GrowerAccount.fromJson(result['account'] as Map<String, dynamic>);
  }

  Future<GrowerAccount> consent(ConsentChoices choices) async =>
      GrowerAccount.fromJson(await _request('PUT', 'accounts/consent', {
        'choices': choices.toJson(),
        'notice_version': privacyNoticeVersion
      }) as Map<String, dynamic>);

  Future<void> logout() async {
    try {
      await _request('POST', 'accounts/logout');
    } finally {
      _token = null;
    }
  }

  Future<void> changePassword(String current, String replacement) async {
    await _request('POST', 'accounts/password',
        {'current_password': current, 'new_password': replacement});
    _token = null;
  }

  Future<void> deleteAccount(String password) async {
    await _request('POST', 'accounts/delete', {'password': password});
    _token = null;
  }

  Future<List<PlantPassport>> plants({String? after}) async {
    final result = await _request(
            'GET', 'passports?limit=20${after == null ? '' : '&after=$after'}')
        as List;
    return result
        .map((x) => PlantPassport.fromJson(x as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<PlantPassport> save(PlantPassport plant,
          {bool create = false}) async =>
      PlantPassport.fromJson(await _request(
          create ? 'POST' : 'PUT',
          create ? 'passports' : 'passports/${plant.id}',
          plant.toJson()) as Map<String, dynamic>);

  Future<void> deletePlant(String id) async {
    await _request('DELETE', 'passports/$id');
  }

  Future<List<CareEvent>> care(String id, {String? after}) async {
    final result = await _request('GET',
            'passports/$id/care?limit=20${after == null ? '' : '&after=$after'}')
        as List;
    return result
        .map((x) => CareEvent.fromJson(x as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<void> addCare(String id, String kind, String date, String note) async {
    await _request('POST', 'passports/$id/care',
        {'kind': kind, 'occurred_on': date, 'note': note});
  }

  Future<GoalAssessment> recommend(GoalDraft goal) async => GoalAssessment(
      await _request('POST', 'goals/recommendations', goal.toJson())
          as Map<String, dynamic>);

  Future<CarePreview> previewPlan(
          GoalDraft goal, String profile, int weeks) async =>
      CarePreview(await _request('POST', 'plans/preview', {
        'profile_id': profile,
        'goal': goal.toJson(),
        'weeks': weeks
      }) as Map<String, dynamic>);

  Future<CareVersion> savePlan(
          GoalDraft goal, String profile, int weeks, String requestId) async =>
      CareVersion(await _request('POST', 'plans', {
        'profile_id': profile,
        'goal': goal.toJson(),
        'weeks': weeks,
        'request_id': requestId,
        'save_notice_version': carePlanNoticeVersion
      }) as Map<String, dynamic>);

  Future<CareVersion> revisePlan(String id, GoalDraft goal, String profile,
          int weeks, int expected) async =>
      CareVersion(await _request('POST', 'plans/$id/versions', {
        'profile_id': profile,
        'goal': goal.toJson(),
        'weeks': weeks,
        'expected_version': expected,
        'save_notice_version': carePlanNoticeVersion
      }) as Map<String, dynamic>);

  Future<CareVersion> readPlan(String id, {int? version}) async =>
      CareVersion(await _request(
              'GET', 'plans/$id${version == null ? '' : '/versions/$version'}')
          as Map<String, dynamic>);

  Future<List<CareSummary>> plans({String? after}) async => (await _request(
              'GET', 'plans?limit=20${after == null ? '' : '&after=$after'}')
          as List)
      .map((x) => CareSummary(x as Map<String, dynamic>))
      .toList(growable: false);

  Future<List<CareHistoryItem>> planHistory(String id, {int? before}) async =>
      (await _request('GET',
                  'plans/$id/versions?limit=20${before == null ? '' : '&before=$before'}')
              as List)
          .map((x) => CareHistoryItem(x as Map<String, dynamic>))
          .toList(growable: false);

  Future<void> deletePlan(String id) async {
    await _request('DELETE', 'plans/$id');
  }

  void close() {
    _token = null;
    _client.close();
  }
}
