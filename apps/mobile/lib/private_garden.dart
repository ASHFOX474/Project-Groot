import 'package:flutter/material.dart';

import 'private_api.dart';
import 'goal_intake.dart';
import 'saved_care_plans.dart';

const _privacyNotice =
    'Your handle, password hash, consent choices and plant records are stored '
    'in this project’s database. Plants and care history are private to your account. '
    'No GPS, photos, analytics or public sharing are collected by this version. '
    'Optional choices are off by default and editable. Use test data on the local HTTP preview. '
    'No email recovery exists yet. Keep your password safely; restarting the app requires sign-in.';

class PrivateGarden extends StatefulWidget {
  const PrivateGarden({super.key, this.api});
  final PrivateApi? api;
  @override
  State<PrivateGarden> createState() => _PrivateGardenState();
}

class _PrivateGardenState extends State<PrivateGarden> {
  late final PrivateApi _api = widget.api ?? PrivateApi();
  GrowerAccount? _account;
  List<PlantPassport> _plants = [];
  bool _busy = false;
  bool _more = false;
  String? _error;

  @override
  void dispose() {
    if (widget.api == null) _api.close();
    super.dispose();
  }

  void _clear() {
    setState(() {
      _account = null;
      _plants = [];
      _more = false;
    });
  }

