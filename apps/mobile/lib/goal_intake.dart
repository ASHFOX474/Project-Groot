import 'package:flutter/material.dart';

import 'goal_models.dart';
import 'goal_voice.dart';
import 'private_api.dart';
import 'care_plan_view.dart';

class GoalIntake extends StatefulWidget {
  const GoalIntake(
      {super.key,
      required this.api,
      this.voice,
      this.initialGoal,
      this.revisePlanId,
      this.expectedVersion});
  final PrivateApi api;
  final GoalVoice? voice;
  final GoalDraft? initialGoal;
  final String? revisePlanId;
  final int? expectedVersion;
  @override
  State<GoalIntake> createState() => _GoalIntakeState();
}

class _GoalIntakeState extends State<GoalIntake> {
  final _form = GlobalKey<FormState>();
  final _goal = TextEditingController();
  final _district = TextEditingController();
  final _area = TextEditingController();
  final _soil = TextEditingController();
  final _ph = TextEditingController();
  final _temperature = TextEditingController();
  String _language = 'bn', _category = 'any', _precision = 'none';
  String _context = 'container', _sunlight = 'unknown';
  String _texture = 'unknown', _drainage = 'unknown';
  DateTime _date = bangladeshToday();
  bool _busy = false;
  String? _error;
  GoalAssessment? _result;
  GoalDraft? _submittedDraft;

  @override
  void initState() {
    super.initState();
    final d = widget.initialGoal;
    if (d == null) return;
    _language = d.language;
    _category = d.category;
    _precision = d.precision;
    _context = d.context;
    _sunlight = d.sunlight;
    _texture = d.texture;
    _drainage = d.drainage;
    _goal.text = d.goal;
    _district.text = d.district;
    _soil.text = d.description;
    _area.text = d.area?.toString() ?? '';
    _ph.text = d.ph?.toString() ?? '';
    _temperature.text = d.temperature?.toString() ?? '';
    _date = DateTime.parse(d.plantingDate);
  }

