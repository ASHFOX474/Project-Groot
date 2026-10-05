# Accounts, privacy choices and Plant Passports

## Try it on the Android preview

Signed-in growers can also open **Plan a goal** for transient bilingual condition
matching. Goal/location details are not saved into passports or consent receipts;
there is no GPS collection. Optional speech has its own provider disclosure.
See [goal input/privacy contract](GOALS_RECOMMENDATIONS.md).

Separately saving a care plan explicitly retains chosen location and structured
conditions (not free goal/soil prose), with owner-only immutable versions. This
does not collect GPS/audio or change consent preferences. Whole-plan/account
deletion cascades plan versions. See [care contracts/privacy](CARE_PLANS.md).

After the normal Mac setup, open Groot and tap the **account icon** in the top
right. Choose **Create a new account**, enter a unique handle (3–32 ASCII letters,
digits or underscores) and a passphrase of 15–128 characters. Handles are
case-insensitive; passwords are not trimmed. These are local accounts, not verified
email/phone identities. No recovery email, password reset or MFA is implemented.
Keep your passphrase safely. Use test data, not real personal information, on the
local HTTP preview. Do not reuse a password from another service.

Read the in-app notice before registering. Optional choices default to off; an
account and private garden work with all three off. The current notice version is
`2026-10-04`. **Consent choices** lets you change or withdraw each preference:

| Choice | Intended purpose | Current behavior |
| --- | --- | --- |
| Precise location | Optional coordinates attached to a future check-in | No GPS capture, location permission or coordinate field exists |
| Photo check-ins | Separate per-plant storage and health choices | Private uploads are implemented; sharing, public passports and analytics do not exist |
| Community | Optional moderated text posts and district-level aggregates | Requires this choice plus a separate community profile notice; posts are approved before feed visibility, and withdrawal hides posts/removes district metadata |
| Impact | Optional aggregate survival statistics | No separate impact dashboard; community trends use only opted-in, k-anonymous district aggregates |

These are recorded preferences, not blanket permission for unrelated features.
Community activation additionally needs the `community-2026-10-06` profile notice.
Setting a choice to true does **not** publish a passport, photo or exact location.
Necessary account/passport storage is explained separately from optional uses; no
marketing consent is required.

Tap **Add plant** to enter a nickname, your species identification, planting date,
growing space, sunlight, soil/potting description and optionally an approximate
area. Unknown sunlight/soil are acceptable. Do not enter a home address or exact
coordinates in free text. Dates run from 1900 through today in Bangladesh.
Species names are self-reported, not an AI identification or planting approval.
The app currently records names manually; the API additionally permits an optional
active non-demo catalog reference. A reference is still not a recommendation.

Open a passport to edit it or **Log care** (watering, feeding, pruning, repotting,
observation). Care dates cannot precede planting or be in the future; editing the
planting date cannot invalidate existing care. History is ordered by date and ID,
paginated, and self-reported, not proof of care/survival. Log an observation to
clarify an earlier entry; care-entry edits are not implemented. The opt-in Android
[offline notebook](OFFLINE_CARE.md) now queues care using durable UUID retry IDs.
The ordinary online form/legacy clients omit those IDs: after a lost network
response there, refresh history before retrying rather than assuming deduplication.

Open **Rewards and community** from the private garden to review care streaks and
self-reported 3-, 6- and 12-month milestones. The score averages capped scores
across plants, so plant count adds no points. To post, enable community consent,
choose a district and public alias, then submit text for moderation. Approved feed
items show the alias only; neighborhood results require five opted-in growers and
show aggregates rather than individual gardens. These records do not verify plant
survival or publish private photos.

**Sign out** revokes this session. **Password** requires the current password and
revokes every session, then asks you to sign in again. **Delete plant** requires a
UI confirmation and deletes that passport and its care history. **Delete account**
requires a confirmation and current password; it deletes that account's active
records, sessions, passports, care history and consent receipts, not other users
or the catalog. These deletions cannot be undone in the app. Backups may retain
older data until the operator removes/expires them under a retention policy.

## Storage and authorization

