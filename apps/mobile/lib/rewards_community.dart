import 'package:flutter/material.dart';

import 'private_api.dart';

class RewardMilestone {
  RewardMilestone(Map<String, dynamic> json)
      : months = json['months'] as int,
        targetOn = json['target_on'] as String,
        status = json['status'] as String,
        points = json['points'] as int,
        note = json['note'] as String;
  final int months;
  final String targetOn;
  final String status;
  final int points;
  final String note;
}

class PlantReward {
  PlantReward(Map<String, dynamic> json)
      : nickname = json['nickname'] as String,
        currentStreakDays = json['current_streak_days'] as int,
        bestStreakDays = json['best_streak_days'] as int,
        score = json['score'] as int,
        milestones = (json['milestones'] as List)
            .map((x) => RewardMilestone(x as Map<String, dynamic>))
            .toList(growable: false);
  final String nickname;
  final int currentStreakDays;
  final int bestStreakDays;
  final int score;
  final List<RewardMilestone> milestones;
}

class RewardsSummary {
  RewardsSummary(Map<String, dynamic> json)
      : plantCount = json['plant_count'] as int,
        careDays = json['care_days'] as int,
        currentStreakDays = json['current_streak_days'] as int,
        bestStreakDays = json['best_streak_days'] as int,
        score = (json['score'] as num).toDouble(),
        scoreMethod = json['score_method'] as String,
        plants = (json['plants'] as List)
            .map((x) => PlantReward(x as Map<String, dynamic>))
            .toList(growable: false);
  final int plantCount;
  final int careDays;
  final int currentStreakDays;
  final int bestStreakDays;
  final double score;
  final String scoreMethod;
  final List<PlantReward> plants;
}

class CommunityProfile {
  CommunityProfile(Map<String, dynamic> json)
      : district = json['district'] as String,
        publicAlias = json['public_alias'] as String;
  final String district;
  final String publicAlias;
}

class CommunityPost {
  CommunityPost(Map<String, dynamic> json)
      : id = json['id'] as String,
        authorAlias = json['author_alias'] as String,
        topic = json['topic'] as String,
        body = json['body'] as String,
        status = json['status'] as String,
        createdAt = json['created_at'] as String;
  final String id;
  final String authorAlias;
  final String topic;
  final String body;
  final String status;
  final String createdAt;
}

class CommunityReportResponse {
  CommunityReportResponse(Map<String, dynamic> json)
      : accepted = json['accepted'] as bool,
        autoHidden = json['auto_hidden'] as bool;
  final bool accepted;
  final bool autoHidden;
}

class NeighborhoodSummary {
  NeighborhoodSummary(Map<String, dynamic> json)
      : district = json['district'] as String,
        available = json['available'] as bool,
        participatingGrowers = json['participating_growers'] as int,
        averageScore = (json['average_score'] as num?)?.toDouble(),
        averageStreak = (json['average_current_streak_days'] as num?)?.toDouble(),
        milestones3 = json['milestones_3_months'] as int,
        milestones6 = json['milestones_6_months'] as int,
        milestones12 = json['milestones_12_months'] as int,
        message = json['message'] as String;
  final String district;
  final bool available;
  final int participatingGrowers;
  final double? averageScore;
  final double? averageStreak;
  final int milestones3;
  final int milestones6;
  final int milestones12;
  final String message;
}

class RewardsCommunity extends StatefulWidget {
  const RewardsCommunity({
    super.key,
    required this.api,
    required this.communityEnabled,
    this.openSettings,
  });
  final PrivateApi api;
  final bool communityEnabled;
  final Future<void> Function()? openSettings;

  @override
  State<RewardsCommunity> createState() => _RewardsCommunityState();
}

