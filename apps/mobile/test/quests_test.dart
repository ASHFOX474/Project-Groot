import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/quest_board.dart';
import 'package:groot_app/private_api.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'dart:convert';

Map<String, dynamic> board() => {
      'plan_id': 'test-plan',
      'version': 1,
      'today': '2026-10-05',
      'availability': 'current',
      'weather_enabled': false,
      'weather': {
        'status': 'stale',
        'district': 'dhaka',
        'fetched_at': '2026-10-04T00:00:00Z',
        'message': 'Forecast is stale. No weather adaptation.',
        'attribution': 'Weather data: Open-Meteo (CC BY 4.0).',
        'source_url': 'https://open-meteo.com/'
      },
      'quests': [
        {
          'key': 'observation:2026-10-05',
          'title': 'Observe your plant',
          'cadence': 'daily',
          'topic': 'monitoring',
          'starts_on': '2026-10-05',
          'due_on': '2026-10-05',
          'instruction': 'Observation only.',
          'sources': [],
          'completed': false,
          'adaptation': 'none',
          'weather_note': ''
        }
      ],
      'message': 'One check-in',
      'reminder_count': 1
    };

void main() {
  testWidgets('stale data is visible and completion reloads the board',
      (tester) async {
    var completed = false;
    final client = MockClient((request) async {
      if (request.method == 'POST') completed = true;
      final value = board();
      (value['quests'] as List)[0]['completed'] = completed;
      return http.Response(jsonEncode(value), 200);
    });
    await tester.pumpWidget(MaterialApp(
        home:
            QuestBoard(api: PrivateApi(client: client), planId: 'test-plan')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Forecast is stale'), findsOneWidget);
    expect(find.text('Observe your plant'), findsOneWidget);
    final complete =
        find.byKey(const Key('quest-complete-observation:2026-10-05'));
    await tester.ensureVisible(complete);
    await tester.pumpAndSettle();
    await tester.tap(complete);
    await tester.pumpAndSettle();
    expect(completed, isTrue);
    expect(find.textContaining('Completed'), findsOneWidget);
  });
}
