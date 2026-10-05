import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/photo_checkins.dart';
import 'package:groot_app/private_api.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

final fixtureBytes = base64Decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=');

class FixturePicker implements PhotoPicker {
  Uint8List? bytes = fixtureBytes;
  int picks = 0, experts = 0;
  @override
  Future<Uint8List?> pick() async {
    picks++;
    return bytes;
  }

  @override
  Future<void> expert() async {
    experts++;
  }
}

const plant = PlantPassport(
    id: 'fixture-plant',
    nickname: 'Fixture plant',
    species: 'Fixture',
    plantedOn: '2026-01-01',
    conditions: {});
http.Response jsonResponse(Object data, [int status = 200]) =>
    http.Response(jsonEncode(data), status,
        headers: {'content-type': 'application/json; charset=utf-8'});
Map<String, dynamic> summary({Map<String, dynamic>? assistance}) => {
      'id': 'fixture-photo',
      'observed_on': '2026-10-05',
      'uploaded_at': '2026-10-05T00:00:00Z',
      'caption': 'Fixture caption',
      'width': 1,
      'height': 1,
      'symptoms': [],
      'assistance': assistance
    };

Future<void> visibleTap(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(finder, 200,
      scrollable: find.byType(Scrollable).first);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<PrivateApi> signedApi(
    Future<http.Response> Function(http.Request) handler) async {
  final api = PrivateApi(
      baseUrl: 'http://localhost:8000',
      client: MockClient((r) async {
        if (r.url.path.endsWith('login')) {
          return jsonResponse({
            'access_token': 'fixture-token',
            'account': {
              'id': 'fixture-owner',
              'handle': 'fixture',
              'choices': const ConsentChoices().toJson()
            }
          });
        }
        return handler(r);
      }));
  await api.signIn('fixture', 'fixture only passphrase');
  return api;
}

void main() {
  test('health assistance defaults to off independently of storage', () {
    final choices = PhotoConsent.fromJson({'storage': false, 'health': false});
    expect(choices.storage, false);
    expect(choices.health, false);
  });

  test(
      'photo operation IDs are random UUIDv4, not image content or credentials',
      () {
    final ids = List.generate(100, (_) => photoOperationId());
    expect(ids.toSet().length, 100);
    expect(
        ids.every((id) => RegExp(
                r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$')
            .hasMatch(id)),
        true);
  });

  testWidgets('storage is off by default and expert path does not upload',
      (tester) async {
    final picker = FixturePicker();
    final api = await signedApi((r) async =>
        r.url.path.endsWith('photo-consent')
            ? jsonResponse({'storage': false, 'health': false, 'generation': 0})
            : jsonResponse([]));
    await tester.pumpWidget(MaterialApp(
        home: PhotoCheckins(api: api, plant: plant, picker: picker)));
    await tester.pumpAndSettle();
    expect(find.text('Choose one photo'), findsNothing);
    await tester.tap(find.text('Expert help ·16123'));
    await tester.pumpAndSettle();
    expect(picker.picks, 0);
    expect(picker.experts, 1);
    await tester.pumpWidget(const SizedBox.shrink());
    api.close();
  });

  testWidgets('explicit photo opt-in, rights, upload and identical retry',
      (tester) async {
    var storage = false, posts = 0;
    final bodies = <Map<String, dynamic>>[];
    final picker = FixturePicker();
    final api = await signedApi((r) async {
      if (r.url.path.endsWith('photo-consent')) {
        if (r.method == 'PUT') {
          final body = jsonDecode(r.body) as Map;
          expect(body['health'], false);
          expect(body['notice_version'], '2026-10-05-photos-v1');
          storage = body['storage'] as bool;
        }
        return jsonResponse({
          'storage': storage,
          'health': false,
          'generation': storage ? 1 : 0
        });
      }
      if (r.method == 'POST') {
        bodies.add(jsonDecode(r.body) as Map<String, dynamic>);
        if (++posts == 1) throw const SocketException('lost response');
        return jsonResponse(summary(), 201);
      }
      return jsonResponse(posts > 1 ? [summary()] : []);
    });
    await tester.pumpWidget(MaterialApp(
        home: PhotoCheckins(api: api, plant: plant, picker: picker)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Photo choices'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byType(SwitchListTile).first);
    await tester.pumpAndSettle();
    await tester.tap(find.byType(SwitchListTile).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save choices'));
    await tester.pumpAndSettle();
    await visibleTap(tester, find.text('Choose one photo'));
    await tester.enterText(find.byType(TextField).last, 'নিজের ছবি');
    await visibleTap(tester, find.byType(CheckboxListTile));
    await visibleTap(tester, find.text('Upload private check-in'));
    await visibleTap(tester, find.text('Retry same check-in'));
    expect(posts, 2);
    expect(bodies[0], bodies[1]);
    expect(bodies[0]['symptoms'], isEmpty);
    expect(bodies[0]['rights_confirmed'], true);
    expect(bodies[0]['consent_generation'], 1);
    expect(bodies[0].keys, isNot(contains('owner_id')));
    expect(find.text('Retry same check-in'), findsNothing);
    await tester.pumpWidget(const SizedBox.shrink());
    api.close();
  });

  testWidgets('timeline uncertain flags, private image and confirmed deletion',
      (tester) async {
    var deleted = false;
    final health = {
      'message_en': 'Not a diagnosis',
      'message_bn': 'রোগ নির্ণয় নয়',
      'quality': 'retake',
      'urgent': true,
      'flags': [
        {
          'message_en': 'Possible discoloration',
          'message_bn': 'সম্ভাব্য রং পরিবর্তন',
          'basis': 'unvalidated heuristic'
        }
      ]
    };
    final api = await signedApi((r) async {
      if (r.url.path.endsWith('photo-consent')) {
        return jsonResponse(
            {'storage': false, 'health': false, 'generation': 0});
      }
      if (r.method == 'DELETE') {
        deleted = true;
        return http.Response('', 204);
      }
      if (r.url.path.endsWith('/image')) {
        return http.Response.bytes(fixtureBytes, 200,
            headers: {'content-type': 'image/jpeg'});
      }
      return jsonResponse(deleted ? [] : [summary(assistance: health)]);
    });
    await tester.pumpWidget(MaterialApp(
        home: PhotoCheckins(api: api, plant: plant, picker: FixturePicker())));
    await tester.pumpAndSettle();
    await visibleTap(tester, find.text('View private photo'));
    expect(find.byType(Image), findsOneWidget);
    await tester.scrollUntilVisible(
        find.text(
            'Possible observations · LOW / UNCALIBRATED · probability unavailable'),
        150,
        scrollable: find.byType(Scrollable).first);
    expect(find.text('Rapid decline reported: seek expert help promptly.'),
        findsOneWidget);
    await visibleTap(tester, find.text('Delete photo'));
    expect(deleted, false);
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    expect(deleted, true);
    expect(find.text('No private photo check-ins yet.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.close();
  });

  testWidgets(
      'cancelled picker does not enable upload and invalid date is blocked',
      (tester) async {
    var posts = 0;
    final picker = FixturePicker()..bytes = null;
    final api = await signedApi((r) async {
      if (r.method == 'POST') posts++;
      return r.url.path.endsWith('photo-consent')
          ? jsonResponse({'storage': true, 'health': false, 'generation': 1})
          : jsonResponse([]);
    });
    await tester.pumpWidget(MaterialApp(
        home: PhotoCheckins(api: api, plant: plant, picker: picker)));
    await tester.pumpAndSettle();
    await visibleTap(tester, find.text('Choose one photo'));
    expect(
        tester
            .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Upload private check-in'))
            .onPressed,
        isNull);
    picker.bytes = fixtureBytes;
    await visibleTap(tester, find.text('Choose one photo'));
    await tester.enterText(find.byType(TextField).first, '2099-01-01');
    await visibleTap(tester, find.byType(CheckboxListTile));
    await visibleTap(tester, find.text('Upload private check-in'));
    expect(posts, 0);
    await tester.drag(find.byType(ListView), const Offset(0, 1800));
    await tester.pumpAndSettle();
    expect(find.text('Use a valid photo date from planting through today.'),
        findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.close();
  });

  test('native bridge exposes only chosen image and fixed dialer action',
      () async {
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidPhotoPicker.channel, (call) async {
      calls.add(call);
      return call.method == 'pick' ? fixtureBytes : null;
    });
    final picker = AndroidPhotoPicker();
    expect(await picker.pick(), fixtureBytes);
    await picker.expert();
    expect(calls.map((c) => c.method), ['pick', 'expert']);
    expect(calls.every((c) => c.arguments == null), true);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidPhotoPicker.channel, null);
  });
}
