import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/care_reminders.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('bd.groot/care_reminders');
  tearDown(() => TestDefaultBinaryMessengerBinding
      .instance.defaultBinaryMessenger
      .setMockMethodCallHandler(channel, null));
  test(
      'reminder enable sends only device-local time, and supports denial/cancel',
      () async {
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
      calls.add(call);
      return false;
    });
    expect(await CareReminders.enable(8, 30), isFalse);
    expect(calls.single.arguments, {'hour': 8, 'minute': 30});
    expect(await CareReminders.status(), isFalse);
    await CareReminders.cancel();
    expect(calls.last.method, 'cancel');
  });
  test('unsupported platform falls back to in-app reminders', () async {
    expect(await CareReminders.enable(8, 0), isFalse);
    expect(await CareReminders.status(), isFalse);
    await CareReminders.cancel();
  });
}
