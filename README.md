# Groot

Groot is a Bangla-first plant-care companion for Bangladesh. This repository is a **starter**, not a completed AI product. It provides an Android-first Flutter shell, a FastAPI catalog API, a PostgreSQL database, and a documented path to care plans, check-ins, weather-aware tasks, and survival milestones.

## What works in this starter

- `GET /health/live` and `GET /health/ready` for service checks.
- `GET /v1/catalog/species` for a small, explicitly labelled **demo** catalog.
- A Flutter screen that fetches the catalog and shows connection errors.
- A local PostgreSQL service with an initial schema and demo rows.
- A complete Android runner and Mac emulator setup instructions.
- Source-traceable research profiles, a strict offline/atomic import process and
  a recommendation-candidate data boundary that excludes demo and uncleared data.
  Current profiles remain draft; no approved planting advice is shipped yet.
- Handle/password accounts, editable optional consent choices, owner-only Plant
  Passports and a dated care history, with an Android account/garden flow.
- Bangla/English goal intake, optional Android voice-to-editable-text, chosen
  location precision and conservative, cited suitability rules. Approved content
  is still pending; demo/draft records never become recommendations.
- Personalized reviewed care previews, citations/review dates, explicit private
  saving and immutable plan versions, with withheld missing/conflicting/stale advice.
  Approved care content is still pending; no instructions are invented.
- Daily observations and weekly reviewed-instruction tasks, retry-safe completion,
  opt-in district forecasts with stale-data fallback, in-app and generic Android
  reminders. See [quests/weather setup](docs/QUESTS_WEATHER_REMINDERS.md).
- Opt-in Android offline notebook for downloaded plans/plants and durable manual
  care, with owner-bound retry IDs, explicit conflicts and stale-advice withholding.
  Device screen lock is required; see [offline setup and limits](docs/OFFLINE_CARE.md).
- Explicitly opted-in private photo check-ins with bounded JPEG/PNG storage,
  paginated timelines, possible-observation flags with uncalibrated confidence,
  and an agricultural expert-help path. This is not a disease diagnosis service.
- Self-reported care streaks, 3-, 6- and 12-month milestone rewards, an average
  per-plant score, and a consented moderated community with k-anonymous district
  trends. Community posts stay hidden until approved.

AI recommendations, validated disease detection, automatic irrigation/doses,
email recovery and MFA remain **planned work**. Photo check-ins are private,
off by default and never public; survival and care rewards are self-reported and
do not verify plant health. No screen or endpoint should present the local
observation heuristic as a diagnosis.

See the [four-milestone audit and remaining approval steps](docs/MILESTONE_STATUS.md).
The local starter, migration and account/passport paths work; the catalog
infrastructure works but its research drafts are not approved planting advice.

## First time on a friend's Mac?

Follow the [complete Mac setup and Android preview guide](docs/SETUP_MAC.md):
cloning, tool installation, Android Studio reopening, emulator creation, SDK
settings, backend setup and terminal/F5 preview. The maintainer must publish the
complete setup files first; local uncommitted files are not available in a GitHub clone.

## Repository map

| Path | Purpose |
| --- | --- |
| `apps/mobile/` | Flutter Android app source |
| `services/api/` | FastAPI service and API tests |
| `services/api/migrations/` | Immutable Alembic schema revisions |
| `services/api/catalog/` | Versioned research draft and source-access evidence |
| `db/init/` | Unchanged historical SQL used to test legacy adoption, not startup |
| `docs/` | Product, architecture, and delivery plan |
| `AGENTS.md` | Instructions for coding agents and skill selection |
| `builders.md` | Change reports: which files changed, why, and verification |
| `MASTER_PROMPT.md` | Reusable project workflow prompt |

## Requirements

- Docker with Docker Compose for the API and database.
- Flutter 3.47.5 (the version used to generate and verify the runner), Java 21,
  and Android SDK 36 with an emulator for the mobile app.
- Python 3.12 or newer if running the API without Docker.

## Start the API and database

From the repository root:

```sh
# Only copy if you do not already have a local .env; do not overwrite it.
test -f .env || cp .env.example .env
docker compose up --build --wait
sh scripts/db.sh seed-demo  # explicit local sample data, never part of schema migrations
python3 scripts/smoke_api.py
```

Open `http://localhost:8000/docs`, or check:

```sh
curl http://localhost:8000/health/ready
curl http://localhost:8000/v1/catalog/species
```

The API listens only on `127.0.0.1:8000`. PostgreSQL is private to the Compose
network, avoiding conflicts with other local databases. Its credentials in
`.env.example` are development defaults. The named volume preserves data; SQL
schema changes now run through a one-shot Alembic migration service before the API
starts. Existing unversioned volumes require the backed-up, validated adoption in
[Database migrations](docs/DATABASE_MIGRATIONS.md), not a reset or blind stamp.
Never use `docker compose down -v`
unless you intentionally want to delete that database.

## Start the Flutter app

The Android runner is included. **Do not rerun `flutter create` during normal
setup.** Your local `flutter/` SDK stays on disk but is ignored by Git; the helper
uses it first, otherwise it uses Flutter on your PATH. See
[Mac setup and preview](docs/SETUP_MAC.md) for Android tooling and troubleshooting.

