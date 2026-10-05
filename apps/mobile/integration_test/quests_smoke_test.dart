import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/quest_board.dart';
import 'package:groot_app/private_api.dart';
import 'package:groot_app/care_reminders.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('fixture quest check-in and native reminder cancellation',
      (tester) async {
    // Explicit synthetic fixture: no API/database writes or live advice approval.
    var completed = false;
    final api = PrivateApi(
        client: MockClient((request) async {
          if (request.method == 'POST') completed = true;
          return http.Response(
              jsonEncode({
                'plan_id': 'fixture-only',
                'version': 1,
                'today': '2026-10-05',
                'availability': 'current',
                'weather_enabled': false,
                'weather': {
                  'status': 'stale',
                  'district': 'dhaka',
                  'fetched_at': '2026-10-04T00:00:00Z',
                  'message': 'Fixture: stale forecast; no weather adaptation.',
                  'attribution': 'Open-Meteo',
                  'source_url': 'https://open-meteo.com/'
                },
                'message': 'Synthetic fixture only; not advice.',
                'reminder_count': completed ? 0 : 1,
                'quests': [
                  {
                    'key': 'observation:2026-10-05',
                    'title': 'Fixture observation',
                    'cadence': 'daily',
                    'topic': 'monitoring',
                    'starts_on': '2026-10-05',
                    'due_on': '2026-10-05',
                    'instruction': 'Fixture observation only.',
                    'sources': [],
                    'completed': completed,
                    'adaptation': 'none',
                    'weather_note': ''
                  }
                ]
              }),
              200);
        }),
        onSessionCleared: CareReminders.cancel);
    await tester.pumpWidget(
        MaterialApp(home: QuestBoard(api: api, planId: 'fixture-only')));
    await tester.pumpAndSettle();
    expect(find.textContaining('stale forecast'), findsOneWidget);
    final button =
        find.byKey(const Key('quest-complete-observation:2026-10-05'));
    await tester.ensureVisible(button);
    await tester.pumpAndSettle();
    await tester.tap(button);
    await tester.pumpAndSettle();
    expect(completed, isTrue);
    await CareReminders.cancel();
    const native = MethodChannel('bd.groot/care_reminders');
    expect(await native.invokeMethod<bool>('status'), isFalse);
    // Permission is explicitly granted only for the emulator test; no OS mock.
    if (const bool.fromEnvironment('NATIVE_REMINDER_TEST')) {
      expect(await CareReminders.enable(20, 0), isTrue);
      expect(await native.invokeMethod<bool>('status'), isTrue);
      await CareReminders.cancel();
      expect(await native.invokeMethod<bool>('status'), isFalse);
    }
    await tester.pumpWidget(const SizedBox.shrink());
    api.close();
    await tester.pumpAndSettle();
  });
}
