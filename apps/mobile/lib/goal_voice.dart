import 'package:flutter/services.dart';

/// Android owns recognition; Groot never records/uploads audio itself.
class GoalVoice {
  static const _channel = MethodChannel('bd.groot/goal_voice');
  Future<String?> transcribe(String language) =>
      _channel.invokeMethod<String>('recognize', {'language': language});
}
