import 'dart:math';
import 'package:flutter/material.dart';
import 'care_models.dart';
import 'goal_models.dart';
import 'private_api.dart';
import 'quest_board.dart';

String newCareRequestId() {
  final random = Random.secure();
  final bytes = List.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}

class CarePlanView extends StatefulWidget {
  const CarePlanView(
      {super.key,
      required this.api,
      this.draft,
      this.profileId,
      this.planId,
      this.expectedVersion,
      this.versionNumber,
      this.onRevise});
  final PrivateApi api;
  final GoalDraft? draft;
  final String? profileId, planId;
  final int? expectedVersion, versionNumber;
  final Future<bool?> Function(CareVersion)? onRevise;
  @override
  State<CarePlanView> createState() => _CarePlanViewState();
}

class _CarePlanViewState extends State<CarePlanView> {
  int _weeks = 4;
  bool _busy = false;
  String? _error;
  String _requestId = newCareRequestId();
  CarePreview? _preview;
  CareVersion? _saved;
  final List<CareHistoryItem> _history = [];
  final _scroll = ScrollController();
  bool _moreHistory = true;
  bool get _editing => widget.draft != null;
  String t(String bn, String en) =>
      (widget.draft?.language ?? _saved?.plan.language ?? 'bn') == 'bn'
          ? bn
          : en;
  String topicLabel(String topic) => switch (topic) {
        'soil_preparation' => t('মাটি প্রস্তুতি', 'Soil preparation'),
        'watering' => t('পানি', 'Watering'),
        'nutrition' => t('পুষ্টি', 'Nutrition'),
        'monitoring' => t('পর্যবেক্ষণ', 'Monitoring'),
        _ => topic,
      };

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() work) async {
    setState(() {
      _busy = true;
      _error = null;
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
        setState(() => _error = t('সংযোগ ব্যর্থ। আবার চেষ্টা করুন।',
            'Connection failed. Retry when online.'));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
      if (mounted && _error != null && _scroll.hasClients) _scroll.jumpTo(0);
    }
  }

  Future<void> _load() => _run(() async {
        if (_editing) {
          final result = await widget.api
              .previewPlan(widget.draft!, widget.profileId!, _weeks);
          if (mounted) setState(() => _preview = result);
        } else {
          final result = await widget.api
              .readPlan(widget.planId!, version: widget.versionNumber);
          if (mounted) setState(() => _saved = result);
        }
      });
  Future<void> _save() async {
    final approved = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
                title: Text(
                    t('ব্যক্তিগত পরিকল্পনা সংরক্ষণ?', 'Save a private plan?')),
                content: Text(t(
                    'নির্বাচিত জেলা/অবস্থানের নির্ভুলতা, চাষের শর্ত, উৎস ও পরিকল্পনার সংস্করণ আপনার অ্যাকাউন্টে রাখা হবে। লক্ষ্য/মাটির বর্ণনার লেখা বা অডিও রাখা হবে না। আংশিক পরিকল্পনা সম্পূর্ণ যত্ন নয়। পরিকল্পনা বা অ্যাকাউন্ট মুছলে সংস্করণগুলোও মুছবে।',
                    'Your chosen district/location precision, structured growing conditions, citations and plan versions will be stored privately in your account. Free goal/soil-description text and audio are not retained. A partial plan is not complete care. Deleting the plan or account deletes its versions.')),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(c, false),
                      child: Text(t('বাতিল', 'Cancel'))),
                  FilledButton(
                      key: const Key('care-confirm-save'),
                      onPressed: () => Navigator.pop(c, true),
                      child: Text(t('সংরক্ষণ করুন', 'Save')))
                ]));
    if (approved != true || !mounted) return;
    await _run(() async {
      final result = widget.expectedVersion == null
          ? await widget.api
              .savePlan(widget.draft!, widget.profileId!, _weeks, _requestId)
          : await widget.api.revisePlan(widget.planId!, widget.draft!,
              widget.profileId!, _weeks, widget.expectedVersion!);
      if (mounted) {
        setState(() {
          _saved = result;
          _preview = null;
        });
        if (_scroll.hasClients) _scroll.jumpTo(0);
      }
    });
  }

  Future<void> _historyPage() => _run(() async {
        final rows = await widget.api.planHistory(_saved!.id,
            before: _history.isEmpty ? null : _history.last.version);
        if (mounted) {
          setState(() {
            _history.addAll(rows);
            _moreHistory = rows.length == 20;
          });
        }
      });
  Future<void> _delete() async {
    final yes = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
                title: Text(t('সব সংস্করণসহ পরিকল্পনা মুছবেন?',
                    'Delete this plan and all versions?')),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(c, false),
                      child: const Text('Cancel')),
                  TextButton(
                      onPressed: () => Navigator.pop(c, true),
                      child: const Text('Delete'))
                ]));
    if (yes != true || !mounted) return;
    await _run(() async {
      await widget.api.deletePlan(_saved!.id);
      if (mounted) Navigator.pop(context);
    });
  }

  @override
  Widget build(BuildContext context) {
    final plan = _preview ?? _saved?.plan;
    return Scaffold(
        appBar: AppBar(
            title: Text(t('পর্যালোচিত যত্ন পরিকল্পনা', 'Reviewed care plan'))),
        body: ListView(
            controller: _scroll,
            padding: const EdgeInsets.all(20),
            children: [
              if (_editing && _saved == null)
                DropdownButtonFormField<int>(
                    key: const Key('care-weeks'),
                    initialValue: _weeks,
                    decoration:
                        InputDecoration(labelText: t('সপ্তাহ', 'Weeks')),
                    items: [
                      for (var i = 1; i <= 12; i++)
                        DropdownMenuItem(value: i, child: Text('$i'))
                    ],
                    onChanged: _busy
                        ? null
                        : (v) {
                            if (v != null) {
                              setState(() {
                                _weeks = v;
                                _preview = null;
                                _requestId = newCareRequestId();
                              });
                              _load();
                            }
                          }),
              if (_busy) const LinearProgressIndicator(),
              if (_error != null) Text(_error!, key: const Key('care-error')),
              TextButton(
                  onPressed: _busy
                      ? null
                      : (_saved == null
                          ? _load
                          : () => _run(() async {
                                final result = await widget.api.readPlan(
                                    _saved!.id,
                                    version: _saved!.version);
                                if (mounted) setState(() => _saved = result);
                              })),
                  child: Text(t('পুনরায় যাচাই', 'Recheck evidence'))),
              if (_saved case final saved?) ...[
                if (widget.versionNumber != null)
                  Text(t(
                      'পুরোনো সংস্করণ: এগুলো সংরক্ষিত শর্ত, বর্তমান অবস্থার নিশ্চয়তা নয়।',
                      'Historical version: saved conditions, not confirmation of your current site.')),
                Text('Version ${saved.version} · ${saved.createdAt}',
                    key: const Key('care-version')),
                Text('Evidence: ${saved.availability}',
                    key: const Key('care-availability')),
                SelectableText('Fingerprint: ${saved.fingerprint}'),
                Text(
                    'Location precision: ${saved.conditions.precision}${saved.conditions.precision == 'district' ? ' · ${saved.conditions.district}' : ''}'),
                ExpansionTile(
                    title: Text(
                        t('সংরক্ষিত চাষের শর্ত', 'Saved growing conditions')),
                    children: [
                      Text(
                          '${saved.conditions.category} · ${saved.conditions.context} · ${saved.conditions.area ?? 'unknown'} m²'),
                      Text(
                          'Sun: ${saved.conditions.sunlight} · Soil: ${saved.conditions.texture} · ${saved.conditions.drainage}'),
                      Text(
                          'pH: ${saved.conditions.ph ?? 'unknown'} · ${saved.conditions.temperature ?? 'unknown'} °C'),
                      Text('Seed-sowing: ${saved.conditions.plantingDate}'),
                    ]),
              ],
              if (plan != null) ...[
                Text('${plan.bn} · ${plan.en}',
                    style: Theme.of(context).textTheme.titleLarge),
                Text(plan.message, key: const Key('care-status')),
                Text('${plan.generator} · ${plan.profileId}'),
                Text(
                    'Profile review / expiry: ${plan.reviewedAt ?? '—'} / ${plan.validUntil ?? '—'}'),
                for (final reason in plan.reasons) Text('✓ $reason'),
                Text(plan.disclaimer),
                for (final issue in plan.issues)
                  Card(
                      child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                    '${issue.code} · ${issue.topic ?? ''} ${issue.weeks.join(', ')}'),
                                Text(issue.message),
                                for (final source in issue.sources)
                                  CareCitation(source: source)
                              ]))),
                // Defense in depth: never render historical advice when evidence is stale.
                if (plan.status != 'blocked' &&
                    (_saved == null || _saved!.availability == 'current'))
                  for (final step in plan.steps)
                    Card(
                        child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                      '${topicLabel(step.topic)} · ${t('সপ্তাহ', 'Week')} ${step.weekStart}–${step.weekEnd}'),
                                  Text('${step.startsOn} → ${step.endsOn}'),
                                  Text(step.instruction),
                                  Text(
                                      'Reviewed: ${step.reviewedBy} · ${step.reviewedAt} · Valid until ${step.validUntil}'),
                                  for (final source in step.sources)
                                    CareCitation(source: source)
                                ]))),
                ExpansionTile(
                    title: Text(t('শর্তের উৎস', 'Condition sources')),
                    children: [
                      for (final source in plan.conditionSources)
                        CareCitation(source: source)
                    ]),
                if (_editing && _saved == null)
                  FilledButton(
                      key: const Key('care-save'),
                      onPressed:
                          _busy || plan.status == 'blocked' ? null : _save,
                      child: Text(widget.expectedVersion == null
                          ? t('ব্যক্তিগত পরিকল্পনা সংরক্ষণ',
                              'Save private plan')
                          : t('নতুন সংস্করণ সংরক্ষণ', 'Save new version'))),
              ],
              if (_saved != null) ...[
                if (widget.versionNumber == null)
                  FilledButton(
                      key: const Key('care-quests'),
                      onPressed: _busy ? null : () async {
                        final expired = await Navigator.push<bool>(context,
                            MaterialPageRoute(builder: (_) => QuestBoard(api: widget.api, planId: _saved!.id)));
                        if (mounted && expired == true) Navigator.pop(this.context, true);
                      },
                      child: Text(t('যত্নের কাজ ও আবহাওয়া', 'Care quests & weather'))),
                if (widget.versionNumber == null && widget.onRevise != null)
                  OutlinedButton(
                      onPressed: _busy
                          ? null
                          : () async {
                              final expired = await widget.onRevise!(_saved!);
                              if (!mounted) return;
                              if (expired == true) {
                                Navigator.pop(this.context, true);
                                return;
                              }
                              _load();
                            },
                      child: Text(t('শর্ত সংশোধন / নতুন সংস্করণ',
                          'Revise conditions / new version'))),
                for (final row in _history)
                  ListTile(
                      title: Text('Version ${row.version} · ${row.status}'),
                      subtitle: Text(row.date),
                      onTap: _busy
                          ? null
                          : () async {
                              final expired = await Navigator.push<bool>(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) => CarePlanView(
                                          api: widget.api,
                                          planId: _saved!.id,
                                          versionNumber: row.version)));
                              if (mounted && expired == true) {
                                Navigator.pop(this.context, true);
                              }
                            }),
                if (_moreHistory)
                  TextButton(
                      key: const Key('care-history'),
                      onPressed: _busy ? null : _historyPage,
                      child: Text(
                          t('সংস্করণ ইতিহাস / আরও', 'Version history / more'))),
                if (widget.versionNumber == null)
                  TextButton(
                      onPressed: _busy ? null : _delete,
                      child: Text(t('পরিকল্পনা মুছুন', 'Delete plan'))),
              ]
            ]));
  }
}

class CareCitation extends StatelessWidget {
  const CareCitation({super.key, required this.source});
  final GoalCitation source;
  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.all(8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${source.title} · ${source.locator}'),
        Text(source.note),
        SelectableText(source.url),
        Text(
            'Checked: ${source.checkedAt} · Valid until: ${source.validUntil}'),
        Text(source.license),
        SelectableText(source.licenseUrl),
        Text(source.attribution)
      ]));
}
