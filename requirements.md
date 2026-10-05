# Groot collaborator requirements

This file describes what a collaborator needs after cloning Groot. Groot is an
Android-first Flutter app with a FastAPI service and PostgreSQL database. The
current repository includes demo catalog data, private accounts and plant
passports, reviewed care-plan plumbing, quests/weather/reminders, offline care,
private photo check-ins, and self-reported rewards/community features. Approved
agronomic care content and production AI services are not included.

## Required software

Install these tools before running the project:

- Git and the macOS command-line tools (`xcode-select --install` if needed).
- Docker Desktop with Docker Compose 2.17 or newer and BuildKit named-build
  context support.
- Flutter 3.47.5 stable with Dart 3.13.4. A newer compatible Flutter version
  may work, but the checked reference version is preferred.
- Java Development Kit 21. Flutter compiles the Android project with Java/Kotlin
  17 settings; the Android build toolchain itself expects a JDK 21 installation.
- Android SDK API 36, platform-tools, emulator, build-tools 36.0.0, NDK
  28.2.13676358, CMake 3.22.1, and a Google APIs API 36 system image.
- Android Studio is recommended for SDK Manager and Device Manager. VS Code with
  the Dart and Flutter extensions is recommended for editing and F5 debugging.
- Python 3.12 or newer for repository scripts and optional host-side API work.

Host PostgreSQL, Node.js, and an AI API key are not required for the standard
Docker workflow.

## Clone and inspect

```sh
mkdir -p "$HOME/Developer"
cd "$HOME/Developer"
git clone https://github.com/ASHFOX474/Project-Groot.git
cd Project-Groot
git status --short
```

If this is a private repository, use normal GitHub authentication. Do not put a
token or password in a clone URL. Do not run `flutter create` over the checkout;
the Android runner and Gradle wrapper are already part of the repository.

Install Flutter separately from the repository. For example, after installing
the SDK into `$HOME/development/flutter`:

```sh
export PATH="$HOME/development/flutter/bin:$PATH"
flutter --version
./scripts/flutterw --version
```

The wrapper uses `GROOT_FLUTTER_BIN` when set, then an ignored `flutter/` folder
inside the checkout, then Flutter on `PATH`:

```sh
export GROOT_FLUTTER_BIN="$HOME/development/flutter/bin/flutter"
```

Use the actual SDK path on the collaborator's machine. Never commit the SDK.

## Configure the backend

From the repository root, create a local environment file without overwriting an
existing one:

```sh
test -f .env || cp .env.example .env
docker compose up --build --wait
sh scripts/db.sh seed-demo
python3 scripts/smoke_api.py
```

The API is available at `http://localhost:8000`. Useful checks are:

```sh
curl http://localhost:8000/health/ready
curl http://localhost:8000/v1/catalog/species
```

The Compose database volume is persistent. Do not run `docker compose down -v`
unless intentionally deleting local database data. Schema changes use Alembic;
review `docs/DATABASE_MIGRATIONS.md` and use `sh scripts/db.sh` before changing
or upgrading a database. The current migration head is `0009`.

Weather is disabled by default. Review
[`docs/QUESTS_WEATHER_REMINDERS.md`](docs/QUESTS_WEATHER_REMINDERS.md) before
enabling any external weather provider.

## Configure Android and run the app

Set the Flutter Android SDK and JDK if Flutter has not been configured:

```sh
./scripts/flutterw config --jdk-dir="$(/usr/libexec/java_home -v 21)"
./scripts/flutterw config --android-sdk="$HOME/Library/Android/sdk"
./scripts/flutterw doctor --android-licenses
./scripts/flutterw doctor -v
```

Create or use a Google APIs Android API 36 emulator. The project setup expects a
device named `Groot_API_36`, but any connected device ID can be supplied.

Terminal 1, from the repository root:

```sh
sh scripts/start-emulator.sh
```

Terminal 2, from the repository root:

```sh
./scripts/flutterw devices
sh scripts/preview-android.sh emulator-5554
```

Replace `emulator-5554` with the ID reported by `flutterw devices`. The emulator
reaches the host API through `10.0.2.2`. In VS Code, select the emulator and use
the `Groot · Android demo` launch configuration. The Android manifest permits
cleartext HTTP only for debug builds; use HTTPS for a distributed app.

## Run checks

Run checks from the repository root after installing Docker and Flutter:

```sh
python3 -B -m unittest discover -s scripts/tests -v
python3 -B scripts/check_repo.py
sh scripts/check-api.sh
sh scripts/check-db.sh
sh scripts/check-mobile.sh
```

`check-db.sh` starts an isolated PostgreSQL test project and does not use the
development volume. `check-mobile.sh` runs Flutter analysis/tests and builds the
Android debug APK. A live seeded emulator smoke test is optional:

```sh
cd apps/mobile
../../scripts/flutterw test integration_test/catalog_smoke_test.dart \
  -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

## Project rules for collaborators

- Read `README.md`, `docs/PRODUCT.md`, and `docs/ARCHITECTURE.md` before making
  cross-cutting changes.
- Read the feature guide before changing care plans, offline care,
  quests/weather/reminders, accounts, catalog data, or photos.
- Keep secrets, `.env`, photos, backups, SDKs, build output, and caches out of Git.
- Do not edit an applied migration. Add a new forward migration and document the
  rollback/data-preservation decision.
- Private records are owner-scoped. Consent is separate for community sharing,
  photos, and offline storage. Community output is moderated, pseudonymous, and
  district-level; never publish exact locations or private photos.
- Rewards are self-reported indicators, not verified plant-survival measurements.
- Append a dated entry to `builders.md` after every task that changes project
  files. Include changed files, purpose, checks, and remaining risks.
- Do not commit or push unless the project owner explicitly asks for it.

For the longer Mac and Android walkthrough, see
[`docs/SETUP_MAC.md`](docs/SETUP_MAC.md). For API contracts and privacy rules,
see the account and feature documents under `docs/`.