  Future<void> _run(Future<void> Function() operation) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await operation();
    } on PrivateApiException catch (e) {
      if (mounted) {
        if (e.signedOut) _clear();
        setState(() => _error = e.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Connection failed. Retry when online.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _load({bool more = false}) async {
    final batch = await _api.plants(
        after: more && _plants.isNotEmpty ? _plants.last.id : null);
    if (mounted) {
      setState(() {
        _plants = more ? [..._plants, ...batch] : batch;
        _more = batch.length == 20;
      });
    }
  }

  Future<void> _settings() async {
    final account = _account;
    if (account == null) return;
    final choices = await showDialog<ConsentChoices>(
        context: context,
        builder: (_) => _ConsentDialog(choices: account.choices));
    if (choices == null || !mounted) return;
    await _run(() async {
      final updated = await _api.consent(choices);
      if (mounted) setState(() => _account = updated);
    });
  }

  Future<void> _credentials({bool delete = false}) async {
    final values = await showDialog<List<String>>(
        context: context, builder: (_) => _PasswordDialog(delete: delete));
    if (values == null || !mounted) return;
    await _run(() async {
      if (delete) {
        await _api.deleteAccount(values[0]);
      } else {
        await _api.changePassword(values[0], values[1]);
      }
      if (mounted) _clear();
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('আমার গাছ · Plant Passports')),
        body: SafeArea(
            child: _account == null
                ? _SignInForm(
                    busy: _busy,
                    error: _error,
                    submit: (handle, password, register, choices) =>
                        _run(() async {
                          final account = await _api.signIn(handle, password,
                              register: register, choices: choices);
                          if (!mounted) return;
                          setState(() => _account = account);
                          await _load();
                        }))
                : Column(children: [
                    Wrap(spacing: 8, children: [
                      TextButton(
                          onPressed: _busy ? null : _settings,
                          child: const Text('Consent choices')),
                      TextButton(
                          onPressed: _busy ? null : () => _credentials(),
                          child: const Text('Password')),
                      TextButton(
                          onPressed:
                              _busy ? null : () => _credentials(delete: true),
                          child: const Text('Delete account')),
                      TextButton(
                          onPressed: _busy
                              ? null
                              : () => _run(() async {
                                    try {
                                      await _api.logout();
                                    } finally {
                                      if (mounted) _clear();
                                    }
                                  }),
                          child: const Text('Sign out')),
                    ]),
                    Text('Private garden · ${_account?.handle}'),
                    TextButton.icon(
                        onPressed: _busy
                            ? null
                            : () async {
                                final expired = await Navigator.of(context)
                                    .push<bool>(MaterialPageRoute(
                                        builder: (_) => GoalIntake(api: _api)));
                                if (mounted && expired == true) _clear();
                              },
                        icon: const Icon(Icons.eco_outlined),
                        label:
                            const Text('লক্ষ্য ও উপযুক্ত গাছ · Plan a goal')),
                    TextButton.icon(
                        onPressed: _busy
                            ? null
                            : () async {
                                final expired = await Navigator.of(context)
                                    .push<bool>(MaterialPageRoute(
                                        builder: (_) =>
                                            SavedCarePlans(api: _api)));
                                if (mounted && expired == true) _clear();
                              },
                        icon: const Icon(Icons.history),
                        label: const Text('যত্ন পরিকল্পনা · Saved care plans')),
                    if (_busy) const LinearProgressIndicator(),
                    if (_error != null) Text(_error!, semanticsLabel: _error),
                    TextButton(
                        onPressed: _busy ? null : () => _run(() => _load()),
                        child: const Text('Refresh')),
                    Expanded(
                        child: _plants.isEmpty
                            ? const Center(
                                child: Text(
                                    'No plants yet. Add your first private passport.'))
                            : ListView(children: [
                                for (final plant in _plants)
                                  ListTile(
                                      title: Text(plant.nickname),
                                      subtitle: Text(
                                          '${plant.species} · planted ${plant.plantedOn}'),
                                      trailing: const Icon(Icons.lock_outline),
                                      onTap: _busy
                                          ? null
                                          : () async {
                                              await Navigator.of(context).push(
                                                  MaterialPageRoute<void>(
                                                      builder: (_) =>
                                                          _PassportDetail(
                                                              api: _api,
                                                              plant: plant,
                                                              signedOut:
                                                                  _clear)));
                                              if (mounted && _account != null) {
                                                await _run(() => _load());
                                              }
                                            }),
                                if (_more)
                                  TextButton(
                                      onPressed: _busy
                                          ? null
                                          : () => _run(() => _load(more: true)),
                                      child: const Text('Load more plants')),
                              ])),
                    Padding(
                        padding: const EdgeInsets.all(12),
                        child: FilledButton.icon(
                            icon: const Icon(Icons.add),
                            label: const Text('Add plant'),
                            onPressed: _busy
                                ? null
                                : () async {
                                    final plant = await Navigator.of(context)
                                        .push<PlantPassport>(MaterialPageRoute(
                                            builder: (_) =>
                                                const _PassportForm()));
                                    if (plant == null || !mounted) return;
                                    await _run(() async {
                                      await _api.save(plant, create: true);
                                      await _load();
                                    });
                                  })),
                  ])),
      );
}

class _SignInForm extends StatefulWidget {
  const _SignInForm(
      {required this.busy, required this.error, required this.submit});
  final bool busy;
  final String? error;
  final Future<void> Function(String, String, bool, ConsentChoices) submit;
  @override
  State<_SignInForm> createState() => _SignInFormState();
}

class _SignInFormState extends State<_SignInForm> {
  final _form = GlobalKey<FormState>();
  final _handle = TextEditingController();
  final _password = TextEditingController();
  bool _register = false;
  ConsentChoices _choices = const ConsentChoices();
  @override
  void dispose() {
    _handle.dispose();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Form(
      key: _form,
      child: ListView(padding: const EdgeInsets.all(20), children: [
        const Text('Private accounts', style: TextStyle(fontSize: 22)),
        const Text(_privacyNotice),
        const SizedBox(height: 16),
        TextFormField(
            controller: _handle,
            decoration: const InputDecoration(
                labelText: 'Handle (3–32 letters, digits, _)'),
            autocorrect: false,
            enableSuggestions: false,
            maxLength: 32,
            validator: (v) => RegExp(r'^[a-z0-9_]{3,32}$')
                    .hasMatch((v ?? '').trim().toLowerCase())
                ? null
                : 'Use a valid handle.'),
        TextFormField(
            controller: _password,
            obscureText: true,
            autocorrect: false,
            enableSuggestions: false,
            decoration: const InputDecoration(
                labelText: 'Password (15–128 characters)'),
            maxLength: 128,
            validator: (v) =>
                (v?.length ?? 0) >= 15 ? null : 'Use at least 15 characters.'),
        SwitchListTile(
            title: const Text('Create a new account'),
            value: _register,
            onChanged:
                widget.busy ? null : (v) => setState(() => _register = v)),
        if (_register)
          ConsentControls(
              choices: _choices,
              enabled: !widget.busy,
              changed: (v) => setState(() => _choices = v)),
        if (widget.error != null) Text(widget.error!),
        FilledButton(
            onPressed: widget.busy
                ? null
                : () async {
                    if (_form.currentState?.validate() != true) return;
                    final password = _password.text;
                    _password.clear();
                    await widget.submit(
                        _handle.text, password, _register, _choices);
                  },
            child: Text(widget.busy
                ? 'Please wait…'
                : _register
                    ? 'Create account'
                    : 'Sign in')),
      ]));
}

class ConsentControls extends StatelessWidget {
  const ConsentControls(
      {super.key,
      required this.choices,
      required this.changed,
      this.enabled = true});
  final ConsentChoices choices;
  final ValueChanged<ConsentChoices> changed;
  final bool enabled;
  @override
  Widget build(BuildContext context) => Column(children: [
        const Text(
            'Optional choices · features not active yet. No collection or sharing is enabled here.'),
        SwitchListTile(
            title: const Text('Allow precise location on future check-ins'),
            value: choices.location,
            onChanged: enabled
                ? (v) => changed(ConsentChoices(
                    location: v,
                    community: choices.community,
                    impact: choices.impact))
                : null),
        SwitchListTile(
            title: const Text('Allow future community photo sharing'),
            value: choices.community,
            onChanged: enabled
                ? (v) => changed(ConsentChoices(
                    location: choices.location,
                    community: v,
                    impact: choices.impact))
                : null),
        SwitchListTile(
            title: const Text('Allow aggregate survival impact statistics'),
            value: choices.impact,
            onChanged: enabled
                ? (v) => changed(ConsentChoices(
                    location: choices.location,
                    community: choices.community,
                    impact: v))
                : null),
      ]);
}

class _ConsentDialog extends StatefulWidget {
  const _ConsentDialog({required this.choices});
  final ConsentChoices choices;
  @override
  State<_ConsentDialog> createState() => _ConsentDialogState();
}

class _ConsentDialogState extends State<_ConsentDialog> {
  late ConsentChoices _choices = widget.choices;
  @override
  Widget build(BuildContext context) => AlertDialog(
          title: const Text('Consent choices'),
          content: SingleChildScrollView(
              child: ConsentControls(
                  choices: _choices,
                  changed: (v) => setState(() => _choices = v))),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel')),
            FilledButton(
                onPressed: () => Navigator.pop(context, _choices),
                child: const Text('Save choices'))
          ]);
}

class _PasswordDialog extends StatefulWidget {
  const _PasswordDialog({this.delete = false});
  final bool delete;
  @override
  State<_PasswordDialog> createState() => _PasswordDialogState();
}

class _PasswordDialogState extends State<_PasswordDialog> {
  final _current = TextEditingController();
  final _replacement = TextEditingController();
  final _form = GlobalKey<FormState>();
  @override
  void dispose() {
    _current.dispose();
    _replacement.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
          title: Text(widget.delete
              ? 'Permanently delete account?'
              : 'Change password'),
          content: Form(
              key: _form,
              child: SingleChildScrollView(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(widget.delete
                    ? 'This deletes all your passports, care history and consent records from the active database. Backups may remain.'
                    : 'All sessions will end. Sign in with your new password.'),
                TextFormField(
                    controller: _current,
                    obscureText: true,
                    enableSuggestions: false,
                    autocorrect: false,
                    decoration:
                        const InputDecoration(labelText: 'Current password'),
                    validator: (v) =>
                        (v?.isNotEmpty ?? false) ? null : 'Required'),
                if (!widget.delete)
                  TextFormField(
                      controller: _replacement,
                      obscureText: true,
                      enableSuggestions: false,
                      autocorrect: false,
                      decoration:
                          const InputDecoration(labelText: 'New password'),
                      maxLength: 128,
                      validator: (v) => (v?.length ?? 0) >= 15
                          ? null
                          : 'At least 15 characters'),
              ]))),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel')),
            FilledButton(
                onPressed: () {
                  if (_form.currentState?.validate() == true) {
                    Navigator.pop(context, [_current.text, _replacement.text]);
                  }
                },
                child: Text(
                    widget.delete ? 'Delete permanently' : 'Change password'))
          ]);
}

