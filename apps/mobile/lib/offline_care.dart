// Explicit, bounded offline notebook. No bearer/password or automatic weather.
import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/services.dart';
import 'private_api.dart';

class OfflineCareException implements Exception {
  const OfflineCareException(this.message);
  final String message;
}

abstract interface class OfflineVault {
  Future<String?> unlock();
  Future<void> write(String data);
  Future<void> clear();
  Future<void> lock();
}

class AndroidOfflineVault implements OfflineVault {
  static const channel = MethodChannel('bd.groot/offline_care');
  @override
  Future<String?> unlock() => channel.invokeMethod<String>('unlock');
  @override
  Future<void> write(String data) => channel.invokeMethod<void>('write', data);
  @override
  Future<void> clear() => channel.invokeMethod<void>('clear');
  @override
  Future<void> lock() => channel.invokeMethod<void>('lock');
}

Map<String, dynamic> _copy(Map<String, dynamic> data) =>
    jsonDecode(jsonEncode(data)) as Map<String, dynamic>;

String _operationId() {
  final random = Random.secure();
  final bytes = List.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}

/// Revocation cannot be discovered offline. Never call cached evidence current.
/// Hide instructions after 24h, future cache times or any known evidence expiry.
Map<String, dynamic> offlinePlan(Map<String, dynamic> cached, DateTime now) {
  final raw = _copy(cached['snapshot'] as Map<String, dynamic>);
  final plan = raw['plan'] as Map<String, dynamic>;
  final checked = DateTime.tryParse(cached['checked_at'] as String? ?? '');
  final today = now.toUtc().add(const Duration(hours: 6));
  final date = today.toIso8601String().substring(0, 10);
  bool valid(String? expiry) => expiry != null && expiry.compareTo(date) >= 0;
  final steps = (plan['instructions'] as List).cast<Map<String, dynamic>>();
  final sources = [
    ...(plan['condition_sources'] as List).cast<Map<String, dynamic>>(),
    for (final step in steps)
      ...(step['sources'] as List).cast<Map<String, dynamic>>()
  ];
  plan['offline_sources'] = sources;
  if (raw['availability'] != 'current' ||
      checked == null ||
      checked.isAfter(now) ||
      now.difference(checked) >= const Duration(hours: 24) ||
      !valid(plan['valid_until'] as String?) ||
      steps.any((s) => !valid(s['valid_until'] as String?)) ||
      sources.any((s) => !valid(s['valid_until'] as String?))) {
    plan['instructions'] = <dynamic>[];
    plan['status'] = 'blocked';
    plan['message'] =
        'Cached instructions withheld. Reconnect and download reviewed guidance again.';
  }
  raw['availability'] = 'offline_unverified';
  return raw;
}

class OfflineCareStore {
  OfflineCareStore._(this.vault, this._data);
  final OfflineVault vault;
  Map<String, dynamic> _data;
  bool _closed = false;
  Future<void> _tail = Future.value();
  static Map<String, dynamic> _empty() => {
        'schema': 1,
        'owner': null,
        'origin': null,
        'passports': <String, dynamic>{},
        'plans': <String, dynamic>{},
        'operations': <dynamic>[]
      };
  static Future<OfflineCareStore> open(OfflineVault vault) async {
    final value = await vault.unlock();
    final data =
        value == null ? _empty() : jsonDecode(value) as Map<String, dynamic>;
    if (data['schema'] != 1 ||
        data['passports'] is! Map ||
        data['plans'] is! Map ||
        data['operations'] is! List) {
      throw const OfflineCareException(
          'Unsupported offline notebook. Do not overwrite it; seek recovery assistance.');
    }
    return OfflineCareStore._(vault, data);
  }

