# Rewards and community test evidence

## Contracts

- Care streaks use unique Bangladesh civil care dates. The current streak ends
  today or yesterday; the best historical streak is retained in the response.
- A 3-, 6- or 12-month card is `earned` only after the planting date is reached
  and a recent care entry exists. Otherwise it is `upcoming` or
  `awaiting_checkin`. The API labels all results self-reported.
- Garden score is the rounded average of capped per-plant scores. Plant count is
  never a score bonus and private plant names do not enter public responses.
- Community posting requires the account choice, a separate district profile
  notice and a public alias. New posts are `pending`; only approved posts enter
  the feed. Three distinct reports auto-hide a post for moderation.
- Neighborhood responses require at least five opted-in growers with plants and
  return district aggregates only. Exact locations, passports and photos are
  excluded.
- Withdrawing community consent hides the owner's posts and clears retained
  district metadata. Account deletion continues to cascade all community rows.

## Checks

| Area | Evidence |
| --- | --- |
| Pure reward calculations and month/streak boundaries | `services/api/tests/test_rewards.py` |
| Migration head, old account rows, owner/session boundaries and downgrade guard | Existing integration migration suite plus `0009` schema |
| Reward response, pending → approved moderation, consent withdrawal, k-anonymous neighborhood | `services/api/tests/integration/test_rewards_community.py` |
| Typed Flutter parsing | `apps/mobile/test/rewards_community_test.dart` |
| Full Flutter analysis, widget tests and Android debug APK | `sh scripts/check-mobile.sh` |

The feature does not verify biological survival, identify disease, publish photos
or capture GPS. Moderator accounts are provisioned by an operator through the
database; there is no public moderator self-registration.