class _RewardsCommunityState extends State<RewardsCommunity> {
  RewardsSummary? _rewards;
  CommunityProfile? _profile;
  NeighborhoodSummary? _neighborhood;
  List<CommunityPost> _posts = [];
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final rewards = await widget.api.rewards();
      final profile = await widget.api.communityProfile();
      final posts = await widget.api.communityFeed();
      NeighborhoodSummary? neighborhood;
      if (profile != null) {
        try {
          neighborhood = await widget.api.communityNeighborhood();
        } on PrivateApiException catch (error) {
          if (error.statusCode != 409) rethrow;
        }
      }
      if (mounted) {
        setState(() {
          _rewards = rewards;
          _profile = profile;
          _posts = posts;
          _neighborhood = neighborhood;
        });
      }
    } on PrivateApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Connection failed. Retry when online.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _profileDialog() async {
    if (!widget.communityEnabled) {
      await widget.openSettings?.call();
      return;
    }
    final result = await showDialog<List<String>>(
      context: context,
      builder: (_) => _ProfileDialog(existing: _profile),
    );
    if (result == null || !mounted) return;
    setState(() => _busy = true);
    try {
      await widget.api.saveCommunityProfile(result[0], result[1]);
      await _load();
    } on PrivateApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _postDialog() async {
    final result = await showDialog<List<String>>(
      context: context,
      builder: (_) => const _PostDialog(),
    );
    if (result == null || !mounted) return;
    setState(() => _busy = true);
    try {
      await widget.api.createCommunityPost(result[0], result[1]);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Submitted for moderation.')));
      }
      await _load();
    } on PrivateApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _report(CommunityPost post) async {
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => SimpleDialog(
        title: const Text('Report post'),
        children: [
          for (final value in const <String, String>{
            'harassment': 'Harassment',
            'unsafe_advice': 'Unsafe advice',
            'privacy': 'Privacy concern',
            'spam': 'Spam',
            'other': 'Other',
          }.entries)
            SimpleDialogOption(
                onPressed: () => Navigator.pop(context, value.key),
                child: Text(value.value)),
        ],
      ),
    );
    if (reason == null || !mounted) return;
    try {
      final result = await widget.api.reportCommunityPost(post.id, reason, '');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(result.autoHidden
                ? 'Report accepted; the post is hidden for review.'
                : 'Report accepted.')));
      }
      await _load();
    } on PrivateApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Rewards · Community')),
        body: ListView(padding: const EdgeInsets.all(20), children: [
          if (_busy) const LinearProgressIndicator(),
          if (_error != null) Text(_error!, key: const Key('rewards-error')),
          TextButton(onPressed: _busy ? null : _load, child: const Text('Refresh')),
          if (_rewards case final rewards?) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Garden score ${rewards.score.toStringAsFixed(1)} / 100',
                      style: Theme.of(context).textTheme.titleLarge),
                  Text('Current care streak: ${rewards.currentStreakDays} days'),
                  Text('Best care streak: ${rewards.bestStreakDays} days · ${rewards.careDays} care days'),
                  Text(rewards.scoreMethod),
                  const Text('Milestones are self-reported and do not verify plant survival.'),
                ]),
              ),
            ),
            for (final plant in rewards.plants)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${plant.nickname} · score ${plant.score}'),
                    Text('Streak ${plant.currentStreakDays} days · best ${plant.bestStreakDays}'),
                    for (final milestone in plant.milestones)
                      ListTile(
                        dense: true,
                        title: Text('${milestone.months}-month milestone · ${milestone.status}'),
                        subtitle: Text('${milestone.targetOn} · ${milestone.note}'),
                        trailing: milestone.status == 'earned'
                            ? const Icon(Icons.verified_outlined)
                            : null,
                      ),
                  ]),
                ),
              ),
          ],
          const Divider(),
          Text('Community', style: Theme.of(context).textTheme.titleLarge),
          Text(widget.communityEnabled
              ? 'Community is optional. Posts are reviewed before they appear.'
              : 'Enable community consent before creating a public profile.'),
          TextButton.icon(
              onPressed: _busy ? null : _profileDialog,
              icon: const Icon(Icons.public),
              label: Text(_profile == null ? 'Create community profile' : 'Edit community profile')),
          if (_profile != null) ...[
            Text('Public alias: ${_profile!.publicAlias} · district: ${_profile!.district}'),
            FilledButton.icon(
                onPressed: _busy ? null : _postDialog,
                icon: const Icon(Icons.edit_note),
                label: const Text('Write a moderated post')),
          ],
          if (_neighborhood case final neighborhood?)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Neighborhood · ${neighborhood.district}',
                      style: Theme.of(context).textTheme.titleMedium),
                  Text(neighborhood.message),
                  if (neighborhood.available) ...[
                    Text('Growers: ${neighborhood.participatingGrowers} · average score: ${neighborhood.averageScore}'),
                    Text('Average current streak: ${neighborhood.averageStreak} days'),
                    Text('Milestones: 3m ${neighborhood.milestones3} · 6m ${neighborhood.milestones6} · 12m ${neighborhood.milestones12}'),
                  ],
                ]),
              ),
            ),
          const SizedBox(height: 8),
          Text('Approved posts', style: Theme.of(context).textTheme.titleMedium),
          if (_posts.isEmpty) const Text('No approved posts yet.'),
          for (final post in _posts)
            Card(
              child: ListTile(
                title: Text('${post.authorAlias} · ${post.topic}'),
                subtitle: Text(post.body),
                trailing: IconButton(
                    tooltip: 'Report',
                    onPressed: _busy ? null : () => _report(post),
                    icon: const Icon(Icons.flag_outlined)),
              ),
            ),
          const Text('Exact addresses, private passports and private photos are never shown here.'),
        ]),
      );
}