  bool get enabled => _data['owner'] != null;
  String? get owner => _data['owner'] as String?;
  String? get origin => _data['origin'] as String?;
  List<Map<String, dynamic>> get passports => (_copy(_data)['passports'] as Map)
      .values
      .cast<Map<String, dynamic>>()
      .toList();
  List<Map<String, dynamic>> get plans => (_copy(_data)['plans'] as Map)
      .values
      .cast<Map<String, dynamic>>()
      .toList();
  List<Map<String, dynamic>> get operations =>
      (_copy(_data)['operations'] as List).cast<Map<String, dynamic>>();
  int get pending => operations.where((o) => o['status'] == 'pending').length;

  Future<void> _serial(Future<void> Function() action) {
    final next = _tail.then((_) => action());
    _tail = next.then<void>((_) {}, onError: (Object _, StackTrace __) {});
    return next;
  }

  Future<void> _commit(Map<String, dynamic> next) async {
    _requireOpen();
    final encoded = jsonEncode(next);
    if (utf8.encode(encoded).length > 2 * 1024 * 1024) {
      throw const OfflineCareException(
          'Offline notebook is full. Sync before adding more; no pending care was discarded.');
    }
    await vault
        .write(encoded); // Commit durable bytes before changing visible state.
    _requireOpen();
    _data = next;
  }

  void _requireOpen() {
    if (_closed) {
      throw const OfflineCareException(
          'Notebook locked. Reopen it before continuing; pending care is preserved.');
    }
  }

  Future<void> enable(String owner, String origin) => _serial(() async {
        if (enabled && (this.owner != owner || this.origin != origin)) {
          throw const OfflineCareException(
              'This notebook belongs to another account/server. Sync it there or explicitly erase it first.');
        }
        await _commit(_copy(_data)
          ..['owner'] = owner
          ..['origin'] = origin);
      });
  void _requireEnabled() {
    _requireOpen();
    if (!enabled) {
      throw const OfflineCareException('Enable the offline notebook first.');
    }
  }