  Future<void> _plan(GoalPlant plant) async {
    final expired = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
            builder: (_) => CarePlanView(
                api: widget.api,
                draft: _submittedDraft!,
                profileId: plant.profileId,
                planId: widget.revisePlanId,
                expectedVersion: widget.expectedVersion)));
    if (mounted && expired == true) Navigator.pop(context, true);
  }

  String t(String bn, String en) => _language == 'bn' ? bn : en;

  @override
  void dispose() {
    for (final c in [_goal, _district, _area, _soil, _ph, _temperature]) {
      c.dispose();
    }
    super.dispose();
  }

  void _change(VoidCallback update) => setState(() {
        update();
        _result = null;
        _error = null;
      });

  String? _number(String? value, double minimum, double maximum,
      {bool positive = false}) {
    if (value == null || value.trim().isEmpty) return null;
    final number = goalNumber(value);
    return number != null &&
            number.isFinite &&
            number >= minimum &&
            number <= maximum &&
            (!positive || number > 0)
        ? null
        : t('সঠিক সংখ্যাটি দিন; না জানলে ফাঁকা রাখুন।',
            'Enter a valid number, or leave unknown blank.');
  }

  Future<void> _submit() async {
    if (_form.currentState?.validate() != true) return;
    FocusScope.of(context).unfocus();
    final draft = GoalDraft(
        language: _language,
        goal: _goal.text.trim(),
        category: _category,
        precision: _precision,
        district: _district.text.trim(),
        context: _context,
        area: goalNumber(_area.text),
        sunlight: _sunlight,
        description: _soil.text.trim(),
        ph: goalNumber(_ph.text),
        texture: _texture,
        drainage: _drainage,
        plantingDate: _date.toIso8601String().substring(0, 10),
        temperature: goalNumber(_temperature.text));
    setState(() {
      _busy = true;
      _result = null;
      _error = null;
    });
    try {
      final result = await widget.api.recommend(draft);
      if (mounted) {
        setState(() {
          _result = result;
          _submittedDraft = draft;
        });
      }
    } on PrivateApiException catch (e) {
      if (!mounted) return;
      if (e.signedOut && Navigator.of(context).canPop()) {
        Navigator.of(context).pop(true);
        return;
      }
      setState(() => _error = t(
          'অনুরোধ সম্পন্ন হয়নি। তথ্য, সংযোগ ও সাইন-ইন পরীক্ষা করুন।',
          e.message));
    } catch (_) {
      if (mounted) {
        setState(() => _error = t('সংযোগ ব্যর্থ। অনলাইনে আবার চেষ্টা করুন।',
            'Connection failed. Retry when online.'));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _speak() async {
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
                title: Text(t('ভয়েস ইনপুট', 'Voice input')),
                content: Text(t(
                    'Android-এর নির্বাচিত স্পিচ সেবা আপনার অডিও অনলাইনে পাঠাতে পারে। Groot অডিও সংরক্ষণ করে না। ঠিকানা বা ব্যক্তিগত তথ্য বলবেন না। লেখা দেখে ঠিক করে নিজে জমা দিন।',
                    'Your Android speech provider may process audio online. Groot does not store audio. Do not speak addresses or personal details. Review/edit the transcript before submitting.')),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: Text(t('বাতিল', 'Cancel'))),
                  FilledButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: Text(t('চালিয়ে যান', 'Continue')))
                ]));
    if (confirmed != true || !mounted) return;
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final transcript =
          await (widget.voice ?? GoalVoice()).transcribe(_language);
      if (mounted && transcript != null && transcript.trim().isNotEmpty) {
        if (transcript.length > 500) {
          setState(() => _error = t('ভয়েস লেখা বেশি বড়। সংক্ষেপে টাইপ করুন।',
              'Transcript is too long. Type a shorter goal.'));
        } else {
          _goal.text = transcript;
        }
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = t(
            'এই ডিভাইসে ভয়েস পাওয়া যাচ্ছে না। টাইপ করুন বা কিবোর্ডের মাইক ব্যবহার করুন।',
            'Voice is unavailable on this device. Type or use your keyboard microphone.'));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickDate() async {
    final value = await showDatePicker(
        context: context,
        initialDate: _date,
        firstDate: DateTime(1900),
        lastDate: DateTime(2100),
        helpText: t('বীজ বপনের সম্ভাব্য তারিখ', 'Planned seed-sowing date'),
        cancelText: t('বাতিল', 'Cancel'),
        confirmText: t('ঠিক আছে', 'OK'));
    if (mounted && value != null) {
      _change(() => _date = value);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
            title: Text(t('লক্ষ্য ও উপযুক্ত গাছ', 'Goal and suitable plants'))),
        body: SafeArea(
            child: Form(
                key: _form,
                // Keep every field registered for validation even off screen.
                child: SingleChildScrollView(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _Choice(
                              label: 'Language · ভাষা',
                              id: 'goal-language',
                              value: _language,
                              options: const {'bn': 'বাংলা', 'en': 'English'},
                              enabled: !_busy,
                              change: (v) => _change(() => _language = v)),
                          const SizedBox(height: 12),
                          Text(t(
                              'সুপারিশ অস্থায়ী। যত্ন পরিকল্পনা আলাদাভাবে সংরক্ষণ করলে নির্বাচিত অবস্থান ও চাষের শর্ত রাখা হবে, লক্ষ্য/মাটির বর্ণনার লেখা নয়। ঠিকানা বা GPS লিখবেন না।',
                              'Recommendations are temporary. Separately saving a care plan retains chosen location and structured conditions, not free goal/soil-description text. Do not enter addresses or GPS.')),
                          TextFormField(
                              key: const Key('goal-text'),
                              controller: _goal,
                              enabled: !_busy,
                              maxLength: 500,
                              minLines: 2,
                              maxLines: 4,
                              decoration: InputDecoration(
                                  labelText: t('আপনার লক্ষ্য (বাংলা বা ইংরেজি)',
                                      'Your goal (Bangla or English)')),
                              validator: (v) => (v ?? '').trim().isEmpty
                                  ? t('লক্ষ্য লিখুন।', 'Enter a goal.')
                                  : null,
                              onChanged: (_) => _change(() {})),
                          OutlinedButton.icon(
                              key: const Key('goal-voice'),
                              onPressed: _busy ? null : _speak,
                              icon: const Icon(Icons.mic_none),
                              label: Text(t('বলুন (ডিভাইসে থাকলে)',
                                  'Speak (if available)'))),
                          _Choice(
                              label: t('লক্ষ্যের ধরন', 'Goal category'),
                              id: 'goal-category',
                              value: _category,
                              options: {
                                'any': t('যেকোনো', 'Any'),
                                'crop': t('ফসল', 'Crops'),
                                'tree': t('গাছ', 'Trees')
                              },
                              enabled: !_busy,
                              change: (v) => _change(() => _category = v)),
                          Text(t(
                              'লেখা থেকে ধরন অনুমান করা হয় না; উপরের ধরন নিশ্চিত করুন।',
                              'Free text is not parsed into a plant category; confirm the category above.')),
                          _Choice(
                              label: t('কতটুকু অবস্থান দেবেন?',
                                  'Location precision you choose'),
                              id: 'goal-precision',
                              value: _precision,
                              options: {
                                'none': t('কিছুই নয়', 'No location'),
                                'country':
                                    t('শুধু বাংলাদেশ', 'Bangladesh only'),
                                'district': t('শুধু জেলা', 'District only')
                              },
                              enabled: !_busy,
                              change: (v) => _change(() {
                                    _precision = v;
                                    if (v != 'district') _district.clear();
                                  })),
                          if (_precision == 'district')
                            TextFormField(
                                key: const Key('goal-district'),
                                controller: _district,
                                enabled: !_busy,
                                maxLength: 80,
                                decoration: InputDecoration(
                                    labelText: t('জেলা (যেমন ঢাকা / Dhaka)',
                                        'District (e.g. Dhaka / ঢাকা)')),
                                validator: (v) => (v ?? '').trim().isEmpty
                                    ? t('জেলা দিন বা কম নির্ভুলতা বেছে নিন।',
                                        'Enter a district or choose less precision.')
                                    : null,
                                onChanged: (_) => _change(() {})),
                          _Choice(
                              label: t('চাষের পরিবেশ', 'Growing space'),
                              id: 'goal-context',
                              value: _context,
                              options: {
                                'container':
                                    t('টব / ছাদ', 'Container / rooftop'),
                                'open_ground': t('খোলা মাটি', 'Open ground'),
                                'forestry': t('বনায়ন', 'Forestry')
                              },
                              enabled: !_busy,
                              change: (v) => _change(() => _context = v)),
                          TextFormField(
                              key: const Key('goal-area'),
                              controller: _area,
                              enabled: !_busy,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                      decimal: true),
                              maxLength: 12,
                              decoration: InputDecoration(
                                  labelText: t(
                                      'জায়গা (বর্গমিটার; না জানলে ফাঁকা)',
                                      'Area (m²; blank if unknown)')),
                              validator: (v) =>
                                  _number(v, 0, 100000, positive: true),
                              onChanged: (_) => _change(() {})),
                          _Choice(
                              label: t('সূর্যালোকের ধরন', 'Sunlight'),
                              id: 'goal-sunlight',
                              value: _sunlight,
                              options: {
                                'unknown': t('জানি না', 'Unknown'),
                                'full_sun': t('পূর্ণ রোদ', 'Full sun'),
                                'partial_shade':
                                    t('আংশিক ছায়া', 'Partial shade'),
                                'shade': t('ছায়া', 'Shade')
                              },
                              enabled: !_busy,
                              change: (v) => _change(() => _sunlight = v)),
                          TextFormField(
                              key: const Key('goal-soil'),
                              controller: _soil,
                              enabled: !_busy,
                              maxLength: 300,
                              decoration: InputDecoration(
                                  labelText: t(
                                      'মাটি / টবের মাধ্যমের বর্ণনা (ঐচ্ছিক)',
                                      'Soil / potting description (optional)')),
                              onChanged: (_) => _change(() {})),
                          TextFormField(
                              key: const Key('goal-ph'),
                              controller: _ph,
                              enabled: !_busy,
                              maxLength: 6,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                      decimal: true),
                              decoration: InputDecoration(
                                  labelText: t('মাপা pH (০–১৪; না জানলে ফাঁকা)',
                                      'Measured pH (0–14; blank if unknown)')),
                              validator: (v) => _number(v, 0, 14),
                              onChanged: (_) => _change(() {})),
                          _Choice(
                              label: t('মাটির গঠন', 'Soil texture'),
                              id: 'goal-texture',
                              value: _texture,
                              options: {
                                'unknown': t('জানি না', 'Unknown'),
                                'sand': t('বালু', 'Sand'),
                                'sandy_loam': t('বেলে দোআঁশ', 'Sandy loam'),
                                'loam': t('দোআঁশ', 'Loam'),
                                'clay_loam': t('এঁটেল দোআঁশ', 'Clay loam'),
                                'clay': t('এঁটেল', 'Clay')
                              },
                              enabled: !_busy,
                              change: (v) => _change(() => _texture = v)),
                          _Choice(
                              label: t('পানি নিষ্কাশন', 'Drainage'),
                              id: 'goal-drainage',
                              value: _drainage,
                              options: {
                                'unknown': t('জানি না', 'Unknown'),
                                'well_drained':
                                    t('ভালো নিষ্কাশন', 'Well drained'),
                                'moist_not_waterlogged': t(
                                    'আর্দ্র, জলাবদ্ধ নয়',
                                    'Moist, not waterlogged'),
                                'waterlogged': t('জলাবদ্ধ', 'Waterlogged')
                              },
                              enabled: !_busy,
                              change: (v) => _change(() => _drainage = v)),
                          TextFormField(
                              key: const Key('goal-temperature'),
                              controller: _temperature,
                              enabled: !_busy,
                              maxLength: 6,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                      decimal: true, signed: true),
                              decoration: InputDecoration(
                                  labelText: t(
                                      'চাষের তাপমাত্রা °C (জানা থাকলে)',
                                      'Growing temperature °C (if known)')),
                              validator: (v) => _number(v, -20, 60),
                              onChanged: (_) => _change(() {})),
                          TextButton(
                              key: const Key('goal-date'),
                              onPressed: _busy ? null : _pickDate,
                              child: Text(
                                  '${t('বীজ বপনের তারিখ', 'Seed-sowing date')}: ${_date.toIso8601String().substring(0, 10)}')),
                          if (_busy) const LinearProgressIndicator(),
                          FilledButton(
                              key: const Key('goal-submit'),
                              onPressed: _busy ? null : _submit,
                              child: Text(t('পর্যালোচিত মিল দেখুন',
                                  'Find reviewed matches'))),
                          if (_error != null)
                            Text(_error!, semanticsLabel: _error),
                          if (_result case final result?) ...[
                            const SizedBox(height: 20),
                            Text(result.message,
                                key: const Key('goal-result'),
                                style: Theme.of(context).textTheme.titleMedium),
                            for (final step in result.nextSteps)
                              Text('• $step'),
                            Text(
                                '${t('নিয়মের সংস্করণ', 'Rules version')}: ${result.rulesVersion}'),
                            for (final plant in result.plants)
                              _PlantResult(
                                  plant: plant,
                                  language: _language,
                                  onPlan: () => _plan(plant)),
                          ],
                        ])))),
      );
}

