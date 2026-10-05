# Offline-care TDD evidence — 2026-10-05

Source: user requested downloaded plan viewing, offline care entry, later sync
without retry duplicates and explicit conflict rules. Implementation plan was
communicated before editing; no separate supplied plan file.

## Journeys and RED

- Grower opts into an Android notebook, downloads reviewed plans/plants, then
  unlocks and records care without network access, including after restart.
- Retry a lost response or crash without adding another server care record.
- See pending/synced/needs-review states; another account cannot sync private care.
- Preserve original records through an additive migration; never recreate deleted
  plants, overwrite care content or claim old weather/guidance is current.

Before production edits, `../../scripts/flutterw test test/offline_care_test.dart`
failed because the referenced `OfflineVault`/`OfflineCareStore`/`offlinePlan`
implementation did not exist (intentional compile-time RED).

`sh scripts/check-db.sh python -m pytest -q tests/integration/test_offline_care.py`
executed5 tests: **4 failed,1 passed**. The new UUID was rejected as extra input;
concurrent retry and migration preservation contracts were unimplemented. This
was a real runtime RED on disposable PostgreSQL, not a development-data reset.

Initial tool-cache sandbox restrictions and one incorrectly supplied test command
were resolved before recording RED; those infrastructure failures are not RED proof.

## GREEN and guarantees

| Guarantee | Evidence | Result |
| --- | --- | --- |
| Durable queue/reopen preserves UUID; failures never falsely acknowledge | `apps/mobile/test/offline_care_test.dart` | Passed |
| Lost response/local acknowledgment write failure retries original ID | Same Flutter test | Passed |
| Closing during sync prevents a late acknowledgment overwriting reopened local care | Same Flutter test | Passed |
| Different owner/server refused;409/422 retained for review;401/429/503 stay pending | Same Flutter test | Passed |
| Date/action/note/plant checks and500-entry no-eviction bound | Same Flutter test | Passed |
| No network needed to record; explicit opt-in/download/citations/sync/local erase | Same Flutter widget tests | Passed |
| Offline instructions withheld for expiry/age, metadata retained | Same Flutter test | Passed |
| Concurrent PostgreSQL retry returns same care ID; changed content409 | `services/api/tests/integration/test_offline_care.py` | Passed |
| Ownership/deletion/date/legacy compatibility and additive preservation | Same PostgreSQL test | Passed |
| Entire backend/API/migration regressions | `sh scripts/check-db.sh` | 236 passed;99.58% statement coverage (>=90% gate) |
| Network-isolated unit/config checks | `sh scripts/check-api.sh` | 136 passed;100 integration tests deselected |
| Flutter analysis, full regression suite and normal ARM64 debug APK | `sh scripts/check-mobile.sh` | Clean analysis;48 passed;build passed |
| Offline-specific tests, lifecycle race, pending-removal guard and five-minute/account isolation | `flutterw test test/offline_care_test.dart --coverage` | 25 passed;queue core174/187 executable lines covered (93.05%) |
| Emulator offline record/reopen/sync-once, native locked/no-PIN rejection | `flutterw test integration_test/offline_care_smoke_test.dart -d emulator-5554` | One passed |

The first full DB run caught outdated older-head rollback-message expectations;
they were updated to assert0007's deduplication guard. Rerun236 tests passed.
The opt-in widget fixture needed actual UTF-8 JSON headers and settled scrolling
through a lazy list/selectable citations. The pending-removal regression first
failed because the store allowed deleting a pending entry; the new guard now
passes. A late-response regression also first failed: lock waited behind network
sync, allowing an old store to overwrite a reopened notebook. Lock now invalidates
the store synchronously and rejects its subsequent commits; foreground timeout,
backgrounding and disposal use the same guard. Final25 offline and48 full Flutter
tests passed. Dart lint fixes
were mechanical braces/unused-import corrections; final analysis is clean.

Seven repository-check regressions and `git diff --check` passed. The actual
Git-index handoff check intentionally does **not** pass: prior quest and new
offline files remain untracked pending owner staging/commit. No remote CI run
or push is claimed.

## Boundaries and preservation

The emulator's main care/reopen/sync flow uses synthetic vault/HTTP fixtures and
does not approve live agricultural content or create real accounts. Native lock
refusal is real, but successful device credential confirmation, native encryption,
key invalidation and process-kill atomic-file recovery are **not** verified by that
fixture. No permission was given to add a test PIN; those remain secure-device
manual checks. Clock tampering and remote revocation cannot be solved offline.

The private backup `backups/groot-before-0007.v7Aq6S` was restored on a no-network,
tmpfs PostgreSQL server. All17 table counts/hashes matched. Guarded0007 upgrade
and compatible API restart succeeded; all17 old tables' values remained unchanged
(excluding only the new nullable retry column). The test restore container alone
was removed; backup and real database remain. Live catalog smoke passed5 Bangla rows.

Project instructions prohibit commits unless requested, overriding this skill's
checkpoint-commit examples. RED/GREEN evidence is preserved here instead; no
staging/commits/push or unrelated worktree/SDK/editor changes.
