import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/care_models.dart';
import 'package:groot_app/care_plan_view.dart';
import 'package:groot_app/goal_models.dart';
import 'package:groot_app/goal_intake.dart';
import 'package:groot_app/private_api.dart';
import 'package:groot_app/saved_care_plans.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

Map<String, dynamic> careJson() =>
    jsonDecode(File('../../services/api/tests/fixtures/care_contract.json')
        .readAsStringSync()) as Map<String, dynamic>;
Map<String, dynamic> goalJson() =>
    jsonDecode(File('../../services/api/tests/fixtures/goal_contract.json')
        .readAsStringSync()) as Map<String, dynamic>;
GoalDraft draft() =>
    GoalDraft.fromJson(goalJson()['request'] as Map<String, dynamic>);
Map<String, dynamic> versionJson(
        {String availability = 'current', int version = 1}) =>
    {
      'plan_id': '11111111-1111-4111-8111-111111111111',
      'version': version,
      'created_at': '2026-10-04T10:00:00Z',
      'fingerprint': 'a' * 64,
      'availability': availability,
      'conditions': draft().toJson(),
      'plan': careJson()
    };

class CareApi extends PrivateApi {
  String availability = 'current';
  String status = 'partial';
  bool failSave = false;
  final List<String> requests = [];
  int previews = 0;
  int? revised;
  @override
  Future<CarePreview> previewPlan(
      GoalDraft goal, String profile, int weeks) async {
    previews++;
    return CarePreview({...careJson(), 'weeks': weeks, 'status': status});
  }

  @override
  Future<CareVersion> savePlan(
      GoalDraft goal, String profile, int weeks, String requestId) async {
    requests.add(requestId);
    if (failSave) throw const PrivateApiException('Retry online.');
    return CareVersion(versionJson());
  }

  @override
  Future<CareVersion> revisePlan(String id, GoalDraft goal, String profile,
      int weeks, int expected) async {
    revised = expected;
    return CareVersion(versionJson(version: expected + 1));
  }

  @override
  Future<CareVersion> readPlan(String id, {int? version}) async => CareVersion(
      versionJson(availability: availability, version: version ?? 2));
  @override
  Future<List<CareHistoryItem>> planHistory(String id, {int? before}) async => [
        CareHistoryItem(
            {'version': 1, 'created_at': '2026-10-04', 'status': 'partial'})
      ];
  @override
  Future<List<CareSummary>> plans({String? after}) async => [];
}

