import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/offline_care.dart';
import 'package:groot_app/private_api.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:flutter/material.dart';
import 'package:groot_app/offline_care_view.dart';

class MemoryVault implements OfflineVault {
  String? value;
  bool failWrites = false;
  @override
  Future<String?> unlock() async => value;
  @override
  Future<void> write(String data) async {
    if (failWrites) throw StateError('disk full');
    value = data;
  }

  @override
  Future<void> clear() async {
    value = null;
  }

  @override
  Future<void> lock() async {}
}

Map<String, dynamic> passport = {
  'id': 'plant',
  'nickname': 'Fixture',
  'species_name': 'Fixture',
  'species_id': null,
  'planted_on': '2026-01-01',
  'conditions': {
    'growing_context': 'container',
    'soil': 'Unknown',
    'sunlight': 'unknown'
  }
};

Future<OfflineCareStore> notebook(MemoryVault vault) async {
  final store = await OfflineCareStore.open(vault);
  await store.enable('owner', 'http://localhost:8000');
  await store.cachePassport(passport);
  return store;
}

PrivateApi api(MockClient client) =>
    PrivateApi(client: client, baseUrl: 'http://localhost:8000');
http.Response login() => http.Response(
    jsonEncode({
      'access_token': 'fixture-bearer',
      'account': {
        'id': 'owner',
        'handle': 'fixture',
        'choices': const ConsentChoices().toJson()
      }
    }),
    200);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('care is durable before sync and restart preserves operation ID',
      () async {
    final vault = MemoryVault();
    final store = await notebook(vault);
    await store.enqueueCare('plant', 'observation', '2026-10-05', 'নিজের যত্ন');
    final reopened = await OfflineCareStore.open(vault);
    expect(reopened.operations.single['request_id'],
        store.operations.single['request_id']);
    expect(reopened.operations.single['status'], 'pending');
    expect(vault.value, isNot(contains('fixture-bearer')));
  });

  test(
      'lost response retries identical operation and never acknowledges failure',
      () async {
    final store = await notebook(MemoryVault());
    await store.enqueueCare('plant', 'observation', '2026-10-05', 'note');
    final ids = <String>[];
    var calls = 0;
    final client = api(MockClient((r) async {
      if (r.url.path.endsWith('login')) return login();
      if (r.url.path.endsWith('/me')) {
        return http.Response('{"id":"owner"}', 200);
      }
      ids.add((jsonDecode(r.body) as Map)['request_id'] as String);
      if (++calls == 1) throw const SocketException('lost response');
      return http.Response('{"id":"server-event"}', 201);
    }));
    await client.signIn('fixture', 'test password only');
    await store.sync(client);
    expect(store.operations.single['status'], 'pending');
    await store.sync(client);
    expect(store.operations.single['status'], 'synced');
    await store.sync(client);
    expect(ids.length, 2);
    expect(ids[0], ids[1]);
    client.close();
  });

  test(
      'changed account never sends pending care and HTTP conflicts need review',
      () async {
    final store = await notebook(MemoryVault());
    await store.enqueueCare('plant', 'watering', '2026-10-05', 'note');
    var owner = 'other', posts = 0;
    final client = api(MockClient((r) async {
      if (r.url.path.endsWith('login')) return login();
      if (r.url.path.endsWith('/me')) {
        return http.Response(jsonEncode({'id': owner}), 200);
      }
      posts++;
      return http.Response('{}', 404);
    }));
    await client.signIn('fixture', 'test password only');
    await expectLater(store.sync(client), throwsA(isA<OfflineCareException>()));
    expect(posts, 0);
    owner = 'owner';
    await store.sync(client);
    expect(store.operations.single['status'], 'needs_review');
    await store.sync(client);
    expect(posts, 1);
    client.close();
  });

  test('failed durable write does not claim the care was saved', () async {
    final vault = MemoryVault();
    final store = await notebook(vault);
    vault.failWrites = true;
    await expectLater(store.enqueueCare('plant', 'watering', '2026-10-05', ''),
        throwsStateError);
    expect(store.operations, isEmpty);
  });

  test('simultaneous local entries are not lost', () async {
    final store = await notebook(MemoryVault());
    await Future.wait(List.generate(10,
        (i) => store.enqueueCare('plant', 'observation', '2026-10-05', '$i')));
    expect(store.operations.length, 10);
    expect(store.operations.map((x) => x['request_id']).toSet().length, 10);
  });

  test('late sync after locking cannot overwrite a reopened notebook',
      () async {
    final vault = MemoryVault();
    final store = await notebook(vault);
    await store.enqueueCare('plant', 'observation', '2026-10-05', 'first');
    final entered = Completer<void>();
    final response = Completer<http.Response>();
    final client = api(MockClient((r) async {
      if (r.url.path.endsWith('login')) return login();
      if (r.url.path.endsWith('/me')) {
        return http.Response('{"id":"owner"}', 200);
      }
      entered.complete();
      return response.future;
    }));
    await client.signIn('fixture', 'test password only');
    final syncing = store.sync(client);
    await entered.future;
    final closing = store.lock();
    final reopened = await OfflineCareStore.open(vault);
    await reopened.enqueueCare('plant', 'observation', '2026-10-05', 'second');
    final interrupted =
        expectLater(syncing, throwsA(isA<OfflineCareException>()));
    response.complete(http.Response('{"id":"server-event"}', 201));
    await interrupted;
    await closing;
    final finalStore = await OfflineCareStore.open(vault);
    expect(finalStore.pending, 2);
    expect(finalStore.operations.map((o) => o['note']), ['first', 'second']);
    client.close();
  });

  test('pending entries cannot be removed through the reviewed-record action',
      () async {
    final store = await notebook(MemoryVault());
    await store.enqueueCare('plant', 'observation', '2026-10-05', 'note');
    await expectLater(
        store.removeOperation(store.operations.single['request_id'] as String),
        throwsA(isA<OfflineCareException>()));
    expect(store.pending, 1);
  });

  test(
      'offline advice keeps citations but withholds expired or old instructions',
      () {
    final preview = jsonDecode(
        File('../../services/api/tests/fixtures/care_contract.json')
            .readAsStringSync()) as Map<String, dynamic>;
    final raw = {
      'plan_id': 'fixture',
      'version': 1,
      'availability': 'current',
      'plan': preview
    };
    final now = DateTime.utc(2026, 10, 5, 12);
    final cached = {'checked_at': now.toIso8601String(), 'snapshot': raw};
    expect(offlinePlan(cached, now)['plan']['instructions'], isNotEmpty);
    expect(
        offlinePlan(cached, now.add(const Duration(days: 2)))['plan']
            ['instructions'],
        isEmpty);
    preview['valid_until'] = '2026-10-04';
    expect(offlinePlan(cached, now)['plan']['instructions'], isEmpty);
    expect(offlinePlan(cached, now)['plan']['condition_sources'],
        preview['condition_sources']);
  });

  test(
      'invalid dates, unknown plants, actions and oversized notes stay out of queue',
      () async {
    final store = await notebook(MemoryVault());
    for (final args in [
      ['missing', 'watering', '2026-10-05', ''],
      ['plant', 'watering', '2025-12-31', ''],
      ['plant', 'watering', '2026-02-30', ''],
      ['plant', 'watering', '2099-01-01', ''],
      ['plant', 'pesticide', '2026-10-05', ''],
      ['plant', 'watering', '2026-10-05', 'x' * 1001],
      ['plant', 'watering', '2026-10-05', '\u0000'],
    ]) {
      await expectLater(store.enqueueCare(args[0], args[1], args[2], args[3]),
          throwsA(isA<OfflineCareException>()));
    }
    expect(store.operations, isEmpty);
  });

  test('queue limits preserve pending records instead of evicting them',
      () async {
    final vault = MemoryVault();
    await notebook(vault);
    final raw = jsonDecode(vault.value!) as Map<String, dynamic>;
    raw['operations'] =
        List.generate(500, (i) => {'request_id': '$i', 'status': 'pending'});
    vault.value = jsonEncode(raw);
    final store = await OfflineCareStore.open(vault);
    await expectLater(store.enqueueCare('plant', 'watering', '2026-10-05', ''),
        throwsA(isA<OfflineCareException>()));
    expect(store.operations.length, 500);
  });

  test(
      'clearing and locking remove in-memory access but only clear erases durable data',
      () async {
    final vault = MemoryVault();
    final store = await notebook(vault);
    await store.enqueueCare('plant', 'observation', '2026-10-05', 'note');
    await store.lock();
    expect(store.enabled, isFalse);
    final reopened = await OfflineCareStore.open(vault);
    expect(reopened.operations.length, 1);
    await reopened.clear();
    expect(vault.value, isNull);
    expect(reopened.operations, isEmpty);
  });

  test('cannot bind another owner or server without explicit erasure',
      () async {
    final store = await notebook(MemoryVault());
    for (final pair in [
      ['other', 'http://localhost:8000'],
      ['owner', 'https://other.example']
    ]) {
      await expectLater(
          store.enable(pair[0], pair[1]), throwsA(isA<OfflineCareException>()));
    }
    expect(store.owner, 'owner');
  });

  for (final status in [409, 422, 401, 429, 503]) {
    test('HTTP $status is never falsely acknowledged or auto-overwritten',
        () async {
      final store = await notebook(MemoryVault());
      await store.enqueueCare('plant', 'observation', '2026-10-05', 'note');
      final client = api(MockClient((r) async {
        if (r.url.path.endsWith('login')) return login();
        if (r.url.path.endsWith('/me')) {
          return http.Response('{"id":"owner"}', 200);
        }
        return http.Response('{}', status);
      }));
      await client.signIn('fixture', 'test password only');
      if ([409, 422].contains(status)) {
        await store.sync(client);
        expect(store.operations.single['status'], 'needs_review');
      } else {
        await expectLater(
            store.sync(client), throwsA(isA<PrivateApiException>()));
        expect(store.operations.single['status'], 'pending');
      }
      client.close();
    });
  }

  test('acknowledgment disk failure replays the same ID after reopening',
      () async {
    final vault = MemoryVault();
    final store = await notebook(vault);
    await store.enqueueCare('plant', 'observation', '2026-10-05', 'note');
    final ids = <String>[];
    final client = api(MockClient((r) async {
      if (r.url.path.endsWith('login')) return login();
      if (r.url.path.endsWith('/me')) {
        return http.Response('{"id":"owner"}', 200);
      }
      ids.add((jsonDecode(r.body) as Map)['request_id'] as String);
      return http.Response('{"id":"same-server-event"}', 201);
    }));
    await client.signIn('fixture', 'test password only');
    vault.failWrites = true;
    await expectLater(store.sync(client), throwsStateError);
    final reopened = await OfflineCareStore.open(vault);
    vault.failWrites = false;
    await reopened.sync(client);
    expect(ids[0], ids[1]);
    expect(reopened.operations.single['status'], 'synced');
    client.close();
  });

  test('download commits complete owner-scoped inventory and handles deletion',
      () async {
    final store = await notebook(MemoryVault());
    await store.enqueueCare('plant', 'observation', '2026-10-05', 'note');
    final client = api(MockClient((r) async {
      if (r.url.path.endsWith('login')) return login();
      if (r.url.path.endsWith('/me')) {
        return http.Response('{"id":"owner"}', 200);
      }
      return http.Response(
          '[]', 200); // Complete inventory: cached plant deleted remotely.
    }));
    await client.signIn('fixture', 'test password only');
    await store.download(client);
    expect(store.passports, isEmpty);
    expect(store.operations.single['status'], 'needs_review');
    client.close();
  });

  test('failed download does not replace existing notebook', () async {
    final store = await notebook(MemoryVault());
    final client = api(MockClient((r) async {
      if (r.url.path.endsWith('login')) return login();
      if (r.url.path.endsWith('/me')) {
        return http.Response('{"id":"owner"}', 200);
      }
      throw const SocketException('offline');
    }));
    await client.signIn('fixture', 'test password only');
    await expectLater(store.download(client), throwsA(isA<SocketException>()));
    expect(store.passports.single['id'], 'plant');
    client.close();
  });

  testWidgets('offline notebook can record care without any network request',
      (tester) async {
    final vault = MemoryVault();
    await notebook(vault);
    final client = api(MockClient((_) async {
      fail('Offline mode must not contact server');
    }));
    await tester.pumpWidget(
        MaterialApp(home: OfflineCareView(api: client, vault: vault)));
    await tester.tap(find.byKey(const Key('offline-unlock')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Offline access only'), findsOneWidget);
    await tester.ensureVisible(find.text('Record care'));
    await tester.tap(find.text('Record care'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Offline widget note');
    await tester.ensureVisible(find.text('Save care'));
    await tester.tap(find.text('Save care'));
    await tester.pumpAndSettle();
    expect((await OfflineCareStore.open(vault)).operations.single['note'],
        'Offline widget note');
    await tester.pumpWidget(const SizedBox.shrink());
    client.close();
    await tester.pumpAndSettle();
  });

  testWidgets(
      'explicit opt-in downloads plans with citations, syncs and erases only local copies',
      (tester) async {
    final vault = MemoryVault();
    final preview = jsonDecode(
        File('../../services/api/tests/fixtures/care_contract.json')
            .readAsStringSync()) as Map<String, dynamic>;
    var writes = 0;
    final client = api(MockClient((r) async {
      if (r.url.path.endsWith('login')) return login();
      if (r.url.path.endsWith('/me')) {
        return http.Response('{"id":"owner"}', 200);
      }
      if (r.url.path.endsWith('/passports')) {
        return http.Response(jsonEncode([passport]), 200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }
      if (r.url.path.endsWith('/plans')) {
        return http.Response(
            jsonEncode([
              {
                'id': 'plan',
                'latest_version': 1,
                'common_name_bn': 'পরীক্ষার গাছ',
                'common_name_en': 'Test plant',
                'status': 'partial'
              }
            ]),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }
      if (r.url.path.endsWith('/plans/plan')) {
        return http.Response(
            jsonEncode({
              'plan_id': 'plan',
              'version': 1,
              'availability': 'current',
              'plan': preview
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }
      writes++;
      return http.Response('{"id":"event"}', 201);
    }));
    await client.signIn('fixture', 'test password only');
    await tester.pumpWidget(
        MaterialApp(home: OfflineCareView(api: client, vault: vault)));
    await tester.tap(find.byKey(const Key('offline-unlock')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enable offline care'));
    await tester.pumpAndSettle();
    expect(find.textContaining('No password/token'), findsOneWidget);
    await tester.tap(find.text('Enable'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Download / refresh plans and plants'));
    await tester.pumpAndSettle();
    expect((await OfflineCareStore.open(vault)).plans.length, 1);
    await tester.scrollUntilVisible(find.text('পরীক্ষার গাছ · Test plant'), 150,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('পরীক্ষার গাছ · Test plant'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Synthetic reviewed instruction only'),
        findsOneWidget);
    expect(find.textContaining('Synthetic care source'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Record care'), 200,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Record care'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Save care'));
    await tester.tap(find.text('Save care'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.byKey(const Key('offline-sync')), -200,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('offline-sync')));
    await tester.pumpAndSettle();
    expect(writes, 1);
    await tester.scrollUntilVisible(
        find.textContaining('watering · synced'), 200,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    expect(find.textContaining('watering · synced'), findsOneWidget);
    await tester.scrollUntilVisible(
        find.text('Disable and erase local notebook'), 200,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Disable and erase local notebook'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    expect(vault.value, isNull);
    expect(writes, 1);
    await tester.pumpWidget(const SizedBox.shrink());
    client.close();
    await tester.pumpAndSettle();
  });

  testWidgets(
      'five-minute device timeout hides decrypted records and requires unlock',
      (tester) async {
    final vault = MemoryVault();
    await notebook(vault);
    final client = api(MockClient((_) async {
      fail('Offline mode');
    }));
    await tester.pumpWidget(
        MaterialApp(home: OfflineCareView(api: client, vault: vault)));
    await tester.tap(find.byKey(const Key('offline-unlock')));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(minutes: 5));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('offline-unlock')), findsOneWidget);
    expect(
        find.textContaining('Device authentication expired'), findsOneWidget);
    expect(vault.value, isNotNull);
    await tester.pumpWidget(const SizedBox.shrink());
    client.close();
  });

  testWidgets('different signed-in owner sees no offline plant data',
      (tester) async {
    final vault = MemoryVault();
    await notebook(vault);
    final client = api(MockClient((_) async => http.Response(
        jsonEncode({
          'access_token': 'fixture',
          'account': {
            'id': 'other',
            'handle': 'other',
            'choices': const ConsentChoices().toJson()
          }
        }),
        200)));
    await client.signIn('other', 'fixture only passphrase');
    await tester.pumpWidget(
        MaterialApp(home: OfflineCareView(api: client, vault: vault)));
    await tester.tap(find.byKey(const Key('offline-unlock')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Notebook belongs to another'), findsOneWidget);
    expect(find.text('Fixture'), findsNothing);
    await tester.pumpWidget(const SizedBox.shrink());
    client.close();
  });

  test(
      'Android bridge only sends notebook data and supports explicit lock/erase',
      () async {
    final methods = <String>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidOfflineVault.channel, (call) async {
      methods.add(call.method);
      if (call.method == 'unlock') return 'fixture';
      if (call.method == 'write') expect(call.arguments, '{}');
      return null;
    });
    final vault = AndroidOfflineVault();
    expect(await vault.unlock(), 'fixture');
    await vault.write('{}');
    await vault.clear();
    await vault.lock();
    expect(methods, ['unlock', 'write', 'clear', 'lock']);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidOfflineVault.channel, null);
  });
}