class _ProfileDialog extends StatefulWidget {
  const _ProfileDialog({this.existing});
  final CommunityProfile? existing;
  @override
  State<_ProfileDialog> createState() => _ProfileDialogState();
}

class _ProfileDialogState extends State<_ProfileDialog> {
  late String _district = widget.existing?.district ?? 'dhaka';
  late final _alias = TextEditingController(text: widget.existing?.publicAlias ?? 'Garden grower');
  @override
  void dispose() { _alias.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Community profile'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          DropdownButtonFormField<String>(
              initialValue: _district,
              decoration: const InputDecoration(labelText: 'District (broad only)'),
              items: const ['dhaka','chattogram','rajshahi','khulna','sylhet','rangpur','barishal','mymensingh']
                  .map((value) => DropdownMenuItem(value: value, child: Text(value))).toList(),
              onChanged: (value) { if (value != null) setState(() => _district = value); }),
          TextField(controller: _alias, maxLength: 40, decoration: const InputDecoration(labelText: 'Public alias')),
          const Text('Only the alias and broad district aggregate can appear publicly.'),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () {
            final alias = _alias.text.trim();
            if (alias.length >= 3) Navigator.pop(context, [_district, alias]);
          }, child: const Text('Save')),
        ],
      );
}

class _PostDialog extends StatefulWidget {
  const _PostDialog();
  @override
  State<_PostDialog> createState() => _PostDialogState();
}

class _PostDialogState extends State<_PostDialog> {
  final _body = TextEditingController();
  String _topic = 'general';
  @override
  void dispose() { _body.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Moderated community post'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          DropdownButtonFormField<String>(
              initialValue: _topic,
              items: const {'milestone':'Milestone','care':'Care','question':'Question','general':'General'}
                  .entries.map((entry) => DropdownMenuItem(value: entry.key, child: Text(entry.value))).toList(),
              onChanged: (value) { if (value != null) setState(() => _topic = value); }),
          TextField(controller: _body, maxLength: 1000, maxLines: 5, decoration: const InputDecoration(labelText: 'Message')),
          const Text('Do not include addresses, phone numbers or private photos.'),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () {
            final body = _body.text.trim();
            if (body.isNotEmpty) Navigator.pop(context, [_topic, body]);
          }, child: const Text('Submit for review')),
        ],
      );
}
