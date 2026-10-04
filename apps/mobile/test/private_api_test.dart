import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/private_api.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('session is sent only as a bearer header and cleared on logout',
      () async {
    var requests = 0;
    final api = PrivateApi(
        baseUrl: 'http://localhost:8000',
        client: MockClient((request) async {
          requests++;
          expect(request.url.query.contains('token'), isFalse);
          if (request.url.path.endsWith('register')) {
            final body = jsonDecode(request.body) as Map<String, dynamic>;
            expect(body['notice_version'], privacyNoticeVersion);
            expect((body['choices'] as Map).values, everyElement(false));
            expect(request.headers.containsKey('Authorization'), isFalse);
            return http.Response(
                jsonEncode({
                  'access_token': 'a' * 43,
                  'account': {
                    'handle': 'grower',
                    'choices': const ConsentChoices().toJson(),
                  }
                }),
                201);
          }
          if (requests == 2) {
            expect(request.headers['Authorization'], 'Bearer ${'a' * 43}');
            return http.Response('', 204);
          }
          expect(request.headers.containsKey('Authorization'), isFalse);
          return http.Response('[]', 200);
        }));
    await api.signIn('grower', 'a long private password', register: true);
    await api.logout();
    expect(await api.plants(), isEmpty);
    api.close();
  });

  test('errors never display server body or sensitive request content',
      () async {
    final api = PrivateApi(
        client:
            MockClient((_) async => http.Response('secret server stack', 503)));
    try {
      await api.signIn('grower', 'a private passphrase');
      fail('Expected error');
    } on PrivateApiException catch (e) {
      expect(e.message, isNot(contains('secret')));
    }
    api.close();
  });

  test('401 reports expired sign-in and preserves no local bearer', () async {
    var index = 0;
    final api = PrivateApi(client: MockClient((request) async {
      index++;
      if (index == 1) {
        return http.Response(
            jsonEncode({
              'access_token': 'b' * 43,
              'account': {
                'handle': 'grower',
                'choices': const ConsentChoices().toJson()
              }
            }),
            200);
      }
      if (index == 3) {
        expect(request.headers.containsKey('Authorization'), isFalse);
      }
      return http.Response('{}', 401);
    }));
    await api.signIn('grower', 'a long private passphrase');
    for (var i = 0; i < 2; i++) {
      try {
        await api.plants();
        fail('Expected error');
      } on PrivateApiException catch (e) {
        expect(e.signedOut, isTrue);
      }
    }
    api.close();
  });
}
