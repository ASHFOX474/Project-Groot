import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/private_api.dart';
import 'package:groot_app/goal_models.dart';
import 'package:groot_app/private_garden.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('live private account, passport, care and explicit deletion',
      (tester) async {
    final api = PrivateApi();
    final handle = 'smoke_${DateTime.now().millisecondsSinceEpoch}';
    final password = 'Local smoke ${DateTime.now().microsecondsSinceEpoch}!A';
    var created = false;
    var deleted = false;
    try {
      // Check the installed native bridge without activating a microphone/provider.
      await expectLater(
          const MethodChannel('bd.groot/goal_voice')
              .invokeMethod<String>('recognize', {'language': 'unsupported'}),
          throwsA(isA<PlatformException>()
              .having((e) => e.code, 'code', 'language')));
      await tester.pumpWidget(MaterialApp(home: PrivateGarden(api: api)));
      await tester.enterText(find.byType(TextFormField).at(0), handle);
      await tester.enterText(find.byType(TextFormField).at(1), password);
      await tester.ensureVisible(find.text('Create a new account'));
      await tester.tap(find.text('Create a new account'));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(find.text('Create account'), 200,
          scrollable: find.byType(Scrollable).first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Create account'));
      await tester.pumpAndSettle(const Duration(milliseconds: 100),
          EnginePhase.sendSemanticsUpdate, const Duration(seconds: 30));
      expect(find.text('Private garden · $handle'), findsOneWidget);
      created = true;
      await tester.tap(find.text('লক্ষ্য ও উপযুক্ত গাছ · Plan a goal'));
      await tester.pumpAndSettle();
      expect(find.text('লক্ষ্য ও উপযুক্ত গাছ'), findsOneWidget);
      await tester.enterText(
          find.byKey(const Key('goal-text')), 'আমার ছাদে সবজি চাই');
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('goal-precision')));
      await tester.tap(find.byKey(const Key('goal-precision')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('শুধু জেলা').last);
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('goal-district')));
      await tester.enterText(find.byKey(const Key('goal-district')), 'ঢাকা');
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('goal-submit')));
      await tester.tap(find.byKey(const Key('goal-submit')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('goal-result')));
      // The live demo must never be promoted just to make this test pass.
      expect(
          find.textContaining('এখনও অনুমোদিত উদ্ভিদ তথ্য নেই'), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await tester.tap(find.text('যত্ন পরিকল্পনা · Saved care plans'));
      await tester.pumpAndSettle();
      expect(find.textContaining('No saved plans.'), findsOneWidget);
      expect(await api.plans(), isEmpty);
      final preview = await api.previewPlan(
          GoalDraft(
              language: 'en',
              goal: 'Care preview',
              plantingDate:
                  bangladeshToday().toIso8601String().substring(0, 10)),
          'missing-reviewed-profile',
          4);
      expect(preview.status, 'blocked');
      expect(preview.steps, isEmpty);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await tester.tap(find.text('Add plant'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField).at(0), 'Emulator okra');
      await tester.enterText(find.byType(TextFormField).at(1), 'ঢেঁড়স');
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(find.text('Save passport'), 200,
          scrollable: find.byType(Scrollable).first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Save passport'));
      await tester.pumpAndSettle();
      expect(find.text('Emulator okra'), findsOneWidget);
      await tester.tap(find.text('Emulator okra'));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Log care'));
      await tester.tap(find.text('Log care'));
      await tester.pumpAndSettle();
      await tester.enterText(
          find.byType(TextField), 'Live emulator care check');
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Save care'));
      await tester.tap(find.text('Save care'));
      await tester.pumpAndSettle();
      expect(find.text('Live emulator care check'), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await tester.tap(find.text('Delete account'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField), password);
      await tester.tap(find.text('Delete permanently'));
      await tester.pumpAndSettle();
      expect(find.text('Sign in'), findsOneWidget);
      deleted = true;
    } finally {
      // Clean up only this randomly named account, never existing users/catalog.
      if (created && !deleted) {
        await api.signIn(handle, password);
        await api.deleteAccount(password);
      }
      api.close();
    }
  });
}