  Future<void> cachePassport(Map<String, dynamic> raw) => _serial(() async {
        _requireEnabled();
        final next = _copy(_data);
        final rows = next['passports'] as Map;
        if (rows.length >= 50 && !rows.containsKey(raw['id'])) {
          throw const OfflineCareException(
              'This prototype supports 50 downloaded plants.');
        }
        rows[raw['id']] = _copy(raw);
        await _commit(next);
      });
  Future<void> cachePlan(Map<String, dynamic> raw) => _serial(() async {
        _requireEnabled();
        final next = _copy(_data);
        final rows = next['plans'] as Map;
        if (rows.length >= 50 && !rows.containsKey(raw['plan_id'])) {
          throw const OfflineCareException(
              'This prototype supports 50 downloaded plans.');
        }
        rows[raw['plan_id']] = {
          'checked_at': DateTime.now().toUtc().toIso8601String(),
          'snapshot': _copy(raw)
        };
        await _commit(next);
      });
  Future<void> download(PrivateApi api) => _serial(() async {
        _requireEnabled();
        if (origin != api.baseUrl || owner != await api.verifyOwner()) {
          throw const OfflineCareException(
              'Sign in to this notebook’s original account/server.');
        }
        final plants = <String, dynamic>{};
        String? after;
        while (true) {
          final page = await api.plants(after: after);
          for (final p in page) {
            plants[p.id] = {'id': p.id, ...p.toJson()};
          }
          if (plants.length > 50) {
            throw const OfflineCareException(
                'Download supports at most 50 plants. Existing notebook was preserved.');
          }
          if (page.length < 20) break;
          after = page.last.id;
        }
        final plans = <String, dynamic>{};
        after = null;
        while (true) {
          final page = await api.plans(after: after);
          for (final p in page) {
            if (plans.length >= 50) {
              throw const OfflineCareException(
                  'Download supports at most 50 plans. Existing notebook was preserved.');
            }
            plans[p.id] = {
              'checked_at': DateTime.now().toUtc().toIso8601String(),
              'snapshot': await api.planSnapshot(p.id)
            };
          }
          if (page.length < 20) break;
          after = page.last.id;
        }
        // No partial replacement and no late response from a changed account.
        if (owner != await api.verifyOwner()) {
          throw const OfflineCareException(
              'Account changed. Download was not saved.');
        }
        final next = _copy(_data)
          ..['passports'] = plants
          ..['plans'] = plans;
        for (final op
            in (next['operations'] as List).cast<Map<String, dynamic>>()) {
          if (op['status'] == 'pending' &&
              !plants.containsKey(op['passport_id'])) {
            op['status'] = 'needs_review';
            op['reason'] = 'Plant no longer exists. It was not recreated.';
          }
        }
        await _commit(next);
      });
  Future<void> enqueueCare(
          String passport, String kind, String date, String note) =>
      _serial(() async {
        _requireEnabled();
        final plant = (_data['passports'] as Map)[passport] as Map?;
        final parsed = DateTime.tryParse(date);
        if (plant == null ||
            parsed == null ||
            parsed.toIso8601String().substring(0, 10) != date ||
            date.compareTo(plant['planted_on'] as String) < 0 ||
            parsed.isAfter(bangladeshToday()) ||
            !['watering', 'feeding', 'pruning', 'repotting', 'observation']
                .contains(kind) ||
            note.runes.length > 1000 ||
            note.contains('\u0000')) {
          throw const OfflineCareException(
              'Check the downloaded plant, care date, action and note.');
        }
        final next = _copy(_data);
        final rows = next['operations'] as List;
        if (rows.length >= 500) {
          throw const OfflineCareException(
              '500 local records reached. Remove reviewed/synced entries explicitly; pending care is never evicted.');
        }
        rows.add({
          'request_id': _operationId(),
          'passport_id': passport,
          'kind': kind,
          'occurred_on': date,
          'note': note.trim(),
          'status': 'pending'
        });
        await _commit(next);
      });
  Future<void> sync(PrivateApi api) => _serial(() async {
        _requireEnabled();
        if (origin != api.baseUrl || owner != await api.verifyOwner()) {
          throw const OfflineCareException(
              'Sign in to the notebook’s original account and server before syncing.');
        }
        // Serial network writes plus server UUID uniqueness survive a crash/lost reply.
        for (final op in operations.where((o) => o['status'] == 'pending')) {
          _requireEnabled();
          final next = _copy(_data);
          final row = (next['operations'] as List)
              .cast<Map<String, dynamic>>()
              .firstWhere((r) => r['request_id'] == op['request_id']);
          try {
            final id = await api.syncCare(op);
            row['status'] = 'synced';
            row['server_id'] = id;
          } on PrivateApiException catch (e) {
            if (![404, 409, 422].contains(e.statusCode)) rethrow;
            row['status'] = 'needs_review';
            row['reason'] = e.message;
            if (e.statusCode == 404) {
              (next['passports'] as Map).remove(op['passport_id']);
            }
          } on Exception {
            return; // Transport failure: leave current and remaining records pending.
          }
          await _commit(
              next); // If this fails, the same UUID is retried next time.
        }
      });
  Future<void> removeOperation(String id) => _serial(() async {
        final next = _copy(_data);
        if ((next['operations'] as List)
            .any((o) => o['request_id'] == id && o['status'] == 'pending')) {
          throw const OfflineCareException(
              'Pending care must be synced/reviewed first. Only explicit whole-notebook erasure discards pending records.');
        }
        (next['operations'] as List).removeWhere((o) => o['request_id'] == id);
        await _commit(next);
      });
  Future<void> clear() => _serial(() async {
        _requireOpen();
        await vault.clear();
        _data = _empty();
      });
  Future<void> lock() {
    // Invalidate synchronously, not behind an in-flight network request. Its late
    // acknowledgment must never write over a newly opened notebook's entries.
    _closed = true;
    _data = _empty();
    return vault.lock();
  }
}
