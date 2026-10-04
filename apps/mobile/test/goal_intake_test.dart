import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/goal_intake.dart';
import 'package:groot_app/goal_models.dart';
import 'package:groot_app/goal_voice.dart';
import 'package:groot_app/private_api.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

Map<String, dynamic> contract() =>
    jsonDecode(File('../../services/api/tests/fixtures/goal_contract.json')
        .readAsStringSync()) as Map<String, dynamic>;

class GoalApi extends PrivateApi {
  GoalDraft? submitted;
  bool expired = false;
  Map<String, dynamic> response =
      contract()['empty_response'] as Map<String, dynamic>;
  @override
  Future<GoalAssessment> recommend(GoalDraft goal) async {
    if (expired) {
      throw const PrivateApiException('Sign in again', signedOut: true);
    }
    submitted = goal;
    return GoalAssessment(response);
  }
}

class Voice extends GoalVoice {
  String? transcript = 'আমার ছাদে সবজি চাই';
  String? language;
  bool unavailable = false;
  @override
  Future<String?> transcribe(String language) async {
    this.language = language;
    if (unavailable) throw PlatformException(code: 'unavailable');
    return transcript;
  }
}

Future<void> reveal(WidgetTester tester, String key) async {
  FocusManager.instance.primaryFocus?.unfocus();
  await tester.pumpAndSettle();
  await tester.ensureVisible(find.byKey(Key(key)));
  await tester.pumpAndSettle();
}

