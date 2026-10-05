# Offline care — Android prototype

## Set up and preview

1. Follow [Mac setup](SETUP_MAC.md). Back up/rehearse restore before upgrading
   an existing database; migration `0007` is required for duplicate-safe care sync
   and the current schema head is `0009`.
2. In the Android emulator/phone, open **Settings → Security & privacy → Device
   unlock → Screen lock** (wording varies) and set your own PIN/password/pattern.
   No screen lock means offline storage refuses access. Groot never reads the PIN.
3. Sign in online → account page → top-right **Offline care** icon → **Unlock
   offline notebook** using the Android credential → **Enable offline care**.
   Read the device-storage/shared-phone/loss disclosure first; default is off.
4. Choose **Download / refresh plans and plants**. Only your saved, rechecked
   latest plans and passports are downloaded. Empty plans remain empty until real
   rights-cleared reviewed care exists. No demo/draft guidance is promoted.
5. Disconnect, or restart the app without a connection. Open the account page's
   **Offline care** icon; no server sign-in is needed for device-unlocked access.
   Expand a downloaded plan or choose **Record care** on a downloaded plant.
6. **Save care** durably records it locally as `pending`, not server-confirmed care.
   To sync later, close the notebook, reconnect and sign in to its original account
   and server, then unlock it again. Opening triggers pending sync; **Sync now** and
   a 30-second foreground retry while the notebook is open are also available.
7. `synced` means the server accepted the record and the acknowledgment was saved
   locally. `needs_review` retains your entry and explains why automatic sync stopped.
   Review the live plant/history before recording a correction as a separate event.

Native vault authentication expires after five minutes. Re-unlock if storage
reports a lock/key error; existing bytes are preserved. **Lock notebook**, leaving
the page, app backgrounding and process restart close device access. Saving new
care can fail after auth expiry/full storage; do not assume it saved without the
pending confirmation. Generic reminders continue to have their separate behavior.
Closing/locking invalidates that in-memory store immediately, including an
in-flight sync. A late acknowledgment cannot overwrite a reopened notebook's
new care entries; the original pending UUID remains for safe retry.

The ordinary online plan/passport screens still require a connection. This feature
is the explicit offline notebook, not silent HTTP caching or offline sign-in.

## Privacy and durability

- One notebook belongs to an immutable server account UUID **and API base URL**,
  not a reusable handle. Another signed-in account cannot open/sync it. To access
  it offline, first sign out and use the device credential; to sync, sign in to its
  actual owner. Do not substitute a newly registered account with the same handle.
- No password, bearer, voice, GPS, photo, consent edit or weather response is
  persisted. Previously saved approximate conditions/citations and your care notes
  are retained only after the separate offline opt-in, which enables no sharing.
- Android Keystore AES-256-GCM with a random IV/authenticated context and a
  device-authentication-required key; encrypted writes use `AtomicFile`. The blob
  is app-private in `noBackupFilesDir`, and app backups are disabled. No plaintext
  fallback, automatic corruption/key-reset erasure or hard-coded encryption key.
- Device credential confirmation gates opening, key use lasts at most five
  minutes, and screenshots/recents capture is blocked by `FLAG_SECURE`. Hardware
  key protection depends on the device; this is not protection from a compromised
  OS/debuggable/rooted device or anyone who knows the device credential.
- Sign-out/password change/session expiry do not silently erase pending care.
  The opted-in encrypted notebook remains device-unlockable without a server
  token. Remote account/plant/plan deletion cannot erase an offline device until
  it reconnects. Review this tradeoff before enabling on a shared phone.
- **Disable and erase local notebook** asks for explicit confirmation including
  pending count, deletes local encrypted storage/key only, and leaves server data
  unchanged. Pending care has no server backup. Uninstall, clear app storage,
  key invalidation or device loss can make it unrecoverable. No portable recovery
  export is implemented; do not overwrite an unreadable notebook as a “fix.”
- Bounds: 50 downloaded plants, 50 latest plans, 500 local care records and 2MiB
  encoded storage. Downloads fail without replacement when incomplete/oversized;
  pending records are never silently evicted. Remove synced/reviewed local copies
  explicitly to reclaim space. Server care history is not downloaded; the notebook
  displays care recorded through this device, not a complete server timeline.

## Cached guidance and weather

