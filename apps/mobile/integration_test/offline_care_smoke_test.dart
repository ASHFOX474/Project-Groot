import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:groot_app/offline_care.dart';
import 'package:groot_app/offline_care_view.dart';
import 'package:groot_app/private_api.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class FixtureVault implements OfflineVault {
  String? value;
  @override
  Future<String?> unlock() async => value;
  @override
  Future<void> write(String data) async {
    value = data;
  }

  @override
  Future<void> lock() async {}
  @override
  Future<void> clear() async {
    value = null;
  }
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('offline UI care survives reopening then syncs exactly once',
      (tester) async {
    // Synthetic fixture only: no live database writes or advice approval.
    final vault = FixtureVault();
    final store = await OfflineCareStore.open(vault);
    await store.enable('fixture-owner', 'http://localhost:8000');
    await store.cachePassport({
      'id': 'fixture-plant',
      'nickname': 'Fixture plant',
      'species_name': 'Fixture only',
      'planted_on': '2026-01-01',
      'conditions': {}
    });
    var writes = 0;
    final api = PrivateApi(
        baseUrl: 'http://localhost:8000',
        client: MockClient((r) async {
          if (r.url.path.endsWith('login')) {
            return http.Response(
                jsonEncode({
                  'access_token': 'fixture-only-token',
                  'account': {
                    'id': 'fixture-owner',
                    'handle': 'fixture',
                    'choices': const ConsentChoices().toJson()
                  }
                }),
                200);
          }
          if (r.url.path.endsWith('/me')) {
            return http.Response('{"id":"fixture-owner"}', 200);
          }
          writes++;
          expect(jsonDecode(r.body)['request_id'], isA<String>());
          return http.Response('{"id":"fixture-event"}', 201);
        }));
    await tester
        .pumpWidget(MaterialApp(home: OfflineCareView(api: api, vault: vault)));
    await tester.tap(find.byKey(const Key('offline-unlock')));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Record care'));
    await tester.tap(find.text('Record care'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Fixture offline note');
    await tester.ensureVisible(find.text('Save care'));
    await tester.tap(find.text('Save care'));
    await tester.pumpAndSettle();
    expect(writes, 0);
    final reopened = await OfflineCareStore.open(vault);
    expect(reopened.pending, 1);
    await api.signIn('fixture', 'fixture only passphrase');
    await reopened.sync(api);
    await reopened.sync(api);
    expect(writes, 1);
    expect(reopened.operations.single['status'], 'synced');
    await tester.pumpWidget(const SizedBox.shrink());
    api.close();
    await tester.pumpAndSettle();
    // Real Android channel: no screen lock means no private notebook access.
    const native = MethodChannel('bd.groot/offline_care');
    await native.invokeMethod<void>('lock');
    final secure = await native.invokeMethod<bool>('secure');
    if (secure == false) {
      await expectLater(native.invokeMethod<String>('unlock'),
          throwsA(isA<PlatformException>()));
    }
    await expectLater(native.invokeMethod<void>('write', '{}'),
        throwsA(isA<PlatformException>()));
  });
}