Future<void> choose(WidgetTester tester, String key, String value) async {
  await reveal(tester, key);
  await tester.tap(find.byKey(Key(key)));
  await tester.pumpAndSettle();
  await tester.tap(find.text(value).last);
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  WidgetController.hitTestWarningShouldBeFatal = true;
  test('shared API contract, Bangla digits and chosen location only', () {
    const draft = GoalDraft(
        language: 'en',
        goal: 'Grow crops / ফসল চাষ',
        category: 'crop',
        precision: 'district',
        district: 'Dhaka',
        context: 'open_ground',
        area: 2,
        sunlight: 'full_sun',
        description: 'Self-reported soil',
        ph: 6.5,
        texture: 'loam',
        drainage: 'well_drained',
        plantingDate: '2026-10-04',
        temperature: 25);
    expect(draft.toJson(), contract()['request']);
    expect(
        GoalAssessment(contract()['empty_response'] as Map<String, dynamic>)
            .plants,
        isEmpty);
    expect(
        const GoalDraft(
                language: 'bn',
                goal: 'সবজি',
                district: 'Dhaka',
                plantingDate: '2026-10-04')
            .toJson()['location'],
        {'precision': 'none'});
    expect(
        const GoalDraft(
                language: 'en',
                goal: 'Trees',
                precision: 'country',
                district: 'Dhaka',
                plantingDate: '2026-10-04')
            .toJson()['location'],
        {'precision': 'country', 'country_code': 'BD'});
    expect(goalNumber(' ৬.৫ '), 6.5);
    expect(goalNumber('জানি না'), isNull);
  });

  test(
      'goal POST uses bearer and clears expired session without echoing errors',
      () async {
    var calls = 0;
    final api = PrivateApi(client: MockClient((request) async {
      calls++;
      if (calls == 1) {
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
      expect(request.url.path, '/v1/goals/recommendations');
      expect(request.url.query, isEmpty);
      expect(request.method, 'POST');
      if (calls <= 3) {
        expect(request.headers['Authorization'], 'Bearer ${'c' * 43}');
      }
      if (calls == 2) {
        expect((jsonDecode(request.body) as Map)['location'],
            {'precision': 'none'});
        return http.Response(jsonEncode(contract()['empty_response']), 200);
      }
      if (calls == 4) {
        expect(request.headers.containsKey('Authorization'), isFalse);
      }
      return http.Response('private goal and server secret', 401);
    }));
    await api.signIn('grower', 'a long private passphrase');
    const draft =
        GoalDraft(language: 'en', goal: 'Trees', plantingDate: '2026-10-04');
    expect((await api.recommend(draft)).status, 'no_reviewed_data');
    for (var n = 0; n < 2; n++) {
      try {
        await api.recommend(draft);
        fail('Expected expiry');
      } on PrivateApiException catch (e) {
        expect(e.signedOut, isTrue);
        expect(e.message, isNot(contains('secret')));
      }
    }
    api.close();
  });

  test(
      'native voice channel uses chosen language and handles cancellation/unavailability',
      () async {
    const channel = MethodChannel('bd.groot/goal_voice');
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    addTearDown(() => messenger.setMockMethodCallHandler(channel, null));
    messenger.setMockMethodCallHandler(channel, (call) async {
      expect(call.method, 'recognize');
      expect(call.arguments, {'language': 'bn'});
      return 'সবজি চাই';
    });
    expect(await GoalVoice().transcribe('bn'), 'সবজি চাই');
    messenger.setMockMethodCallHandler(channel, (_) async => null);
    expect(await GoalVoice().transcribe('en'), isNull);
    messenger.setMockMethodCallHandler(
        channel, (_) async => throw PlatformException(code: 'unavailable'));
    await expectLater(
        GoalVoice().transcribe('en'), throwsA(isA<PlatformException>()));
  });

  testWidgets(
      'bilingual form, district downgrade removes detail and stale results',
      (tester) async {
    final api = GoalApi();
    addTearDown(api.close);
    await tester.pumpWidget(MaterialApp(home: GoalIntake(api: api)));
    expect(find.text('লক্ষ্য ও উপযুক্ত গাছ'), findsOneWidget);
    await choose(tester, 'goal-language', 'English');
    await tester.enterText(
        find.byKey(const Key('goal-text')), 'Grow vegetables');
    await choose(tester, 'goal-precision', 'District only');
    await reveal(tester, 'goal-district');
    await tester.enterText(find.byKey(const Key('goal-district')), 'Dhaka');
    await reveal(tester, 'goal-area');
    await tester.enterText(find.byKey(const Key('goal-area')), '২');
    await reveal(tester, 'goal-submit');
    await tester.tap(find.byKey(const Key('goal-submit')));
    await tester.pumpAndSettle();
    expect(api.submitted!.district, 'Dhaka');
    expect(api.submitted!.area, 2);
    await reveal(tester, 'goal-result');
    expect(find.textContaining('No approved plant profiles'), findsOneWidget);
    await choose(tester, 'goal-precision', 'Bangladesh only');
    expect(find.byKey(const Key('goal-result')), findsNothing);
    expect(find.byKey(const Key('goal-district')), findsNothing);
    await reveal(tester, 'goal-submit');
    await tester.tap(find.byKey(const Key('goal-submit')));
    await tester.pumpAndSettle();
    expect(api.submitted!.toJson()['location'],
        {'precision': 'country', 'country_code': 'BD'});
  });

  testWidgets('required goal and invalid numbers block submission',
      (tester) async {
    final api = GoalApi();
    addTearDown(api.close);
    await tester.pumpWidget(MaterialApp(home: GoalIntake(api: api)));
    await choose(tester, 'goal-language', 'English');
    await reveal(tester, 'goal-submit');
    await tester.tap(find.byKey(const Key('goal-submit')));
    await tester.pumpAndSettle();
    expect(api.submitted, isNull);
    await reveal(tester, 'goal-text');
    await tester.enterText(find.byKey(const Key('goal-text')), 'Grow food');
    await reveal(tester, 'goal-area');
    await tester.enterText(find.byKey(const Key('goal-area')), 'NaN');
    await reveal(tester, 'goal-ph');
    await tester.enterText(find.byKey(const Key('goal-ph')), '15');
    await reveal(tester, 'goal-submit');
    await tester.tap(find.byKey(const Key('goal-submit')));
    await tester.pumpAndSettle();
    expect(api.submitted, isNull);
  });

  testWidgets(
      'voice notice, editable transcript, cancelled/unavailable typing fallback',
      (tester) async {
    final api = GoalApi();
    final voice = Voice();
    addTearDown(api.close);
    await tester
        .pumpWidget(MaterialApp(home: GoalIntake(api: api, voice: voice)));
    await tester.tap(find.byKey(const Key('goal-voice')));
    await tester.pumpAndSettle();
    expect(find.textContaining('অনলাইনে'), findsOneWidget);
    expect(voice.language, isNull);
    await tester.tap(find.text('বাতিল'));
    await tester.pumpAndSettle();
    expect(voice.language, isNull);
    await tester.tap(find.byKey(const Key('goal-voice')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('চালিয়ে যান'));
    await tester.pumpAndSettle();
    expect(voice.language, 'bn');
    expect(api.submitted, isNull);
    expect(
        tester
            .widget<TextFormField>(find.byKey(const Key('goal-text')))
            .controller!
            .text,
        voice.transcript);
    await tester.enterText(
        find.byKey(const Key('goal-text')), 'আমার সম্পাদিত লক্ষ্য');
    voice.transcript = null;
    await tester.tap(find.byKey(const Key('goal-voice')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('চালিয়ে যান'));
    await tester.pumpAndSettle();
    expect(
        tester
            .widget<TextFormField>(find.byKey(const Key('goal-text')))
            .controller!
            .text,
        'আমার সম্পাদিত লক্ষ্য');
    voice.unavailable = true;
    await tester.tap(find.byKey(const Key('goal-voice')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('চালিয়ে যান'));
    await tester.pumpAndSettle();
    await reveal(tester, 'goal-submit');
    expect(find.textContaining('ভয়েস পাওয়া যাচ্ছে না'), findsOneWidget);
    expect(api.submitted, isNull);
  });

  testWidgets(
      'results show reasons, uncertainty, review dates and source evidence',
      (tester) async {
    final api = GoalApi();
    addTearDown(api.close);
    api.response = {
      ...api.response,
      'recommendations': [
        {
          'species_id': 'test-plant',
          'profile_id': 'test-profile',
          'common_name_bn': 'পরীক্ষা',
          'common_name_en': 'Test plant',
          'variety': 'Test variety',
          'assessment': 'needs_confirmation',
          'reasons': ['Sunlight matches'],
          'uncertainties': ['Measured pH needed'],
          'reviewed_at': '2026-10-04',
          'valid_until': '2027-10-04',
          'limitations': 'Test evidence only',
          'sources': [
            {
              'key': 'sunlight',
              'source_title': 'Test source',
              'source_url': 'https://example.org/source',
              'source_locator': 'Table 1',
              'interpretation_note': 'Synthetic fixture',
              'checked_at': '2026-10-04',
              'valid_until': '2027-10-04',
              'license_name': 'CC0',
              'license_url':
                  'https://creativecommons.org/publicdomain/zero/1.0/',
              'attribution': 'Test author'
            }
          ]
        }
      ]
    };
    await tester.pumpWidget(MaterialApp(home: GoalIntake(api: api)));
    await choose(tester, 'goal-language', 'English');
    await tester.enterText(find.byKey(const Key('goal-text')), 'Grow food');
    await reveal(tester, 'goal-submit');
    await tester.tap(find.byKey(const Key('goal-submit')));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Sources and citations'), 220,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    expect(find.textContaining('Needs confirmation'), findsOneWidget);
    expect(find.text('✓ Sunlight matches'), findsOneWidget);
    expect(find.text('• Measured pH needed'), findsOneWidget);
    await tester.tap(find.text('Sources and citations'));
    await tester.pumpAndSettle();
    expect(find.text('https://example.org/source'), findsOneWidget);
  });

  testWidgets(
      'expired session exits goal screen and notifies the private garden',
      (tester) async {
    final api = GoalApi()..expired = true;
    addTearDown(api.close);
    bool? expired;
    await tester.pumpWidget(MaterialApp(
        home: Builder(
            builder: (context) => Scaffold(
                body: TextButton(
                    onPressed: () async {
                      expired = await Navigator.of(context).push<bool>(
                          MaterialPageRoute(
                              builder: (_) => GoalIntake(api: api)));
                    },
                    child: const Text('Open goal'))))));
    await tester.tap(find.text('Open goal'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('goal-text')), 'গাছ লাগাব');
    await reveal(tester, 'goal-submit');
    await tester.tap(find.byKey(const Key('goal-submit')));
    await tester.pumpAndSettle();
    expect(expired, isTrue);
    expect(find.text('Open goal'), findsOneWidget);
    expect(find.byKey(const Key('goal-text')), findsNothing);
  });
}
