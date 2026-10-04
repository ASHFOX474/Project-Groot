import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/main.dart' as app;
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('seeded demo catalog loads through the live API', (tester) async {
    app.main();
    // Bound the wait so an unavailable API fails instead of hanging CI forever.
    for (var attempt = 0; attempt < 30; attempt++) {
      await tester.pump(const Duration(seconds: 1));
      if (find.text('নিম · Neem').evaluate().isNotEmpty) break;
    }
    expect(find.text('Groot'), findsOneWidget);
    // Optional research imports may contain the same names. Verify the demo
    // tiles specifically instead of assuming names are globally unique.
    final demoTiles =
        find.ancestor(of: find.text('Demo'), matching: find.byType(ListTile));
    expect(find.descendant(of: demoTiles, matching: find.text('নিম · Neem')),
        findsOneWidget);
    expect(find.descendant(of: demoTiles, matching: find.text('ঢেঁড়স · Okra')),
        findsOneWidget);
    expect(find.text('Demo'), findsNWidgets(2));
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });
}
