# Quest/weather/reminder test evidence — 2026-10-05

Journeys were derived from the user's request: turn saved plans into daily/weekly
tasks, adapt checks to weather changes, expose stale forecasts and add reminders.
No supplied external plan was executed. Selected skills: FastAPI, Dart/Flutter,
PostgreSQL patterns and test-driven workflow. Tests precede feature implementation;
repository instructions prohibit unrequested commits, so no checkpoint commits
were created. This report preserves RED/GREEN evidence instead.

## RED → GREEN

- `sh scripts/check-api.sh`: new `tests/test_quests.py` initially failed with
  `ModuleNotFoundError: No module named 'app.quests'` (intended missing engine).
- `../../scripts/flutterw test test/quests_test.dart`: initially failed to compile
  because `lib/quest_board.dart` / `QuestBoard` did not exist (intended missing UI).
  The first attempt hit SDK telemetry sandbox access; rerunning with tooling access
  confirmed the actual missing-feature RED signal.
- Implemented bounded scheduling/forecast contracts, an additive revision and
  owner/version persistence, then the Flutter board and native generic reminders.
- Integration fixtures initially planted before review dates and were correctly
  blocked. Corrected only the synthetic fixtures' source/profile/directive review
  dates; did not weaken evidence gates. A malformed-response test accidentally
  supplied a valid response and was corrected.
- Mobile regression tests caught a platform-binding dependency in plain HTTP
  client tests: replaced direct reminder calls with an injected session-clear
  callback wired by the private garden. Corrected widget scroll/layout timing
  before tapping off-screen controls. No ignored failures/skipped checks.

## Passing guarantees

| Guarantee | Test target | Type/result |
| --- | --- | --- |
| Observation daily / directive review weekly, no invented action frequency, partial gaps disclosed, future/stale plans withheld | `services/api/tests/test_quests.py` | Unit PASS |
| Rain/heat update separate checks without changing original text/keys; retrieval-age/date gates disable stale adaptation; Bangla district aliases work | `services/api/tests/test_quests.py` | Unit PASS |
| Fixed HTTPS host, timeout/size cap, rejected redirects/units/timezone/invalid arrays/dates/nonfinite numbers; disabled mode makes no call | `services/api/tests/test_weather.py` | Mocked transport PASS |
| Owner isolation, unknown/future/old version rejection, retry-safe completion/undo, independently noticed opt-in, shared cache, provider failures/corruption and post-fetch expiry | `services/api/tests/integration/test_quests.py` | Real PostgreSQL/API PASS |
| New version resets completion/opt-in, deletion cascades,0005 snapshots survive upgrade, destructive rollback blocked | `services/api/tests/integration/test_quests.py` | Real migration/DB PASS |
| Stale warning visible; actual completion request updates UI; unsupported/denied reminder capability degrades safely | `apps/mobile/test/quests_test.dart`, `care_reminders_test.dart` | Widget/channel PASS |
| Synthetic quest completion and real native Android reminder enable/status/cancel | `apps/mobile/integration_test/quests_smoke_test.dart` | Emulator PASS |

## Final commands/results

- `sh scripts/check-api.sh`: **136 passed**,95 integration cases deselected as
  intended; runtime network disabled. These136 are a subset of the combined231.
- `sh scripts/check-db.sh`: **231 passed**, **99.64% statement coverage**,90% gate
  satisfied; includes app/migrations. Owned temporary PostgreSQL resources only.
- `sh scripts/check-mobile.sh`: analyzer clean, **23 tests passed**, normal ARM64
  debug APK built. Existing Flutter SDK preserved; no new package dependency.
- From `apps/mobile`: `../../scripts/flutterw test integration_test/quests_smoke_test.dart
  -d emulator-5554 --dart-define=NATIVE_REMINDER_TEST=true`: **one passed** on API36.
  Uses explicit synthetic HTTP fixtures, no real account/catalog writes. Temporarily
  enabled emulator notification permission for native scheduling/cancel assertions.
  Flutter removed the test package afterward; reinstalled the normal preview, with
  original notification permission denied. No notification delivery-time claim.
- `python3 -B -m unittest discover -s scripts/tests -v`: **seven passed**.
- `git diff --check`: clean. Real-index `scripts/check_repo.py` deliberately reports
  new untracked source files: this task leaves staging/committing to user approval.
  Existing three staged editor files were preserved. This is not a functional
  app/test failure or a remote CI pass.
- `python3 scripts/smoke_api.py`: live readiness/API and five Bangla catalog rows
  passed. Updated OpenAPI exposes all three quest routes; live weather mode disabled.

## Real data preservation / remaining gaps

Private backup `backups/groot-before-0006.2D5scr` restored into a new no-network,
tmpfs PostgreSQL server; data-only dump hashes matched live data. After guarded
upgrade to0006, all14 original tables' row counts and exact hashes matched before/
after. API/DB are healthy; only owned test/restore resources removed; backup kept.
No live content approval or provider request was made.

Not verified: inexact alarm delivery timing under Doze/battery limits, receiver
notification presentation, OS permission-denial dialog on device, reboot/timezone
recovery (not implemented), live provider availability/plot accuracy or production
roles/TLS. Model issue time remains unknown. No offline queue, automatic irrigation
policy, push service, rewards or passport linkage. Real approved catalog/care
content is pending. Existing Starlette/httpx deprecation warning is non-failing.
The previously diagnosed remote Android SDK setup failure remains unchanged;
no remote workflow was rerun, commit made or push performed.