Future<void> tapKey(WidgetTester tester, String key) async {
  if (find.byKey(Key(key)).evaluate().isEmpty) {
    await tester.scrollUntilVisible(find.byKey(Key(key)), 300,
        scrollable: find.byType(Scrollable).first);
  }
  await tester.ensureVisible(find.byKey(Key(key)));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(Key(key)));
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  WidgetController.hitTestWarningShouldBeFatal = true;
  test('care contract and chosen-precision conditions round trip', () {
    final preview = CarePreview(careJson());
    expect(preview.steps.single.sources.single.locator, 'Test section 1');
    expect(preview.steps.single.reviewedAt, '2026-01-01');
    expect(preview.issues.single.weeks, [1, 2]);
    expect(draft().toJson(), goalJson()['request']);
    expect(
        newCareRequestId(),
        matches(RegExp(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')));
  });
  test('all care routes are private, explicit save notice and redacted errors',
      () async {
    final paths = <String>[];
    final api = PrivateApi(client: MockClient((request) async {
      if (request.url.path.endsWith('/accounts/login')) {
        return http.Response(
            jsonEncode({
              'access_token': 'c' * 43,
              'account': {
                'handle': 'grower',
                'choices': const ConsentChoices().toJson()
              }
            }),
            200);
      }
      expect(request.headers['Authorization'], 'Bearer ${'c' * 43}');
      expect(request.url.query.contains('Bearer'), isFalse);
      paths.add(request.url.path);
      if (request.method == 'POST') {
        final body = jsonDecode(request.body) as Map;
        expect(body.containsKey('owner_id'), isFalse);
        if (request.url.path.endsWith('/preview')) {
          return http.Response.bytes(utf8.encode(jsonEncode(careJson())), 200,
              headers: {'content-type': 'application/json; charset=utf-8'});
        }
        expect(body['save_notice_version'], carePlanNoticeVersion);
        return http.Response.bytes(utf8.encode(jsonEncode(versionJson())), 201,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }
      if (request.method == 'DELETE') return http.Response('', 204);
      if (request.url.path.endsWith('/versions') ||
          request.url.path == '/v1/plans') {
        return http.Response('[]', 200);
      }
      return http.Response.bytes(utf8.encode(jsonEncode(versionJson())), 200,
          headers: {'content-type': 'application/json; charset=utf-8'});
    }));
    addTearDown(api.close);
    await api.signIn('grower', 'long test passphrase');
    await api.previewPlan(draft(), 'test-profile', 2);
    final saved =
        await api.savePlan(draft(), 'test-profile', 2, newCareRequestId());
    await api.revisePlan(saved.id, draft(), 'test-profile', 2, 1);
    await api.readPlan(saved.id);
    await api.readPlan(saved.id, version: 1);
    await api.planHistory(saved.id, before: 2);
    await api.plans(after: saved.id);
    await api.deletePlan(saved.id);
    expect(paths.length, 8);
  });
  testWidgets(
      'partial preview, explicit disclosure, retry identity and saved version',
      (tester) async {
    final api = CareApi();
    addTearDown(api.close);
    await tester.pumpWidget(MaterialApp(
        home:
            CarePlanView(api: api, draft: draft(), profileId: 'test-profile')));
    await tester.pumpAndSettle();
    expect(find.text('Synthetic reviewed instruction only'), findsOneWidget);
    expect(api.requests, isEmpty);
    api.failSave = true;
    await tapKey(tester, 'care-save');
    expect(find.textContaining('Free goal/soil-description'), findsOneWidget);
    await tapKey(tester, 'care-confirm-save');
    expect(find.text('Retry online.'), findsOneWidget);
    api.failSave = false;
    await tapKey(tester, 'care-save');
    await tapKey(tester, 'care-confirm-save');
    expect(api.requests.length, 2);
    expect(api.requests[0], api.requests[1]);
    expect(find.byKey(const Key('care-version')), findsOneWidget);
    await tapKey(tester, 'care-history');
    expect(find.text('Version 1 · partial'), findsOneWidget);
  });
  testWidgets(
      'blocked preview cannot save, stale snapshots never show instructions',
      (tester) async {
    final api = CareApi()..status = 'blocked';
    addTearDown(api.close);
    await tester.pumpWidget(MaterialApp(
        home:
            CarePlanView(api: api, draft: draft(), profileId: 'test-profile')));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.byKey(const Key('care-save')), 300,
        scrollable: find.byType(Scrollable).first);
    expect(
        tester
            .widget<FilledButton>(find.byKey(const Key('care-save')))
            .onPressed,
        isNull);
    api.availability = 'stale';
    await tester.pumpWidget(MaterialApp(
        home: CarePlanView(key: const Key('saved'), api: api, planId: 'test')));
    await tester.pumpAndSettle();
    expect(find.text('Synthetic reviewed instruction only'), findsNothing);
    expect(find.text('Evidence: stale'), findsOneWidget);
  });
  testWidgets('revision preserves expected version and saved plans empty state',
      (tester) async {
    final api = CareApi();
    addTearDown(api.close);
    await tester.pumpWidget(MaterialApp(
        home: CarePlanView(
            api: api,
            draft: draft(),
            profileId: 'test-profile',
            planId: 'test',
            expectedVersion: 2)));
    await tester.pumpAndSettle();
    await tapKey(tester, 'care-save');
    await tapKey(tester, 'care-confirm-save');
    expect(api.revised, 2);
    expect(find.textContaining('Version 3 ·'), findsOneWidget);
    await tester.pumpWidget(MaterialApp(home: SavedCarePlans(api: api)));
    await tester.pumpAndSettle();
    expect(find.textContaining('No saved plans.'), findsOneWidget);
  });
  testWidgets('revision intake loads saved structured conditions',
      (tester) async {
    final api = CareApi();
    addTearDown(api.close);
    await tester.pumpWidget(MaterialApp(
        home: GoalIntake(
            api: api,
            initialGoal: draft(),
            revisePlanId: 'test',
            expectedVersion: 2)));
    await tester.pumpAndSettle();
    expect(
        tester
            .widget<TextFormField>(find.byKey(const Key('goal-district')))
            .controller!
            .text,
        'Dhaka');
    expect(
        tester
            .widget<TextFormField>(find.byKey(const Key('goal-ph')))
            .controller!
            .text,
        '6.5');
  });
}