- Passwords use random 16-byte salts and scrypt (`N=2^17`, `r=8`, `p=1`, 32-byte
  output), using Python's standard cryptographic implementation. A small obvious
  weak-password check is included, not a full breached-password service. The
  [OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
  informed the parameters. Memory-heavy derivations are capped at two per process.
- Sessions use independent cryptographically random 32-byte bearer tokens. Only
  SHA-256 token digests are stored in PostgreSQL. Absolute lifetime is 12 hours,
  with no refresh. Up to five sessions are retained per account; later sign-ins
  replace the oldest. This follows the unpredictable-token/server-side-state
  principles in [OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
- Flutter keeps the token only in memory; no password/token is written to files,
  preferences, URLs or logs. Restarting the app or closing the account screen
  requires sign-in. Closing the screen alone does not revoke a server session;
  use Sign out to revoke it. Persistent login tokens remain separate work.
  A failed sign-out still clears local data, but the server token can remain valid
  until expiry. A 401 clears the local session and private view.
- Separately opted-in offline data remains encrypted and device-unlockable after
  sign-out/session expiry; no bearer/password is retained. Offline storage does
  not grant API authentication. Anyone knowing the device credential can access
  the notebook. Remote deletion cannot erase a disconnected device; explicitly
  erase local data when desired, with a warning before losing unsynced care.
  Review [storage limits, device access and conflicts](OFFLINE_CARE.md).
- Every private DB transaction resolves the bearer session and locks the account,
  then rechecks session validity. Reads/writes include that authenticated owner;
  clients cannot supply an owner ID. Foreign-account and missing passport IDs both
  return 404. Care rows also have a composite FK to their passport **and owner**.
  Password change, logout, consent, deletion and protected writes serialize on
  the account row. Lock/statement waits are bounded.
- Consent changes append a dated receipt (choices, notice version, account) and
  update current choices in the same transaction. Withdrawing a preference does
  not delete private plant records or disable the account.
- This is API-level owner isolation, not encryption from database administrators.
  Other than password/token hashes, records are readable by the DB operator and
  backups. The development DB role is privileged; before real/shared deployment,
  establish least-privilege runtime/migration roles, encrypted storage/backups,
  access review, retention/restore-after-deletion policy and a security review.

## Network and abuse controls

Private endpoints require HTTPS unless `APP_ENV=development` is explicitly set.
Missing/other environments fail closed on HTTP. The local Compose stack deliberately
uses development HTTP and a localhost-only API port; never distribute that setup
with real credentials. Flutter profile/release private requests reject HTTP.
There is no cookie authentication, permissive CORS, or query-string token support;
native requests use `Authorization: Bearer TOKEN`. Never paste live tokens into
URLs, screenshots, tracked files or a shared terminal.

The runtime disables proxy-header trust. For a deployment, configure actual TLS
at the server or a reviewed trusted proxy, specify exact trusted proxy addresses,
prevent direct bypass and set a non-development environment. Do not trust arbitrary
`X-Forwarded-Proto`/`X-Forwarded-For`, wildcard proxy addresses, or change to
development to silence HTTPS errors. Production deployment is not provided here.

Shared PostgreSQL fixed-window limits apply before password work: registration
10/IP and 10/handle per 15 minutes, login 30/IP and 10/handle per 15 minutes;
password-change/deletion verification 10/IP per 15 minutes; other private routes
120/IP per minute. Attempt counters commit even on rejected attempts. Expired
buckets are cleaned on the next throttled request. Only SHA-256 digests of scoped
IP/handle keys are retained; these are pseudonymous, not anonymized. Failed login
responses do not distinguish missing handles from incorrect passwords. Registering
an occupied handle returns a generic conflict; handle availability is not secret.
Shared NAT users can hit a common IP limit. Limits are not a DDoS service; add
reviewed proxy/perimeter protection before a public deployment.

Private responses, including errors, use `Cache-Control: no-store`. Bodies are
bounded to 16KiB even when chunked; unknown fields, invalid units/dates/UUIDs,
oversized strings, null characters and invalid Unicode are rejected. Validation
errors omit supplied input values; unexpected DB errors return generic 503s.
An independently disclosed, per-plan opt-in regional weather provider is now
available; no account/plant/goal data or GPS is sent. General consent preferences
do not enable it. See [weather notice and withdrawal](QUESTS_WEATHER_REMINDERS.md).
No third-party analytics were added. Review deployment/DB
logging too: privileged operator logs and backups must not become a PII leak.

## API contract

Swagger remains at `/docs` for local testing. Do not use real credentials there
over HTTP. Request/response models are in `app/accounts.py`; routes are in
`app/account_routes.py`. Private collections support `limit=1..100` (default20)
and `after=UUID`, with owner-bound cursor lookup for care chronology.

| Method / path (`/v1` prefix) | Behavior |
| --- | --- |
| `POST /accounts/register` | Handle/password, notice version and optional choices; create account and session |
| `POST /accounts/login` | Handle/password; new session |
| `GET /accounts/me` | Own handle and current choices; no password hash |
| `PUT /accounts/consent` | Full choice snapshot + notice version; append receipt |
| `POST /accounts/logout` | Revoke current bearer session |
| `POST /accounts/password` | Current/new password; revoke all sessions |
| `POST /accounts/delete` | Current password; explicit permanent active-data deletion |
| `GET, POST /passports` | Paginated own records / create a private record |
| `GET, PUT, DELETE /passports/{id}` | Own record / replace its editable fields / delete it |
| `GET, POST /passports/{id}/care` | Own dated timeline / append care |

The catalog endpoints remain public. `/v1/catalog/species` is browsing only;
`/v1/catalog/recommendation-candidates` keeps its fail-closed reviewed-reference
boundary. Private plant names, conditions or care logs are never fed into advice,
RAG, public leaderboards or model providers in this version.

## Migration and checks

Revision `0004` adds new tables/indexes only; it changes no catalog rows or old
revision. Account/record deletion cascades are intentional only inside explicitly
authorized owner endpoints. Downgrade is blocked because dropping these tables
would erase private records; prefer a forward fix or a separately approved restore
into an isolated DB. Follow [backup and migration procedures](DATABASE_MIGRATIONS.md).

```sh
sh scripts/check-api.sh
sh scripts/check-db.sh
sh scripts/check-mobile.sh
# After the documented backup + restore rehearsal:
docker compose up --build --wait
sh scripts/db.sh check
python3 scripts/smoke_api.py
```

For the emulator, from `apps/mobile` with the live development API running:

```sh
../../scripts/flutterw test integration_test/account_passport_smoke_test.dart \
  -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

The live test creates a unique test account, creates a passport/log through the
UI, then explicitly deletes that owned account. Do not point it at a production
API. Isolated DB tests cover two-account read/write isolation, real ownership FKs,
expired/revoked/capped sessions, waiting-request revocation, consent withdrawal,
timeline/cursor/date checks, password change, deletion, throttling, redaction,
HTTPS and migration preservation. No email/SMS service or remote CI run is implied.