class _PassportForm extends StatefulWidget {
  const _PassportForm({this.plant});
  final PlantPassport? plant;
  @override
  State<_PassportForm> createState() => _PassportFormState();
}

class _PassportFormState extends State<_PassportForm> {
  final _form = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.plant?.nickname);
  late final _species = TextEditingController(text: widget.plant?.species);
  late final _soil = TextEditingController(
      text: widget.plant?.conditions['soil'] as String? ?? 'Unknown');
  late final _area = TextEditingController(
      text: widget.plant?.conditions['approximate_area'] as String?);
  late String _context =
      widget.plant?.conditions['growing_context'] as String? ?? 'container';
  late String _sun =
      widget.plant?.conditions['sunlight'] as String? ?? 'unknown';
  late String _date = widget.plant?.plantedOn ??
      bangladeshToday().toIso8601String().substring(0, 10);
  @override
  void dispose() {
    _name.dispose();
    _species.dispose();
    _soil.dispose();
    _area.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Plant Passport')),
      body: SafeArea(
          child: Form(
              key: _form,
              child: ListView(padding: const EdgeInsets.all(20), children: [
                const Text(
                    'Private record, not a planting recommendation. Species identification is self-reported.'),
                TextFormField(
                    controller: _name,
                    maxLength: 80,
                    decoration:
                        const InputDecoration(labelText: 'Plant nickname'),
                    validator: _required),
                TextFormField(
                    controller: _species,
                    maxLength: 160,
                    decoration: const InputDecoration(
                        labelText: 'Species name (your identification)'),
                    validator: _required),
                ListTile(
                    title: Text('Planting date · $_date'),
                    trailing: const Icon(Icons.calendar_month),
                    onTap: () async {
                      final picked = await showDatePicker(
                          context: context,
                          initialDate: DateTime.parse(_date),
                          firstDate: DateTime(1900),
                          lastDate: bangladeshToday());
                      if (picked != null && mounted) {
                        setState(() =>
                            _date = picked.toIso8601String().substring(0, 10));
                      }
                    }),
                DropdownButtonFormField<String>(
                    initialValue: _context,
                    decoration:
                        const InputDecoration(labelText: 'Growing space'),
                    items: [
                      for (final x in ['container', 'open_ground', 'forestry'])
                        DropdownMenuItem(value: x, child: Text(x))
                    ],
                    onChanged: (v) {
                      if (v != null) _context = v;
                    }),
                DropdownButtonFormField<String>(
                    initialValue: _sun,
                    decoration: const InputDecoration(labelText: 'Sunlight'),
                    items: [
                      for (final x in [
                        'unknown',
                        'full_sun',
                        'partial_shade',
                        'shade'
                      ])
                        DropdownMenuItem(value: x, child: Text(x))
                    ],
                    onChanged: (v) {
                      if (v != null) _sun = v;
                    }),
                TextFormField(
                    controller: _soil,
                    maxLength: 300,
                    decoration: const InputDecoration(
                        labelText:
                            'Soil or potting conditions (Unknown is okay)'),
                    validator: _required),
                TextFormField(
                    controller: _area,
                    maxLength: 100,
                    decoration: const InputDecoration(
                        labelText:
                            'Approximate area (optional; no address/GPS)')),
                FilledButton(
                    onPressed: () {
                      if (_form.currentState?.validate() != true) return;
                      Navigator.pop(
                          context,
                          PlantPassport(
                              id: widget.plant?.id ?? '',
                              nickname: _name.text.trim(),
                              species: _species.text.trim(),
                              // Editing the identification invalidates an old reference instead of keeping a mismatched species ID.
                              speciesId:
                                  _species.text.trim() == widget.plant?.species
                                      ? widget.plant?.speciesId
                                      : null,
                              plantedOn: _date,
                              conditions: {
                                'growing_context': _context,
                                'sunlight': _sun,
                                'soil': _soil.text.trim(),
                                'approximate_area': _area.text.trim()
                              }));
                    },
                    child: const Text('Save passport')),
              ]))));
  String? _required(String? value) =>
      (value?.trim().isNotEmpty ?? false) ? null : 'Required';
}

