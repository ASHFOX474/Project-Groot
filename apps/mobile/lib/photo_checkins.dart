import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'private_api.dart';

class PhotoConsent {
  const PhotoConsent(this.storage, this.health, [this.generation = 0]);
  final bool storage;
  final bool health;
  final int generation;
  factory PhotoConsent.fromJson(Map<String, dynamic> json) => PhotoConsent(
      json['storage'] as bool,
      json['health'] as bool,
      json['generation'] as int? ?? 0);
}

abstract interface class PhotoPicker {
  Future<Uint8List?> pick();
  Future<void> expert();
}

class AndroidPhotoPicker implements PhotoPicker {
  static const channel = MethodChannel('bd.groot/photos');
  @override
  Future<Uint8List?> pick() => channel.invokeMethod<Uint8List>('pick');
  @override
  Future<void> expert() => channel.invokeMethod<void>('expert');
}

String photoOperationId() {
  final random = Random.secure();
  final bytes = List.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final h = bytes.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-${h.substring(16, 20)}-${h.substring(20)}';
}

class PhotoCheckins extends StatefulWidget {
  const PhotoCheckins(
      {super.key, required this.api, required this.plant, this.picker});
  final PrivateApi api;
  final PlantPassport plant;
  final PhotoPicker? picker;
  @override
  State<PhotoCheckins> createState() => _PhotoCheckinsState();
}