Every plan shows its saved version, download/check time, review/expiry dates,
citations, saved conditions and gaps. Availability is **offline/unverified**, never
“current.” A source may be changed/withdrawn or the plan deleted while disconnected;
the device cannot discover that. Reconnect and download to recheck evidence.

Instructions are withheld after 24 hours from the successful read, a future cache
time, non-current server availability or any known profile/directive/condition/care
source expiry. Metadata/citations remain visible. This conservative prototype limit
does not prove advice stayed valid during those 24 hours. Checks use Bangladesh
civil dates and the device clock, which can be inaccurate/tampered with. Online
reads still revalidate live sources; changing conditions requires a new online
plan version. Expired cached advice never becomes recommendation input.

Weather/quest boards are not downloaded. Offline mode makes no forecast-based
watering/dose changes and cannot generate new advice, recommendations or disease
analysis. Offline care is a self-reported event, not verified growth/survival.

## Retry contract and conflicts

`POST /v1/passports/{id}/care` additionally accepts optional `request_id: UUID`.
The offline client creates and durably saves one UUID **before** network I/O and
uses it for every retry. The server uses the bearer-derived owner inside the
existing account/passport transaction. A partial unique index enforces
`(owner_id, request_id)` for non-null IDs; the account lock serializes concurrent
requests. It never trusts client owner/snapshot/acknowledgment fields.

| Situation | Resolution |
| --- | --- |
| Same owner/UUID/plant/normalized action/date/note retry | Return original care ID; no new record |
| Same UUID reused with different plant/content | 409; original unchanged, local entry needs review |
| Separate care operations, including different devices | Append separate events; no overwriting or content-based guessing that two identical actions were the same |
| Missing/deleted/foreign plant | 404; never recreate it; remove cached plant and retain entry needing review |
| Planting date changed, invalid/future date or rejected note | 422; preserve local entry for review; never silently shift dates |
| Lost response/crash after server commit or failed local acknowledgment write | Persisted UUID retries; server returns the same record |
| Transport failure/429/503 | Stay pending; stop this attempt and retry later |
| Expired/revoked session | Stop; live reauthentication needed before syncing, no persisted bearer |
| Account/server mismatch | Refuse sync before any care POST |
| Passport edits/new plan version/deletions/weather choices | Online only; no queued last-write-wins edits or completion applied to a superseded plan |

Only pending entries are automatically retried. Needs-review entries are not
silently rewritten/resubmitted; inspect live history, then explicitly remove the
local record or log a correction. Removing a local synced entry never deletes
server care. Two intentional operations with different UUIDs are separate events;
idempotency prevents retry duplicates, not every possible repeated user action.

Legacy clients omitting the UUID remain compatible but **are not retry-deduplicated**.
The ordinary online care form still uses that legacy route. If a response is lost
there, refresh history before retrying; use the notebook path for durable retries.

## Migration, rollback and checks

`0007` adds one nullable `plant_care_event.request_id` column and its partial unique
index. Historical rows retain all values and get null; no seeds/backfills/drops.
Downgrade is blocked because losing retry identities can duplicate later sync.
Use a forward fix; retain the column/index and pause sync if deploying an older
client. Restore only into a new isolated DB following [migration procedures](DATABASE_MIGRATIONS.md).

```sh
sh scripts/check-api.sh
sh scripts/check-db.sh
sh scripts/check-mobile.sh
# Before upgrade: documented backup and isolated restore rehearsal.
docker compose build api migrate
sh scripts/db.sh upgrade
sh scripts/db.sh check  # 0009
docker compose up -d --wait api
```

Emulator fixture test (no live DB writes):

```sh
cd apps/mobile
../../scripts/flutterw test integration_test/offline_care_smoke_test.dart -d emulator-5554
```

The emulator test exercises offline UI/persistence/sync with a clearly synthetic
vault/HTTP fixture and the **real native locked/no-device-lock rejection**. It does
not claim that mocked storage verifies native encryption/unlock/crash durability.
The successful credential/Keystore path still needs a secure-device manual test.
See [TDD evidence](testing/offline-care.tdd.md) for actual checks and limitations.

Primary Android references checked 2026-10-05:
[Keystore/authentication](https://developer.android.com/privacy-and-security/keystore),
[device credential confirmation](https://developer.android.com/reference/android/app/KeyguardManager),
[atomic writes](https://developer.android.com/reference/android/util/AtomicFile).
Device confirmation uses the existing Activity callback bridge (deprecated Android
API); a future platform update should migrate it without removing auth checks.