class _PassportDetail extends StatefulWidget {
  const _PassportDetail(
      {required this.api, required this.plant, required this.signedOut});
  final PrivateApi api;
  final PlantPassport plant;
  final VoidCallback signedOut;
  @override
  State<_PassportDetail> createState() => _PassportDetailState();
}

class _PassportDetailState extends State<_PassportDetail> {
  late PlantPassport _plant = widget.plant;
  List<CareEvent> _care = [];
  bool _busy = true;
  bool _more = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    _run(() => _load());
  }

  Future<void> _run(Future<void> Function() operation) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await operation();
    } on PrivateApiException catch (e) {
      if (mounted) {
        if (e.signedOut) {
          widget.signedOut();
          Navigator.pop(context);
        } else {
          setState(() => _error = e.message);
        }
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Connection failed. Retry when online.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _load({bool more = false}) async {
    final items = await widget.api.care(_plant.id,
        after: more && _care.isNotEmpty ? _care.last.id : null);
    if (mounted) {
      setState(() {
        _care = more ? [..._care, ...items] : items;
        _more = items.length == 20;
      });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: Text(_plant.nickname)),
      body: SafeArea(
          child: ListView(padding: const EdgeInsets.all(20), children: [
        Text('${_plant.species} · planted ${_plant.plantedOn}'),
        Text(
            'Space: ${_plant.conditions['growing_context']} · Sun: ${_plant.conditions['sunlight']}'),
        Text(
            'Soil: ${_plant.conditions['soil']}\nArea: ${_plant.conditions['approximate_area'] ?? ''}'),
        const Text(
            'Private, self-reported care history. No AI verification or rewards.'),
        if (_busy) const LinearProgressIndicator(),
        if (_error != null) Text(_error!),
        Wrap(spacing: 8, children: [
          TextButton(
              onPressed: _busy ? null : () => _run(() => _load()),
              child: const Text('Refresh history')),
          TextButton(
              onPressed: _busy
                  ? null
                  : () async {
                      final updated = await Navigator.of(context)
                          .push<PlantPassport>(MaterialPageRoute(
                              builder: (_) => _PassportForm(plant: _plant)));
                      if (updated == null || !mounted) return;
                      await _run(() async {
                        final saved = await widget.api.save(updated);
                        if (mounted) setState(() => _plant = saved);
                      });
                    },
              child: const Text('Edit passport')),
          TextButton(
              onPressed: _busy
                  ? null
                  : () async {
                      final confirmed = await showDialog<bool>(
                          context: context,
                          builder: (_) => AlertDialog(
                                  title: const Text(
                                      'Delete plant and care history?'),
                                  content: const Text(
                                      'This cannot be undone in the app.'),
                                  actions: [
                                    TextButton(
                                        onPressed: () =>
                                            Navigator.pop(context, false),
                                        child: const Text('Cancel')),
                                    FilledButton(
                                        onPressed: () =>
                                            Navigator.pop(context, true),
                                        child: const Text('Delete plant'))
                                  ]));
                      if (confirmed != true || !mounted) return;
                      await _run(() async {
                        await widget.api.deletePlant(_plant.id);
                        if (mounted) Navigator.pop(this.context);
                      });
                    },
              child: const Text('Delete plant')),
        ]),
        for (final event in _care)
          ListTile(
              title: Text('${event.date} · ${event.kind}'),
              subtitle: Text(event.note)),
        if (_care.isEmpty && !_busy) const Text('No care logged yet.'),
        if (_more)
          TextButton(
              onPressed: _busy ? null : () => _run(() => _load(more: true)),
              child: const Text('Load more history')),
        FilledButton(
            onPressed: _busy
                ? null
                : () async {
                    final event = await Navigator.of(context).push<CareEvent>(
                        MaterialPageRoute(
                            builder: (_) =>
                                _CareForm(plantedOn: _plant.plantedOn)));
                    if (event == null || !mounted) return;
                    await _run(() async {
                      await widget.api.addCare(
                          _plant.id, event.kind, event.date, event.note);
                      await _load();
                    });
                  },
            child: const Text('Log care')),
      ])));
}

class _CareForm extends StatefulWidget {
  const _CareForm({required this.plantedOn});
  final String plantedOn;
  @override
  State<_CareForm> createState() => _CareFormState();
}

class _CareFormState extends State<_CareForm> {
  final _note = TextEditingController();
  String _kind = 'watering';
  String _date = bangladeshToday().toIso8601String().substring(0, 10);
  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Log care')),
      body: SafeArea(
          child: ListView(padding: const EdgeInsets.all(20), children: [
        DropdownButtonFormField<String>(
            initialValue: _kind,
            decoration: const InputDecoration(labelText: 'Care action'),
            items: [
              for (final x in [
                'watering',
                'feeding',
                'pruning',
                'repotting',
                'observation'
              ])
                DropdownMenuItem(value: x, child: Text(x))
            ],
            onChanged: (v) {
              if (v != null) _kind = v;
            }),
        ListTile(
            title: Text('Care date · $_date'),
            onTap: () async {
              final picked = await showDatePicker(
                  context: context,
                  initialDate: DateTime.parse(_date),
                  firstDate: DateTime.parse(widget.plantedOn),
                  lastDate: bangladeshToday());
              if (picked != null && mounted) {
                setState(
                    () => _date = picked.toIso8601String().substring(0, 10));
              }
            }),
        TextField(
            controller: _note,
            maxLength: 1000,
            maxLines: 4,
            decoration:
                const InputDecoration(labelText: 'Care notes (optional)')),
        FilledButton(
            onPressed: () => Navigator.pop(
                context, CareEvent('', _kind, _date, _note.text.trim())),
            child: const Text('Save care')),
      ])));
}