class _PhotoCheckinsState extends State<PhotoCheckins>
    with WidgetsBindingObserver {
  late final _picker = widget.picker ?? AndroidPhotoPicker();
  PhotoConsent _consent = const PhotoConsent(false, false);
  List<Map<String, dynamic>> _photos = [];
  Uint8List? _selected;
  Map<String, dynamic>? _pending;
  final _caption = TextEditingController();
  final _date = TextEditingController(
      text: bangladeshToday().toIso8601String().substring(0, 10));
  final _symptoms = <String>{};
  bool _busy = false, _more = false, _rights = false;
  String? _message;
  final Map<String, Uint8List> _images = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _run(_load);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _selected = null;
    _pending = null;
    _images.clear();
    _caption.dispose();
    _date.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused && mounted) {
      setState(_images.clear); // No persistent image cache.
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
    } on PrivateApiException catch (e) {
      if (mounted && e.signedOut) {
        Navigator.pop(context, true);
      } else if (mounted) {
        setState(() => _message = e.message);
      }
    } on PlatformException catch (_) {
      if (mounted) {
        setState(() => _message =
            'Photo picker/dialer unavailable. Choose a single JPEG/PNG up to3MiB/12MP, or dial16123 yourself.');
      }
    } catch (_) {
      if (mounted) {
        setState(() => _message =
            'Connection failed. Retry uses the same check-in ID while this page stays open. After leaving/restarting, refresh the timeline before another upload.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _load({bool more = false}) async {
    final consent =
        PhotoConsent.fromJson(await widget.api.photoConsent(widget.plant.id));
    final rows = await widget.api.photos(widget.plant.id,
        after:
            more && _photos.isNotEmpty ? _photos.last['id'] as String : null);
    if (!mounted) return;
    setState(() {
      _consent = consent;
      _photos = more ? [..._photos, ...rows] : rows;
      _more = rows.length == 20;
      _images.clear();
      if (!consent.health) _symptoms.clear();
    });
  }

  Future<bool> _confirm(String title, String text) async =>
      await showDialog<bool>(
          context: context,
          builder: (c) =>
              AlertDialog(title: Text(title), content: Text(text), actions: [
                TextButton(
                    onPressed: () => Navigator.pop(c, false),
                    child: const Text('Cancel')),
                FilledButton(
                    onPressed: () => Navigator.pop(c, true),
                    child: const Text('Confirm'))
              ])) ==
      true;
  Future<void> _choices() async {
    var storage = _consent.storage, health = _consent.health;
    final saved = await showDialog<bool>(
        context: context,
        builder: (c) => StatefulBuilder(
            builder: (c, update) => AlertDialog(
                    title: const Text('Private photo choices'),
                    content: SingleChildScrollView(
                        child:
                            Column(mainAxisSize: MainAxisSize.min, children: [
                      const Text(
                          'Notice2026-10-05-photos-v1. Store only photos you own/may upload. No GPS, public sharing, external model provider or training use. Photos/notes are private to your account, but readable by the server operator and backups. Raw metadata is stripped; background/location clues in pixels remain. Health assistance is unvalidated color/user-symptom observation, NOT disease diagnosis or treatment. Limits:50 per plant/100 per account. Withdrawing storage permanently deletes this plant’s active photos; withdrawing health removes all saved assistance and symptom choices. Backups may retain earlier data under operator retention policy.'),
                      SwitchListTile(
                          title: const Text('Private photo storage'),
                          value: storage,
                          onChanged: (v) => update(() {
                                storage = v;
                                if (!v) health = false;
                              })),
                      SwitchListTile(
                          title: const Text('Uncertain health assistance'),
                          value: health,
                          onChanged:
                              storage ? (v) => update(() => health = v) : null)
                    ])),
                    actions: [
                      TextButton(
                          onPressed: () => Navigator.pop(c, false),
                          child: const Text('Cancel')),
                      FilledButton(
                          onPressed: () => Navigator.pop(c, true),
                          child: const Text('Save choices'))
                    ])));
    if (saved != true || !mounted) return;
    if ((_consent.storage && !storage) || (_consent.health && !health)) {
      if (!await _confirm(
          'Withdraw photo use?',
          !storage
              ? 'Permanently delete all active photos for this plant, including their notes and assistance? This cannot be undone.'
              : 'Delete saved health assistance and symptom choices for this plant? Private photos/captions remain.')) {
        return;
      }
    }
    if (!mounted) return;
    await _run(() async {
      await widget.api.setPhotoConsent(widget.plant.id, storage, health);
      _selected = null;
      _pending = null;
      _rights = false;
      await _load();
    });
  }

  Future<void> _upload() => _run(() async {
        final parsed = DateTime.tryParse(_date.text);
        if (_pending == null &&
            (parsed == null ||
                parsed.toIso8601String().substring(0, 10) != _date.text ||
                _date.text.compareTo(widget.plant.plantedOn) < 0 ||
                parsed.isAfter(bangladeshToday()))) {
          setState(() =>
              _message = 'Use a valid photo date from planting through today.');
          return;
        }
        final selected = _selected;
        if (selected == null || !_rights) return;
        _pending ??= {
          'consent_generation': _consent.generation,
          'request_id': photoOperationId(),
          'observed_on': _date.text,
          'media_type': 'image/jpeg',
          'image_base64': base64Encode(selected),
          'caption': _caption.text,
          'symptoms': _consent.health ? _symptoms.toList() : [],
          'rights_confirmed': true
        };
        await widget.api.uploadPhoto(widget.plant.id, _pending!);
        if (!mounted) return;
        _pending = null;
        _selected = null;
        _rights = false;
        _caption.clear();
        _symptoms.clear();
        await _load();
      });

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: Text('${widget.plant.nickname} · ছবি')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        const Text(
            'Private photo check-ins · ব্যক্তিগত ছবি\nDates are self-reported; photos do not prove care or survival. Online only; no offline photo queue.'),
        if (_busy) const LinearProgressIndicator(),
        if (_message != null) Text(_message!, key: const Key('photo-message')),
        Wrap(spacing: 8, children: [
          TextButton(
              onPressed: _busy ? null : _choices,
              child: const Text('Photo choices')),
          TextButton(
              onPressed: _busy ? null : () => _run(_load),
              child: const Text('Refresh photo timeline')),
          TextButton(
              onPressed: _busy ? null : () => _run(_picker.expert),
              child: const Text('Expert help ·16123'))
        ]),
        const Text(
            'Serious, worsening or uncertain symptoms: seek an agricultural expert.16123 is officially listed; current phone availability/hours are not verified. If unavailable, contact your local extension office. Nothing is shared automatically.'),
        if (!_consent.storage)
          const Text(
              'Private photo storage is off. Enable it separately in Photo choices.'),
        if (_consent.storage) ...[
          Text(_consent.health
              ? 'Health assistance: low, uncalibrated confidence—not a diagnosis.'
              : 'Health assistance is off. Uploading stores a photo only.'),
          OutlinedButton(
              onPressed: _busy || _pending != null
                  ? null
                  : () => _run(() async {
                        final data = await _picker.pick();
                        if (mounted && data != null) {
                          if (data.length > 524288) {
                            throw const FormatException('Photo too large');
                          }
                          setState(() => _selected = data);
                        }
                      }),
              child: const Text('Choose one photo')),
          if (_selected != null)
            Image.memory(_selected!, height: 160, fit: BoxFit.contain),
          TextField(
              controller: _date,
              enabled: !_busy && _pending == null,
              decoration:
                  const InputDecoration(labelText: 'Photo date · YYYY-MM-DD')),
          TextField(
              controller: _caption,
              enabled: !_busy && _pending == null,
              maxLength: 500,
              decoration: const InputDecoration(
                  labelText: 'Optional note · no address/personal details')),
          if (_consent.health)
            Wrap(spacing: 6, children: [
              for (final symptom in [
                'yellowing',
                'spots',
                'wilting',
                'visible_pests',
                'rapid_decline'
              ])
                FilterChip(
                    label: Text('I observed: ${symptom.replaceAll('_', ' ')}'),
                    selected: _symptoms.contains(symptom),
                    onSelected: _busy || _pending != null
                        ? null
                        : (v) => setState(() {
                              v
                                  ? _symptoms.add(symptom)
                                  : _symptoms.remove(symptom);
                            }))
            ]),
          CheckboxListTile(
              title: const Text(
                  'I own/have permission to upload this photo; it contains no other people’s private information.'),
              value: _rights,
              onChanged: _busy || _pending != null
                  ? null
                  : (v) => setState(() => _rights = v ?? false)),
          if (_pending != null)
            const Text(
                'Retry keeps the original image/date/note/ID. If you leave this page, refresh history before another upload.'),
          if (_pending != null)
            TextButton(
                onPressed: _busy
                    ? null
                    : () async {
                        if (await _confirm('Discard local retry?',
                            'Refresh and inspect the live timeline first: the server may already have saved this photo. Discarding only clears this page’s retry data, not a server photo. Do not upload the same check-in again if it is already there.')) {
                          if (!mounted) return;
                          setState(() {
                            _pending = null;
                            _selected = null;
                            _rights = false;
                          });
                        }
                      },
                child:
                    const Text('Discard local retry after checking history')),
          FilledButton(
              onPressed:
                  _busy || _selected == null || !_rights ? null : _upload,
              child: Text(_pending == null
                  ? 'Upload private check-in'
                  : 'Retry same check-in')),
        ],
        const Divider(),
        for (final photo in _photos)
          Card(
              child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                            'Observed ${photo['observed_on']} · uploaded ${photo['uploaded_at']}'),
                        Text(photo['caption'] as String),
                        if (_images[photo['id']] case final bytes?)
                          Image.memory(bytes, height: 200, fit: BoxFit.contain),
                        TextButton(
                            onPressed: _busy
                                ? null
                                : () => _run(() async {
                                      final bytes = await widget.api.photoImage(
                                          widget.plant.id,
                                          photo['id'] as String);
                                      if (mounted) {
                                        setState(() {
                                          _images
                                              .clear(); // At most one decrypted photo held in memory.
                                          _images[photo['id'] as String] =
                                              bytes;
                                        });
                                      }
                                    }),
                            child: const Text('View private photo')),
                        if (photo['assistance']
                            case final Map<String, dynamic> health) ...[
                          const Text(
                              'Possible observations · LOW / UNCALIBRATED · probability unavailable'),
                          Text(
                              '${health['message_bn']}\n${health['message_en']}'),
                          Text('Image quality: ${health['quality']}'),
                          for (final flag in health['flags'] as List)
                            Text(
                                '${flag['message_bn']}\n${flag['message_en']}\nBasis: ${flag['basis']}'),
                          if (health['urgent'] == true)
                            const Text(
                                'Rapid decline reported: seek expert help promptly.'),
                        ] else
                          const Text(
                              'Health assistance off / withdrawn. No diagnosis made.'),
                        TextButton(
                            onPressed: _busy
                                ? null
                                : () async {
                                    if (await _confirm('Delete private photo?',
                                        'Permanently remove this check-in, image and assistance from active storage? Backups may retain earlier copies.')) {
                                      if (!mounted) return;
                                      await _run(() async {
                                        await widget.api.deletePhoto(
                                            widget.plant.id,
                                            photo['id'] as String);
                                        await _load();
                                      });
                                    }
                                  },
                            child: const Text('Delete photo'))
                      ]))),
        if (_photos.isEmpty && !_busy)
          const Text('No private photo check-ins yet.'),
        if (_more)
          TextButton(
              onPressed: _busy ? null : () => _run(() => _load(more: true)),
              child: const Text('Load more photos')),
      ]));
}
