import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:groot_app/photo_checkins.dart';
import 'package:http/http.dart' as http;
import '../test/photo_checkins_test.dart' as fixture;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
      'private photo upload timeline and image with synthetic HTTP/picker',
      (tester) async {
    var uploaded = false;
    final api = await fixture.signedApi((r) async {
      if (r.url.path.endsWith('photo-consent')) {
        return fixture
            .jsonResponse({'storage': true, 'health': false, 'generation': 1});
      }
      if (r.method == 'POST') {
        uploaded = true;
        return fixture.jsonResponse(fixture.summary(), 201);
      }
      if (r.url.path.endsWith('/image')) {
        return http.Response.bytes(fixture.fixtureBytes, 200,
            headers: {'content-type': 'image/jpeg'});
      }
      return fixture.jsonResponse(uploaded ? [fixture.summary()] : []);
    });
    await tester.pumpWidget(MaterialApp(
        home: PhotoCheckins(
            api: api, plant: fixture.plant, picker: fixture.FixturePicker())));
    await tester.pumpAndSettle();
    await fixture.visibleTap(tester, find.text('Choose one photo'));
    await fixture.visibleTap(tester, find.byType(CheckboxListTile));
    await fixture.visibleTap(tester, find.text('Upload private check-in'));
    expect(uploaded, true);
    await fixture.visibleTap(tester, find.text('View private photo'));
    expect(find.byType(Image), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.close();
  });
  testWidgets(
      'real Android picker cancellation grants no image or library access',
      (tester) async {
    // The runner must press Back only after confirming the system picker is open.
    // No real user photo is selected, uploaded or deleted by this smoke test.
    await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: Text('Cancel the system photo picker'))));
    const native = MethodChannel('bd.groot/photos');
    final result = await native
        .invokeMethod<Uint8List>('pick')
        .timeout(const Duration(seconds: 45));
    expect(result, isNull);
  });
}
