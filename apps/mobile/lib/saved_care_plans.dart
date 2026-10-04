import 'package:flutter/material.dart';
import 'care_models.dart';
import 'care_plan_view.dart';
import 'goal_intake.dart';
import 'private_api.dart';

class SavedCarePlans extends StatefulWidget {
  const SavedCarePlans({super.key, required this.api});
  final PrivateApi api;
  @override
  State<SavedCarePlans> createState() => _SavedCarePlansState();
}

class _SavedCarePlansState extends State<SavedCarePlans> {
  final List<CareSummary> _rows = [];
  bool _busy = false, _more = true;
  String? _error;
  @override
  void initState() {
    super.initState();
    _load(reset: true);
  }

  Future<void> _load({bool reset = false}) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final rows = await widget.api
          .plans(after: reset || _rows.isEmpty ? null : _rows.last.id);
      if (mounted) {
        setState(() {
          if (reset) _rows.clear();
          _rows.addAll(rows);
          _more = rows.length == 20;
        });
      }
    } on PrivateApiException catch (e) {
      if (!mounted) return;
      if (e.signedOut) {
        Navigator.pop(context, true);
        return;
      }
      setState(() => _error = e.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Connection failed. Retry when online.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _open(CareSummary row) async {
    final expired = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
            builder: (_) => CarePlanView(
                api: widget.api,
                planId: row.id,
                onRevise: (v) => Navigator.push<bool>(
                    context,
                    MaterialPageRoute(
                        builder: (_) => GoalIntake(
                            api: widget.api,
                            initialGoal: v.conditions,
                            revisePlanId: v.id,
                            expectedVersion: v.version))))));
    if (!mounted) return;
    if (expired == true) {
      Navigator.pop(context, true);
      return;
    }
    _load(reset: true);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('যত্ন পরিকল্পনা · Saved care plans')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        const Text(
            'Saved status only—open a plan to recheck current evidence. সংরক্ষিত অবস্থা; বর্তমান উৎস যাচাই করতে পরিকল্পনা খুলুন।'),
        if (_busy) const LinearProgressIndicator(),
        if (_error != null) Text(_error!),
        TextButton(
            onPressed: _busy ? null : () => _load(reset: true),
            child: const Text('Refresh')),
        if (!_busy && _rows.isEmpty)
          const Text(
              'No saved plans. Generate a preview from a reviewed goal match first.'),
        for (final row in _rows)
          ListTile(
              title: Text('${row.bn} · ${row.en}'),
              subtitle: Text('Version ${row.version} · saved ${row.status}'),
              onTap: _busy ? null : () => _open(row)),
        if (_more && _rows.isNotEmpty)
          TextButton(
              onPressed: _busy ? null : _load, child: const Text('More')),
      ]));
}
