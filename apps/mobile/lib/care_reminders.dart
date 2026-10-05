import 'package:flutter/services.dart';

/// Generic device reminder only; no bearer, plant names, plans or location sent.
class CareReminders {
  static const _channel = MethodChannel('bd.groot/care_reminders');

  static Future<bool> status() async {
    try {
      return await _channel.invokeMethod<bool>('status') ?? false;
    } on PlatformException {
      return false;
    } on MissingPluginException {
      return false;
    }
  }

  static Future<bool> enable(int hour, int minute) async {
    try {
      return await _channel
              .invokeMethod<bool>('enable', {'hour': hour, 'minute': minute}) ??
          false;
    } on PlatformException {
      return false;
    } on MissingPluginException {
      return false;
    }
  }

  static Future<void> cancel() async {
    try {
      await _channel.invokeMethod<void>('cancel');
    } on PlatformException {
      // No platform scheduling capability; in-app reminders still work.
    } on MissingPluginException {
      // Widget tests / unsupported platforms have no native reminder channel.
    }
  }
}
