import 'package:flutter_test/flutter_test.dart';
import 'package:groot_app/rewards_community.dart';

void main() {
  test('reward and community contracts parse bounded public fields', () {
    final rewards = RewardsSummary({
      'plant_count': 1,
      'care_days': 3,
      'current_streak_days': 2,
      'best_streak_days': 4,
      'score': 51.5,
      'score_method': 'Average of capped per-plant scores',
      'plants': [
        {
          'nickname': 'Okra',
          'current_streak_days': 2,
          'best_streak_days': 4,
          'score': 51,
          'milestones': [
            {
              'months': 3,
              'target_on': '2026-07-06',
              'status': 'earned',
              'points': 25,
              'note': 'Self-reported',
            }
          ],
        }
      ],
    });
    expect(rewards.score, 51.5);
    expect(rewards.plants.single.milestones.single.status, 'earned');

    final profile = CommunityProfile(
        {'district': 'dhaka', 'public_alias': 'Garden voice'});
    expect(profile.publicAlias, 'Garden voice');
    final post = CommunityPost({
      'id': 'post-id',
      'author_alias': 'Garden voice',
      'topic': 'care',
      'body': 'Observe the leaves.',
      'status': 'approved',
      'created_at': '2026-10-06T00:00:00Z',
    });
    expect(post.body, isNot(contains('password')));
  });
}
