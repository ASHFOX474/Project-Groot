import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'care_models.dart';
import 'care_plan_view.dart';
import 'goal_models.dart';
import 'offline_care.dart';
import 'private_api.dart';
import 'private_garden.dart' show CareForm;

class OfflineCareView extends StatefulWidget {
  const OfflineCareView({super.key, required this.api, this.vault});
  final PrivateApi api;
  final OfflineVault? vault;
  @override
  State<OfflineCareView> createState() => _OfflineCareViewState();
}

class _OfflineCareViewState extends State<OfflineCareView>
    with WidgetsBindingObserver {
  late final _vault = widget.vault ?? AndroidOfflineVault();
  OfflineCareStore? _store;
  bool _busy = false;
  String? _message;
  Timer? _retry;
  Timer? _autoLock;
  bool get _sameAccount =>
      _store?.owner == widget.api.currentOwnerId &&
      _store?.origin == widget.api.baseUrl &&
      widget.api.currentOwnerId != null;

  Future<void> _lock() {
    final store = _store;
    _store = null;
    return store?.lock() ?? _vault.lock();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Foreground-only retry: opening the notebook is explicit. No background job.
    _retry = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted && _store != null && !_busy) {
        setState(() {}); // Recheck offline expiry even with no pending writes.
      }
      if (mounted && !_busy && _sameAccount && (_store?.pending ?? 0) > 0) {
        _sync();
      }
    });
  }

  @override
  void dispose() {
    _retry?.cancel();
    _autoLock?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    unawaited(_lock().catchError((Object _) {}));
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused && _store != null) {
      final locking = _lock();
      setState(() {
        _message = 'Notebook locked. Unlock again to continue.';
      });
      unawaited(locking.catchError((Object _) {}));
    }
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await action();
    } on OfflineCareException catch (e) {
      if (mounted) setState(() => _message = e.message);
    } on PrivateApiException catch (e) {
      if (mounted) {
        if (e.signedOut) {
          await _lock();
        }
        if (mounted) setState(() => _message = e.message);
      }
    } on PlatformException catch (_) {
      await _lock();
      if (mounted) {
        setState(() => _message =
            'Android device-lock/storage unavailable. Set a screen-lock PIN/password, then unlock again. Nothing new was saved.');
      }
    } catch (_) {
      if (mounted) {
        setState(() => _message =
            'Connection or storage unavailable. Pending care remains on this device; retry after unlocking/connecting.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _unlock() => _run(() async {
        final store = await OfflineCareStore.open(_vault);
        if (!mounted) {
          await _vault.lock();
          return;
        }
        // A different online account cannot read/queue/sync this notebook.
        if (store.enabled &&
            widget.api.currentOwnerId != null &&
            (store.owner != widget.api.currentOwnerId ||
                store.origin != widget.api.baseUrl)) {
          await _vault.lock();
          throw const OfflineCareException(
              'Notebook belongs to another account/server. Sign out, unlock offline, and sync with the original account.');
        }
        setState(() => _store = store);
        _autoLock?.cancel();
        _autoLock = Timer(const Duration(minutes: 5), () {
          if (!mounted) return;
          final locking = _lock();
          setState(() {
            _message =
                'Device authentication expired. Unlock the notebook again.';
          });
          unawaited(locking.catchError((Object _) {}));
        });
        if (_sameAccount && store.pending > 0) await store.sync(widget.api);
      });
  Future<void> _enable() async {
    final owner = widget.api.currentOwnerId;
    if (owner == null) return;
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
                title: const Text('Enable private offline care?'),
                content: const Text(
                    'Downloaded plans, plant conditions and care notes will remain encrypted on this Android device, including after sign-out. Anyone who knows its screen-lock credential can unlock them. No password/token is saved. Unsynced care is lost if you erase the notebook, uninstall, or lose this device. Offline sources may have changed; instructions expire after 24 hours. Enable only on your own device.'),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(c, false),
                      child: const Text('Cancel')),
                  FilledButton(
                      onPressed: () => Navigator.pop(c, true),
                      child: const Text('Enable'))
                ]));
    if (confirmed != true || !mounted) return;
    await _run(() async {
      if (owner != await widget.api.verifyOwner()) {
        throw const OfflineCareException('Sign in again.');
      }
      await _store?.enable(owner, widget.api.baseUrl);
    });
  }

  Future<void> _sync() => _run(() async {
        final store = _store;
        if (store == null || !_sameAccount) return;
        await store.sync(widget.api);
        if (mounted) {
          setState(() => _message =
              '${store.pending} pending. Synced and needs-review records are shown below.');
        }
      });
  Future<bool> _confirm(String title, String message) async =>
      await showDialog<bool>(
          context: context,
          builder: (c) =>
              AlertDialog(title: Text(title), content: Text(message), actions: [
                TextButton(
                    onPressed: () => Navigator.pop(c, false),
                    child: const Text('Cancel')),
                FilledButton(
                    onPressed: () => Navigator.pop(c, true),
                    child: const Text('Confirm'))
              ])) ==
      true;

  @override
  Widget build(BuildContext context) {
    final store = _store;
    return Scaffold(
        appBar: AppBar(title: const Text('অফলাইন যত্ন · Offline care')),
        body: ListView(padding: const EdgeInsets.all(20), children: [
          const Text(
              'Private device notebook · Cached, not live advice. No fresh weather, recommendations, passport edits or quest completion while offline.'),
          if (_busy) const LinearProgressIndicator(),
          if (_message != null)
            Text(_message!, key: const Key('offline-message')),
          if (store == null)
            FilledButton(
                key: const Key('offline-unlock'),
                onPressed: _busy ? null : _unlock,
                child: const Text('Unlock offline notebook')),
          if (store != null && !store.enabled) ...[
            const Text(
                'Offline care is off. Sign in online first to enable and download your own records.'),
            FilledButton(
                onPressed:
                    _busy || widget.api.currentOwnerId == null ? null : _enable,
                child: const Text('Enable offline care')),
          ],
          if (store != null && store.enabled) ...[
            Text(
                '${store.pending} pending · ${store.operations.where((o) => o['status'] == 'needs_review').length} need review',
                key: const Key('offline-count')),
            if (!_sameAccount)
              const Text(
                  'Offline access only. Close this page and sign in to the original account/server to sync.'),
            FilledButton(
                key: const Key('offline-sync'),
                onPressed: _busy || !_sameAccount ? null : _sync,
                child: const Text('Sync now')),
            OutlinedButton(
                onPressed: _busy || !_sameAccount
                    ? null
                    : () => _run(() => store.download(widget.api)),
                child: const Text('Download / refresh plans and plants')),
            TextButton(
                onPressed: _busy
                    ? null
                    : () => _run(() async {
                          await store.lock();
                          if (mounted) setState(() => _store = null);
                        }),
                child: const Text('Lock notebook')),
            const Text(
                'Downloaded plans · Last checked is not a guarantee sources are still valid.'),
            for (final cached in store.plans) _OfflinePlan(cached: cached),
            if (store.plans.isEmpty)
              const Text(
                  'No downloaded plans. Approved care content is still required; no demo fallback.'),
            const Text(
                'Downloaded plants · Record what you did, not an instruction to act.'),
            for (final raw in store.passports)
              ListTile(
                  title: Text(raw['nickname'] as String),
                  subtitle: Text(
                      '${raw['species_name']} · planted ${raw['planted_on']}\n${raw['conditions']}'),
                  trailing: TextButton(
                      onPressed: _busy
                          ? null
                          : () async {
                              final event = await Navigator.push<CareEvent>(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) => CareForm(
                                          plantedOn:
                                              raw['planted_on'] as String)));
                              if (event == null ||
                                  !mounted ||
                                  _store != store) {
                                return;
                              }
                              await _run(() async {
                                await store.enqueueCare(raw['id'] as String,
                                    event.kind, event.date, event.note);
                                if (mounted) {
                                  setState(() => _message =
                                      'Saved on this device · pending sync.');
                                }
                              });
                            },
                      child: const Text('Record care'))),
            const Text(
                'Local care records · Pending is not yet saved on the server.'),
            for (final op in store.operations)
              ListTile(
                  title: Text(
                      '${op['occurred_on']} · ${op['kind']} · ${op['status']}'),
                  subtitle: Text('${op['note']}\n${op['reason'] ?? ''}'),
                  trailing: op['status'] == 'pending'
                      ? null
                      : IconButton(
                          tooltip: 'Remove local record',
                          icon: const Icon(Icons.clear),
                          onPressed: _busy
                              ? null
                              : () async {
                                  if (await _confirm('Remove local record?',
                                      'This removes only this device’s copy. Synced server care is not deleted; a needs-review entry was not accepted. Never recreate it with a new ID unless you have confirmed it was not saved.')) {
                                    if (mounted) {
                                      await _run(() => store.removeOperation(
                                          op['request_id'] as String));
                                    }
                                  }
                                })),
            TextButton(
                onPressed: _busy
                    ? null
                    : () async {
                        if (await _confirm('Erase offline notebook?',
                            'All downloaded records and ${store.pending} pending care entries will be permanently removed from this device. Server records are unchanged.')) {
                          if (mounted) await _run(store.clear);
                        }
                      },
                child: const Text('Disable and erase local notebook')),
          ],
        ]));
  }
}

