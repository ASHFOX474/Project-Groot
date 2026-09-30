import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/catalog.dart';
import 'package:groot_app/main.dart';

class EmptyCatalogClient extends CatalogClient {
  @override
  Future<List<Species>> getSpecies() async => [];

  @override
  void close() {}
}

void main() {
  testWidgets('Groot starter labels demo data honestly', (tester) async {
    await tester.pumpWidget(GrootApp(catalog: EmptyCatalogClient()));
    await tester.pumpAndSettle();

    expect(find.text('Groot'), findsOneWidget);
    expect(find.textContaining('not planting recommendations'), findsOneWidget);
    expect(find.text('No plants in the catalog yet.'), findsOneWidget);
  });
}