class _Choice extends StatelessWidget {
  const _Choice(
      {required this.label,
      required this.id,
      required this.value,
      required this.options,
      required this.enabled,
      required this.change});
  final String label, id, value;
  final Map<String, String> options;
  final bool enabled;
  final ValueChanged<String> change;
  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: DropdownButtonFormField<String>(
          key: Key(id),
          initialValue: value,
          isExpanded: true,
          decoration: InputDecoration(labelText: label),
          items: [
            for (final entry in options.entries)
              DropdownMenuItem(value: entry.key, child: Text(entry.value))
          ],
          onChanged: enabled
              ? (v) {
                  if (v != null) change(v);
                }
              : null));
}

class _PlantResult extends StatelessWidget {
  const _PlantResult(
      {required this.plant, required this.language, required this.onPlan});
  final GoalPlant plant;
  final String language;
  final VoidCallback onPlan;
  String t(String bn, String en) => language == 'bn' ? bn : en;
  @override
  Widget build(BuildContext context) => Card(
      child: Padding(
          padding: const EdgeInsets.all(16),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${plant.bn} · ${plant.en}',
                style: Theme.of(context).textTheme.titleMedium),
            Text(plant.assessment == 'matching_conditions'
                ? t('পর্যালোচিত শর্তের মিল', 'Reviewed conditions match')
                : t('নিশ্চিতকরণ দরকার—এখনই রোপণের পরামর্শ নয়',
                    'Needs confirmation—not yet a planting recommendation')),
            Text('${plant.variety} · ${plant.profileId}'),
            Text(
                '${t('পর্যালোচনা / মেয়াদ', 'Review / expiry')}: ${plant.reviewedAt} / ${plant.validUntil}'),
            for (final reason in plant.reasons) Text('✓ $reason'),
            Text(t('অনিশ্চয়তা ও সীমাবদ্ধতা', 'Uncertainty and limits'),
                style: Theme.of(context).textTheme.titleSmall),
            for (final warning in plant.uncertainties) Text('• $warning'),
            Text(plant.limitations),
            OutlinedButton(
                onPressed: onPlan,
                child: Text(t('যত্ন পরিকল্পনা দেখুন', 'Preview care plan'))),
            ExpansionTile(
                title: Text(t('উৎস ও তথ্যের উল্লেখ', 'Sources and citations')),
                children: [
                  for (final source in plant.sources)
                    Padding(
                        padding: const EdgeInsets.all(8),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                  '${source.key}: ${source.title} · ${source.locator}'),
                              Text(source.note),
                              SelectableText(source.url),
                              Text(
                                  '${source.checkedAt} / ${source.validUntil} · ${source.license}'),
                              SelectableText(source.licenseUrl),
                              Text(source.attribution),
                            ])),
                ]),
          ])));
}