class _OfflinePlan extends StatelessWidget {
  const _OfflinePlan({required this.cached});
  final Map<String, dynamic> cached;
  @override
  Widget build(BuildContext context) {
    final raw = offlinePlan(cached, DateTime.now().toUtc());
    final plan = CarePreview(raw['plan'] as Map<String, dynamic>);
    return ExpansionTile(
        title: Text('${plan.bn} · ${plan.en}'),
        subtitle: Text(
            'Version ${raw['version']} · downloaded ${cached['checked_at']}'),
        children: [
          const Text(
              'Offline / unverified. Source changes and remote deletion cannot be discovered without reconnecting. No weather adaptation.'),
          Text(plan.message),
          Text('Review: ${plan.reviewedAt} · expiry: ${plan.validUntil}'),
          Text(plan.disclaimer),
          if (raw['conditions'] is Map)
            Text('Saved growing conditions: ${raw['conditions']}'),
          for (final issue in plan.issues) Text(issue.message),
          for (final step in plan.steps)
            ListTile(
                title:
                    Text('${step.topic} · ${step.startsOn} → ${step.endsOn}'),
                subtitle: Text(
                    '${step.instruction}\nReviewed ${step.reviewedAt} · valid until ${step.validUntil}')),
          for (final source in (raw['plan']['offline_sources'] as List))
            CareCitation(source: GoalCitation(source as Map<String, dynamic>)),
        ]);
  }
}
