import 'dart:async';
import 'package:flutter/material.dart';
import 'care_plan_view.dart';
import 'care_reminders.dart';
import 'private_api.dart';
import 'quest_models.dart';

class QuestBoard extends StatefulWidget {
  const QuestBoard({super.key, required this.api, required this.planId});
  final PrivateApi api;
  final String planId;
  @override
  State<QuestBoard> createState() => _QuestBoardState();
}

class _QuestBoardState extends State<QuestBoard> with WidgetsBindingObserver {
  QuestData? _data;
  bool _busy = false, _reminder = false;
  String? _error, _deviceMessage;
  Timer? _refreshTimer;
  bool _foreground = true;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
    _refreshTimer = Timer.periodic(const Duration(minutes: 5), (_) {
      if (_foreground && !_busy) _load();
    });
    CareReminders.status().then((v) {
      if (mounted) setState(() => _reminder = v);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    if (state == AppLifecycleState.resumed && !_busy) _load();
  }

  Future<void> _run(Future<void> Function() work) async {
    if (_busy) return;
    // Hide cached advice immediately during refresh or failure; don't present old
    // weather/evidence as current when the network cannot revalidate it.
    setState(() {
      _busy = true;
      _error = null;
      _data = null;
    });
    try {
      await work();
    } on PrivateApiException catch (e) {
      if (!mounted) return;
      if (e.signedOut) {
        Navigator.pop(context, true);
        return;
      }
      setState(() => _error = e.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'সংযোগ নেই · Offline: current quests/weather cannot be verified. Retry online.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _load() => _run(() async {
        final result = await widget.api.quests(widget.planId);
        if (mounted) setState(() => _data = result);
      });

  Future<void> _complete(CareQuest quest, int version) => _run(() async {
        final result = await widget.api
            .completeQuest(widget.planId, version, quest.key, !quest.completed);
        if (mounted) setState(() => _data = result);
      });

  Future<void> _weather(bool enabled) async {
    if (enabled) {
      final approved = await showDialog<bool>(
          context: context,
          builder: (c) => AlertDialog(
                  title:
                      const Text('জেলার আবহাওয়া · Enable district weather?'),
                  content: const Text(
                      'Your saved district’s approximate city reference point will be sent by the server to Open-Meteo. No GPS, plant name, account or token is sent. Forecasts are regional estimates, not soil moisture. Open-Meteo may retain request coordinates/server IP in logs. Weather is off by default; turn it off here to withdraw. No automatic watering/doses. Supported districts: Dhaka, Chattogram, Rajshahi, Khulna, Sylhet, Rangpur, Barishal, Mymensingh.'),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(c, false),
                        child: const Text('Cancel')),
                    FilledButton(
                        onPressed: () => Navigator.pop(c, true),
                        child: const Text('Enable'))
                  ]));
      if (approved != true || !mounted) {
        return;
      }
    }
    await _run(() async {
      await widget.api.questWeather(widget.planId, enabled);
      final result = await widget.api.quests(widget.planId);
      if (mounted) setState(() => _data = result);
    });
  }

  Future<void> _deviceReminder() async {
    if (_reminder) {
      await CareReminders.cancel();
      if (mounted) {
        setState(() {
          _reminder = false;
          _deviceMessage = 'Device reminder cancelled.';
        });
      }
      return;
    }
    final time = await showTimePicker(
        context: context, initialTime: const TimeOfDay(hour: 8, minute: 0));
    if (time == null || !mounted) return;
    final ok = await CareReminders.enable(time.hour, time.minute);
    if (mounted) {
      setState(() {
        _reminder = ok;
        _deviceMessage = ok
            ? 'Daily generic reminder enabled in device local time. Delivery may be delayed by Android.'
            : 'Notification permission denied or unavailable. In-app reminders still work.';
      });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('যত্নের কাজ · Care quests')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        if (_busy) const LinearProgressIndicator(),
        if (_error != null) Text(_error!, key: const Key('quest-error')),
        TextButton(
            onPressed: _busy ? null : _load,
            child: const Text('আবার যাচাই · Refresh tasks & weather')),
        if (_data case final data?) ...[
          Text(
              'Version ${data.version} · ${data.today} · Evidence: ${data.availability}'),
          Text('${data.reminderCount} pending check-ins/reviews · বাকি কাজ',
              key: const Key('quest-reminders')),
          Text(data.message),
          const Text(
              'Daily = observation. Weekly = review the cited instruction, not a prescribed watering/feeding frequency.'),
          SwitchListTile(
              title: const Text('জেলার আবহাওয়া · District weather'),
              value: data.weatherEnabled,
              onChanged: _busy ? null : _weather),
          Card(
              child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Weather: ${data.weather.status}',
                            key: const Key('quest-weather-status')),
                        Text(data.weather.message),
                        const Text(
                            'Status as of last refresh; checked again on resume and every 5 minutes while this screen is active.'),
                        Text(
                            'Reference: ${data.weather.district ?? '—'} · retrieved: ${data.weather.fetchedAt ?? '—'}'),
                        const Text(
                            'Model issue time is not supplied; retrieval time is not model age.'),
                        Text(data.weather.attribution),
                        SelectableText(data.weather.sourceUrl),
                      ]))),
          if (data.quests.isEmpty)
            const Text(
                'No current tasks. A future/finished plan or changed evidence does not create invented care. Recheck/revise the plan.'),
          for (final quest in data.quests)
            Card(
                child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(quest.title,
                              style: Theme.of(context).textTheme.titleMedium),
                          Text(
                              '${quest.cadence} · ${quest.startsOn} → ${quest.dueOn}'),
                          Text(quest.instruction),
                          if (quest.weatherNote.isNotEmpty)
                            Text(quest.weatherNote),
                          for (final source in quest.sources)
                            CareCitation(source: source),
                          TextButton(
                              key: Key('quest-complete-${quest.key}'),
                              onPressed: _busy ||
                                      quest.startsOn.compareTo(data.today) > 0
                                  ? null
                                  : () => _complete(quest, data.version),
                              child: Text(quest.completed
                                  ? 'Completed · সম্পন্ন (undo)'
                                  : 'Mark check-in/review complete · সম্পন্ন করুন')),
                        ]))),
        ],
        const Divider(),
        const Text(
            'Optional Android reminder: generic “open Groot and check current tasks”, never watering instructions or plant/location details. It is device-wide, repeats daily even if the app is closed, and is cancelled on sign-out, closing the private garden or the next app restart. No background forecast refresh; no exact-time guarantee. Disable it below or in Android settings.'),
        TextButton(
            onPressed: _busy ? null : _deviceReminder,
            child: Text(_reminder
                ? 'Disable device reminder'
                : 'Set daily device reminder')),
        if (_deviceMessage != null) Text(_deviceMessage!),
      ]));
}