From the repository root, in two terminals:

```sh
# Terminal 1: boot the emulator (leave this running).
sh scripts/start-emulator.sh

# Terminal 2: start/check services and launch the app with hot reload.
sh scripts/preview-android.sh emulator-5554
```

`10.0.2.2` reaches the host from the Android emulator. Use `./scripts/flutterw devices`
to find the actual device ID. In VS Code, install the recommended Flutter
extension, select the emulator, then press F5 using “Groot · Android demo”. The
preview is an Android emulator window on your Mac, not a browser or native Mac app.

For a USB Android phone, keep the API private: run `adb reverse tcp:8000 tcp:8000`
and launch with `--dart-define=API_BASE_URL=http://127.0.0.1:8000`. Merely using a
LAN IP will not reach a localhost-only service. Cleartext HTTP is allowed in
**debug Android builds only**; use HTTPS before distributing an app.

## Checks

```sh
python3 -B -m unittest discover -s scripts/tests -v  # repository-check regressions
python3 -B scripts/check_repo.py  # read-only Git tracking/private-path handoff gate
sh scripts/check-api.sh       # isolated Python 3.12 API tests via Docker
sh scripts/check-db.sh        # real PostgreSQL tests + migration coverage; isolated temporary project
sh scripts/check-mobile.sh    # analysis, widget test, and Android debug APK
python3 scripts/smoke_api.py  # live API/database; Compose must be running

# Live emulator test; run against the seeded demo database.
cd apps/mobile
../../scripts/flutterw test integration_test/catalog_smoke_test.dart \
  -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

API unit tests do not need PostgreSQL. Database integration tests create only
fixture-owned databases on a separate temporary PostgreSQL server, never the
development volume. GitHub runs the same check scripts and exercises migration
startup plus explicit seeding. It builds the Android runner but does not
currently run the emulator test. See `docs/ROADMAP.md` for the next slices.

## Database changes

```sh
sh scripts/db.sh current
sh scripts/db.sh check
# After backup/review, upgrade an already versioned database:
sh scripts/db.sh upgrade
```

Use [the migration/backup/rollback guide](docs/DATABASE_MIGRATIONS.md) before any
schema change. Never edit an applied revision or the historical init SQL. Demo
seeding is explicit and does not overwrite existing rows. Tests require Docker
Compose with BuildKit named build contexts (Compose 2.17+).

## Plant catalog review and imports

Read [source access/licensing findings](docs/CATALOG_SOURCES.md) and
[catalog import/eligibility procedures](docs/CATALOG_IMPORT.md). To validate the
bundled research draft without DB writes:

```sh
docker compose build api migrate
sh scripts/import-catalog.sh
```

Import requires the documented backup/review and explicit `--apply --confirm`;
it is not part of normal demo seeding or migrations. Three plants have cited
requirements but remain quarantined pending rights/local agronomic review.
TreeGOER metadata confirms a reusable CC BY4 dataset candidate, not imported care
instructions. Do not confuse a source evidence check with planting approval.

`GET /v1/catalog/recommendation-candidates` is the reviewed reference-data boundary.
It currently returns `[]`, not demo fallback. Private
`POST /v1/goals/recommendations` uses that same eligibility query for condition matching.
`GET /v1/catalog/species` stays a preview/general catalog endpoint and must not feed
recommendations or RAG. Reviewed care plans and quests are implemented; approved
care content remains pending.

## Goals and suitable plants

After signing in, choose **লক্ষ্য ও উপযুক্ত গাছ · Plan a goal** in the private garden.
Select Bangla/English, enter a goal and known growing conditions, then choose how
much location to share (none/country/district). Optional Android voice needs a
supported speech provider; typing always works. Results show reasons, sources and
uncertainty, or explain missing data. Recommendations/previews are transient.
Separately saving a care plan retains structured conditions and chosen location,
not free goal/soil prose. Choose **Preview care plan** on a reviewed match, then
open **Saved care plans** for versions/revision. See [care behavior](docs/CARE_PLANS.md).
See [goal workflow, matching rules and voice/privacy limits](docs/GOALS_RECOMMENDATIONS.md).

## Accounts and Plant Passports

Open the mobile app's top-right account icon to register/sign in, add a private
plant, log care and edit consent choices. All optional choices default off. Session
tokens stay only in app memory; restarting requires sign-in. Use test credentials
on the HTTP emulator preview; real use requires HTTPS and production hardening.
Read [account/privacy behavior, API contract and checks](docs/ACCOUNTS_PASSPORTS.md)
before using personal data. Migration head is now `0009`; back up before upgrading
an existing database. Catalog/recommendation permissions remain unchanged.

## Make your Git repository

For a new copy without `.git`, initialize from the repository root:

```sh
git init
git add .
git commit -m "Initialize Groot starter"
```

This checkout already has a Git repository; do not reinitialize it. Do not commit
`.env`, the local Flutter SDK, build outputs, generated plugin registrants, or
personal photos. Commit the Android runner, Gradle wrapper, and pubspec lockfile.
