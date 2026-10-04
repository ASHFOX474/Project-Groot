import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/private_api.dart';
import 'package:groot_app/private_garden.dart';

class FakePrivateApi extends PrivateApi {
  final records = <PlantPassport>[];
  final events = <CareEvent>[];
  ConsentChoices choices = const ConsentChoices();
  bool signedOut = false;
  bool unavailable = false;
  @override
  Future<GrowerAccount> signIn(String handle, String password,
      {bool register = false,
      ConsentChoices choices = const ConsentChoices()}) async {
    if (unavailable) {
      throw const PrivateApiException('Sign in again', signedOut: true);
    }
    this.choices = choices;
    return GrowerAccount(handle, choices);
  }

  @override
  Future<List<PlantPassport>> plants({String? after}) async => List.of(records);
  @override
  Future<PlantPassport> save(PlantPassport plant, {bool create = false}) async {
    final saved = PlantPassport(
        id: 'plant-id',
        nickname: plant.nickname,
        species: plant.species,
        plantedOn: plant.plantedOn,
        conditions: plant.conditions);
    records.add(saved);
    return saved;
  }

  @override
  Future<List<CareEvent>> care(String id, {String? after}) async =>
      List.of(events);
  @override
  Future<void> addCare(String id, String kind, String date, String note) async {
    events.add(CareEvent('event-id', kind, date, note));
  }

  @override
  Future<GrowerAccount> consent(ConsentChoices choices) async {
    this.choices = choices;
    return GrowerAccount('grower', choices);
  }

  @override
  Future<void> logout() async {
    signedOut = true;
  }

  @override
  void close() {}
}

void main() {
  testWidgets(
      'register, create private passport, log care and withdraw consent',
      (tester) async {
    final api = FakePrivateApi();
    await tester.pumpWidget(MaterialApp(home: PrivateGarden(api: api)));
    expect(find.textContaining('No GPS'), findsOneWidget);
    await tester.enterText(find.byType(TextFormField).at(0), 'grower');
    await tester.enterText(
        find.byType(TextFormField).at(1), 'a long private passphrase');
    await tester.ensureVisible(find.text('Create a new account'));
    await tester.tap(find.text('Create a new account'));
    await tester.pumpAndSettle();
    final optional =
        tester.widgetList<SwitchListTile>(find.byType(SwitchListTile)).skip(1);
    expect(optional.length, 3);
    expect(optional.map((w) => w.value), everyElement(false));
    await tester.scrollUntilVisible(find.text('Create account'), 200,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();
    expect(find.text('Private garden · grower'), findsOneWidget);
    await tester.tap(find.text('Add plant'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'My okra');
    await tester.enterText(find.byType(TextFormField).at(1), 'Okra');
    await tester.scrollUntilVisible(find.text('Save passport'), 200,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save passport'));
    await tester.pumpAndSettle();
    expect(api.records.single.speciesId, isNull);
    expect(find.text('My okra'), findsOneWidget);
    await tester.tap(find.text('My okra'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Log care'));
    await tester.tap(find.text('Log care'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Watered gently');
    await tester.ensureVisible(find.text('Save care'));
    await tester.tap(find.text('Save care'));
    await tester.pumpAndSettle();
    expect(api.events.single.note, 'Watered gently');
    expect(find.text('Watered gently'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.tap(find.text('Consent choices'));
    await tester.pumpAndSettle();
    await tester
        .ensureVisible(find.text('Allow aggregate survival impact statistics'));
    await tester.tap(find.text('Allow aggregate survival impact statistics'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save choices'));
    await tester.pumpAndSettle();
    expect(api.choices.impact, isTrue);
    await tester.tap(find.text('Consent choices'));
    await tester.pumpAndSettle();
    await tester
        .ensureVisible(find.text('Allow aggregate survival impact statistics'));
    await tester.tap(find.text('Allow aggregate survival impact statistics'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save choices'));
    await tester.pumpAndSettle();
    expect(api.choices.impact, isFalse);
    await tester.tap(find.text('Sign out'));
    await tester.pumpAndSettle();
    expect(api.signedOut, isTrue);
    expect(find.text('My okra'), findsNothing);
    expect(find.text('Sign in'), findsOneWidget);
  });

  testWidgets('failed sign-in shows no private garden or password',
      (tester) async {
    final api = FakePrivateApi()..unavailable = true;
    await tester.pumpWidget(MaterialApp(home: PrivateGarden(api: api)));
    await tester.enterText(find.byType(TextFormField).at(0), 'grower');
    await tester.enterText(
        find.byType(TextFormField).at(1), 'a long private passphrase');
    await tester.ensureVisible(find.text('Sign in'));
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Sign in again'), findsOneWidget);
    expect(find.text('Add plant'), findsNothing);
    expect(
        tester
            .widget<TextFormField>(find.byType(TextFormField).at(1))
            .controller
            ?.text,
        isEmpty);
  });
}
